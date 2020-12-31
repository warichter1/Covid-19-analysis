#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Mar 27 18:16:15 2020

@author: wrichter
"""
# data source: https://github.com/CSSEGISandData/COVID-19.git
# use git clone to create a local copy
# git rm --cached filename

import sys
from datetime import date
from datetime import datetime
from collections import OrderedDict
import operator
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.ndimage.filters import gaussian_filter1d as gs1d
import git
import random

from us_state_abbrev import us_state_abbrev

g = git.cmd.Git('./COVID-19')
print(g.pull())

dataPath = './COVID-19/csse_covid_19_data/csse_covid_19_time_series'
plotPath = './plots/'
trackingUrl = "https://covidtracking.com/api/v1/states/daily.json"
trackingIndex = ['state', 'dates']
confirmedCases = 'time_series_covid19_confirmed_US.csv'
deaths = 'time_series_covid19_deaths_US.csv'
censusData = './nst-est2019-alldata.csv'
stateGovDate = './stateOffices.csv'
stateGovIndex = 'Region'
stateGovExclude = ['2016 presidential election', 'Senior U.S. Senator',
                   'Junior U.S. Senator', 'U.S. House of Representatives',
                   'US House Count']
censusIndex = 'NAME'
censusPopulation = 'POPESTIMATE2019'
censusExclude = ['SUMLEV', 'REGION', 'DIVISION', 'STATE']

config = {'jhuPath': dataPath, 'jhuConfirmed': confirmedCases,
          'jhuDeaths': deaths, 'medUrl': trackingUrl,
          'medIndex': trackingIndex,
          'censusData': censusData, 'censusIndex': censusIndex,
          'censusExclude': censusExclude, 'censusPopKey': censusPopulation,
          'stateGovData': stateGovDate, 'stateGovIndex': stateGovIndex,
          'stateGovExclude': stateGovExclude}

country = 'US'
currentDate = date.today()
projectionDays = 30
deathDays = 3
begin = 10


class CovidCountryRegion:
    """Class to parse and analize by country and region."""

    def __init__(self, config={}):
        """Initialize default variabled in class CovidCountryRegion."""
        self.dataStore = OrderedDict()
        self.dataStore['currentAggregate'] = {}
        self.dataStore['currentCaseRate'] = {}
        self.dataStore['currentDeathRate'] = {}
        self.dataStore['stateControl'] = {'Republican': {'confirmedNew': None,
                                                         'deathsNew': None},
                                          'Democratic': {'confirmedNew': None,
                                                         'deathsNew': None}}
        self.dataStore['testsPerCapita'] = {}
        self.dataStore['casesPerCapita'] = {}
        self.config = config

        self.index = 'Province_State'
        self.exclude = ['Country_Region', 'UID', 'iso2', 'iso3', 'Last_Update',
                        'Last Update', 'Latitude', 'Lat_', 'Lat', 'Longitude',
                        'Long_', 'Active', 'Combined_Key', 'FIPS', 'code3',
                        'Population', 'Admin2']
        self.defaultExclude = self.exclude
        self.defaultIndex = self.index
        self.trackingExclude = ['hash', 'fips', 'total', 'lastUpdateEt',
                                'dateChecked', ]
        self.trackingList = ['recovered', 'positive', 'negative', 'pending',
                             'hospitalizedCumulative',
                             'onVentilatorCumulative', 'inIcuCumulative']
        self.rename = {'Province_State': 'Province/State',
                       'Country_Region': 'Country/Region'}
        self.regionKey = 'Province/State'
        self.subkeys = {'Confirmed': {}, 'Deaths': {}}
        self.printStatus = False
        self.daysIndex = []
        self.regions = []
        self.confirmed = []
        self.deaths = []
        self.censusPop = None
        self.tracking = None
        self.stateGov = {}

    def resetImportDefs(self):
        """Reset import to defaults."""
        self.index = self.defaultIndex
        self.exclude = self.defaultExclude

    def processing(self, printStatus=True):
        """All import and configuration is complete, process the data."""
        self.printStatus = printStatus
        self.importData()
        self.daysIndex = self.confirmed.keys()
        print("Current Date:", self.daysIndex[-1:][0], "Processing:")
        for region in self.regions:
            self.processRegionResults(region)
        self.getAggregate()
        if printStatus:
            self.sortTopDict('currentCaseRate')
            self.sortTopDict('currentDeathRate')
            self.sortTopDict('casesPerCapita')
            self.sortTopDict('testsPerCapita', reverse=False)
            self.printTop(['currentAggregate', 'currentCaseRate',
                           'casesPerCapita',
                           'currentDeathRate', 'testsPerCapita'], 5)

    def getAggregate(self):
        """Evauate the current values of each region for high rates."""
        for region in self.dataStore['currentCaseRate'].keys():
            if region not in self.dataStore['testsPerCapita'].keys():
                self.dataStore['testsPerCapita'][region] = 0
            if region in self.dataStore['currentDeathRate'].keys():
                self.dataStore['currentAggregate'][region] = (self.dataStore['currentCaseRate'][region] * self.dataStore['currentDeathRate'][region]) * 100 + self.dataStore['casesPerCapita'][region] * 1000
        self.sortTopDict('currentAggregate')

    def sortTopDict(self, key, reverse=True):
        """Order by key, reverse (low/high)."""
        self.dataStore[key] = OrderedDict(sorted(self.dataStore[key].items(),
                                                 key=operator.itemgetter(1),
                                                 reverse=reverse))

    def importData(self, path=None, confirmed=None, deathFile=None):
        """Import JHU data."""
        filePath = self.config['jhuPath'] if path is None else path
        file = self.config['jhuConfirmed'] if confirmed is None else confirmed
        self.confirmed = self.importCsv(filePath + '/' + file)
        self.confirmed.fillna(0, inplace=True)
        self.regions = sorted(set(self.confirmed.index))
        file = self.config['jhuDeaths'] if deathFile is None else deathFile
        self.deaths = self.importCsv(filePath + '/' + file)
        self.deaths.fillna(0, inplace=True)
        self.tracking = self.downloadJson(self.config['medUrl'],
                                          self.config['medIndex'])
        self.censusPop = self.importCsv(self.config['censusData'],
                                        index=self.config['censusIndex'],
                                        exclude=self.config['censusExclude'])
        self.censusPop = self.censusPop[self.config['censusPopKey']]
        self.stateGov = self.importCsv(self.config['stateGovData'],
                                       index=self.config['stateGovIndex'],
                                       exclude=self.config['stateGovExclude'])

    def processRegionResults(self, region):
        """Process the results of a region."""
        self.dataStore[region] = {'confirmed': [], 'deaths': [],
                                  'confirmedNew': [], 'deathsNew': [],
                                  'totalTests': [], 'casesPerCapita': [],
                                  'caseRate': [], 'deathRate': [],
                                  'maxCaseRate': 0,
                                  'maxDeathRate': 0, 'increasingDeaths': False,
                                  'increasingCases': False}
        previousDay = ""
        for key in self.trackingList:
            self.dataStore[region][key] = []
        for day in self.daysIndex:
            results = self.getTrack(region, day, self.trackingList)
            for key in self.trackingList:
                self.dataStore[region][key].append(results[key])
            confirmed = self.confirmed.loc[region][day].sum()
            self.dataStore[region]['confirmed'].append(confirmed)
            self.dataStore[region]['deaths'].append(self.deaths.loc[region][day].sum())
            if previousDay == "":
                self.dataStore[region]['caseRate'].append(0)
                self.dataStore[region]['deathRate'].append(0)
                self.dataStore[region]['casesPerCapita'].append(0)
                self.dataStore[region]['confirmedNew'].append(confirmed)
                self.dataStore[region]['deathsNew'].append(self.deaths.loc[region][day].sum())
            else:
                if self.dataStore[region]['confirmed'][-2:][0] > 0:
                    caseRate = abs(self.dataStore[region]['confirmed'][-2:][0] / confirmed - 1)
                    self.dataStore[region]['caseRate'].append(caseRate)
                    if region in self.censusPop.keys():
                        self.dataStore[region]['casesPerCapita'].append(confirmed / self.censusPop[region])
                    else:
                        self.dataStore[region]['casesPerCapita'].append(0)
                    if caseRate >= self.dataStore[region]['maxCaseRate']:
                        self.dataStore[region]['maxCaseRate'] = caseRate
                    if caseRate > self.dataStore[region]['caseRate'][-2:][0]:
                        self.dataStore[region]['increasingCases'] = True
                    else:
                        self.dataStore[region]['increasingCases'] = False
                else:
                    self.dataStore[region]['caseRate'].append(0)
                    self.dataStore[region]['casesPerCapita'].append(0)
                new = self.dataStore[region]['confirmed'][-2:]
                self.dataStore[region]['confirmedNew'].append(abs(new[1] - new[0]))
                if self.dataStore[region]['deaths'][-2:][0] > 0:
                    deathRate = self.dataStore[region]['deaths'][-2:][0] / confirmed
                    self.dataStore[region]['deathRate'].append(deathRate)
                    if deathRate >= self.dataStore[region]['maxDeathRate']:
                        self.dataStore[region]['maxDeathRate'] = deathRate
                    if deathRate > self.dataStore[region]['deathRate'][-2:][0]:
                        self.dataStore[region]['increasingDeaths'] = True
                    else:
                        self.dataStore[region]['increasingDeaths'] = False
                else:
                    self.dataStore[region]['deathRate'].append(0)
                new = self.dataStore[region]['deaths'][-2:]
                self.dataStore[region]['deathsNew'].append(abs(new[1] - new[0]))
            previousDay = day
        self.summarizeRegion(region)

    def summarizeRegion(self, region):
        """Create a region summary."""
        self.getParty(region)
        self.dataStore['currentCaseRate'][region] = self.dataStore[region]['caseRate'][-1:][0]
        self.dataStore['currentDeathRate'][region] = self.dataStore[region]['deathRate'][-1:][0]
        self.dataStore[region]['totalTests'] = list(self.addListColsDf(region, keys=['positive', 'negative', 'pending']))
        self.getPop(region)
        if self.printStatus:
            self.printSummary(region)

    def getPop(self, region):
        """Get data for a rgion population."""
        self.dataStore[region]['population'] = 0
        self.dataStore[region]['testsPerCapita'] = 0
        self.dataStore['casesPerCapita'][region] = 0
        if region in self.censusPop.keys():
            self.dataStore[region]['population'] = self.censusPop[region]
            self.dataStore[region]['testsPerCapita'] = self.dataStore[region]['totalTests'][-1:][0] / self.censusPop[region]
            self.dataStore['testsPerCapita'][region] = self.dataStore[region]['testsPerCapita']
            self.dataStore['casesPerCapita'][region] = self.dataStore[region]['confirmed'][-1:][0] / self.censusPop[region]

    def getStateGovStats(self, region):
        """Get statistics for the the region by ruling party."""
        state = {'Republican': 0.0, 'Democratic': 0.0, 'Independent': 0.0,
                 'Coalition': 0.0, 'Unicameral': 0.0}
        if region in self.stateGov.index:
            state[self.stateGov.loc[region]['Governor']] += 1.5
            state[self.stateGov.loc[region]['State Senate']] += 1
            state[self.stateGov.loc[region]['State House']] += 1
            state['control'] = 'Democratic' if state['Democratic'] > state['Republican'] else 'Republican'
        else:
            state['control']  = None
        self.dataStore[region]['government'] = state
        return state['control']

    def getParty(self, region):
        """Get the party in charge of a region."""
        control = self.getStateGovStats(region)
        self.dataStore[region]['control'] = control
        if control is None:
            self.dataStore[region]['control'] = 'None'
            return 0
        confirmedNew = np.array(self.dataStore[region]['confirmedNew'])
        deathsNew = np.array(self.dataStore[region]['deathsNew'])
        if self.dataStore['stateControl'][control]['confirmedNew'] is None:
            self.dataStore['stateControl'][control]['confirmedNew'] = confirmedNew
            self.dataStore['stateControl'][control]['deathsNew'] = deathsNew
        else:
            buffer = self.dataStore['stateControl'][control]['confirmedNew']
            buffer = np.add(buffer, confirmedNew)
            self.dataStore['stateControl'][control]['confirmedNew'] = buffer
            buffer = self.dataStore['stateControl'][control]['deathsNew']
            buffer = np.add(buffer, deathsNew)
            self.dataStore['stateControl'][control]['deathsNew'] = buffer
        return 1

    def getTrack(self, region, day, columns):
        """Get the results for a region by day."""
        result = {}
        tday = datetime.strptime(day, '%m/%d/%y').strftime('%m/%d/%Y')
        code = us_state_abbrev[region]
        for col in columns:
            try:
                result[col] = self.tracking.loc[code].loc[tday][col]
            except:
                result[col] = 0
        return result

    def printTop(self, keys, num):
        """Get top cases by key."""
        for key in keys:
            topCases = OrderedDict(list(self.dataStore[key].items())[0:num])
            print("\nSummary of", key, "Regions")
            for region in topCases.keys():
                self.printSummary(region)

    def printSummary(self, region):
        """Print a summary for the region."""
        control = self.dataStore[region]['control']
        print('[{}-{} - Pop: {}]'.format(region, control[:1], fmtNum(self.dataStore[region]['population'])))
        print("\tcases/today/rate/max/per1000: {}/{}/{:2.2f}%/{:2.2f}%/{}\t".format(fmtNum(self.dataStore[region]['confirmed'][-1:][0]),
                                                                fmtNum(self.dataStore[region]['confirmedNew'][-1:][0]),
                                                                self.dataStore[region]['caseRate'][-1:][0] * 100,
                                                                self.dataStore[region]['maxCaseRate'] * 100,
                                                                int(self.dataStore[region]['casesPerCapita'][-1:][0] * 1000)))
        print("\tDeaths/total/rate/max: {}/{}/{:2.2f}%/{:2.2f}%\t".format(fmtNum(self.dataStore[region]['deaths'][-1:][0]),
                                                               fmtNum(self.dataStore[region]['deathsNew'][-1:][0]),
                                                               self.dataStore[region]['deathRate'][-1:][0] * 100,
                                                               self.dataStore[region]['maxDeathRate'] * 100))
        print("\tIncrease Case/Death: {}/{}".format(self.dataStore[region]['increasingCases'], self.dataStore[region]['increasingDeaths']))
        print("\tTested/Per1000/Hospitalized/Icu/Recovered: {}/{}/{}/{}/{}".format(fmtNum(self.dataStore[region]['totalTests'][-1:][0]),
                                                                        int(self.dataStore[region]['testsPerCapita'] * 1000),
                                                                        fmtNum(self.dataStore[region]['hospitalizedCumulative'][-1:][0]),
                                                                        fmtNum(self.dataStore[region]['onVentilatorCumulative'][-1:][0] + self.dataStore[region]['inIcuCumulative'][-1:][0]),
                                                                        fmtNum(self.dataStore[region]['recovered'][-1:][0])))

    def plotResults(self, keys, data=['confirmed', 'deaths'], num=5,
                    yscale='log',
                    title='Covid-19 - Patient 0: January 21, 2020',
                    smoothed=False, legendText='Aggregated Growth',
                    filterLabel='New'):
        """Plot the results for the period."""
        handles = []
        pos = 0
        colors = ['red', 'magenta', 'blue', 'green', 'cyan', 'yellow', 'black',
                  'orange', 'grey', 'blueviolet', 'gold', 'teal', 'olive',
                  'tan', 'lime', 'skyblue', 'coral', 'maroon', 'pink']
        for key in keys:
            topCases = OrderedDict(list(self.dataStore[key].items())[0:num])
            for region in topCases.keys():
                for field in data:
                    if smoothed is True:
                        ysmoothed = gs1d(self.dataStore[region][field],
                                         sigma=2)
                        label=region + "-" + field
                        plot, = plt.plot(ysmoothed, color=colors[pos],
                                         label=label.replace(filterLabel, ""))
                    else:
                        label = region + "-" + field
                        plot, = plt.plot(self.dataStore[region][field],
                                         color=colors[pos],
                                         label=label.replace((filterLabel, '')))
                    handles.append(plot)
                    pos += 1
        plt.legend(handles=handles, loc='upper left')
        plt.yscale(yscale)
        plt.title(title)
        plt.xlabel("Days\nToday: {}".format(currentDate.strftime("%B %d, %Y")))
        plt.ylabel("US Cases - {}\nTop {} Regions ({})".format(legendText,
                                                               num, yscale))
        plt.savefig(plotPath + 'daily_State{}.png'.format(legendText.replace(' ', '')),
                bbox_inches="tight",
                pad_inches=0.5 + random.uniform(0.0, 0.25))
        plt.show(block=False)
        plt.clf()
        plt.cla()
        plt.close('all')

    def importCsv(self, file, index=[], rename=[], exclude=[]):
        """Import csv data based on index, column(s) to rename/exclude."""
        index = index if len(index) > 0 else self.index
        df = pd.read_csv(file, index_col=index)
        exclude = exclude if len(exclude) > 0 else self.exclude
        if len(exclude) > 0:
            for col in exclude:
                try:
                    del df[col]
                except:
                    continue
        if len(rename) > 0:
            try:
                for col in rename:
                    df.rename({col: rename[col]}, axis='columns')
            except:
                print('Missing:', rename)
        return df

    def downloadJson(self, url, index):
        """Download data in json format, store as a Pandas dataframe."""
        df = pd.read_json(url)
        if len(self.trackingExclude) > 0:
            for col in self.trackingExclude:
                try:
                    del df[col]
                except:
                    continue
        df['dates'] = pd.to_datetime(df.date.astype(str),
                                     format="%Y/%m/%d").dt.strftime('%m/%d/%Y')
        del df['date']
        return df.fillna(0).set_index(index)

    def addListColsDf(self, state, keys=[]):
        """Modify columns in a Pandas Dataframe."""
        if len(keys) < 1:
            return 0
        result = np.array(self.dataStore[state]['positive'])
        for index in range(1, len(keys)):
            result += np.array(self.dataStore[state][keys[index]])
        return result


def fmtNum(num):
    """Formatter to convert int to number with commas by thousand."""
    return format(int(num), ',d')


def statePlot(states=[], key='confirmedNew', smoothed=False, name="default"):
    """Plot data by state."""
    handles = []
    total = None
    for state in states:
        if 'confirmed' in key:
            total = format(int(covidDf.dataStore[state]['confirmed'][-1:][0]),
                           ',d')
            rate = covidDf.dataStore[state]['caseRate'][-1:][0]
        else:
            total = format(int(covidDf.dataStore[state]['deaths'][-1:][0]),
                           ',d')
            rate = covidDf.dataStore[state]['deathRate'][-1:][0]
        if smoothed is False:
            vector = covidDf.dataStore[state][key]
        else:
            vector = gs1d(covidDf.dataStore[state][key], sigma=2)
        label, = plt.plot(vector, label="{}: {}/{:2.2f}%".format(state, total,
                                                                 rate * 100))
        handles.append(label)
    plt.legend(handles=handles)
    plt.title(key.capitalize().replace('new', ' By Day'))
    plt.ylabel('Growth\nRegion: Cases/Rate')
    plt.xlabel('Days: {}'.format(len(covidDf.dataStore[state][key])))
    plt.savefig(plotPath + 'daily_State{}.png'.format(name.replace(' ', '')),
                bbox_inches="tight",
                pad_inches=0.5 + random.uniform(0.0, 0.25))
    plt.show(block=False)
    plt.clf()
    plt.cla()
    plt.close('all')

def statGovPlot(title, yscale, smoothed=False, gname='GovControl'):
    """Plot summary by state government."""
    handles = []
    for party in ['Republican', 'Democratic']:
        for key in ['confirmedNew', 'deathsNew']:
            total = sum(covidDf.dataStore['stateControl'][party][key])
            if smoothed is False:
                vector = covidDf.dataStore['stateControl'][party][key]
            else:
                vector = gs1d(covidDf.dataStore['stateControl'][party][key],
                              sigma=2)
            label, = plt.plot(vector, label="{}-{} Total: {}".format(key.replace('New', ''), party[:1], fmtNum(total)))
            handles.append(label)
    plt.legend(handles=handles)
    plt.yscale(yscale)
    plt.title(title)
    plt.ylabel('Party in Control\nCases/Deaths by Day')
    plt.xlabel('Days: {}'.format(len(vector)))
    plt.savefig(plotPath + 'daily_State{}.png'.format(gname.replace(' ', '')),
                bbox_inches="tight",
                pad_inches=0.5 + random.uniform(0.0, 0.25))
    plt.show(block=False)
    plt.clf()
    plt.cla()
    plt.close('all')

if __name__ == "__main__":
    covidDf = CovidCountryRegion(config)
    startTime = datetime.today()
    covidDf.processing()
    gp = git.cmd.Git('./')
    endTime = datetime.today()
    print("Start:", startTime.strftime("%d/%m/%Y %H:%M:%S"))
    print("End:", endTime.strftime("%d/%m/%Y %H:%M:%S"))
    print('Plot State Government')
    statGovPlot('Covid-19 Pandemic by State Government', yscale='symlog',
                smoothed=True)
    print(gp.add('./plots/*'))
    print(gp.commit('-m', "Upload Daily"))
    print(gp.push())
    print('Plot Aggregate')
    covidDf.plotResults(['currentAggregate'],
                        data=['confirmedNew', 'deathsNew'],
                        yscale='symlog', num=7, smoothed=True)
    covidDf.plotResults(['casesPerCapita'],
                        data=['confirmedNew'],
                        yscale='symlog', num=14, smoothed=True,
                        legendText="Cases Per Capita",
                        filterLabel='-confirmedNew')
    print('Plot Target States')
    statePlot(['Arizona', 'New Jersey', 'Tennessee', 'South Carolina',
                'Georgia', 'Pennsylvania', 'Virginia', 'Maryland', 'Michigan'],
              key='confirmedNew', smoothed=True, name='Focused')
    statePlot(['North Dakota', 'South Dakota', 'Iowa', 'Louisiana', 'Utah',
                'Arkansas', 'Missouri', 'Nebraska', 'Wisconsin', 'Kentucky'],
              key='confirmedNew', smoothed=True, name='Midwest')
    statePlot(['New York', 'California', 'Texas', 'Florida'],
              key='confirmedNew', smoothed=True, name='High')
    print(gp.add('./plots/*'))
    print(gp.commit('-m', "Upload Daily"))
    print(gp.push())
