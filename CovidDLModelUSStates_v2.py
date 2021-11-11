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
import os
import psutil
from datetime import date
from datetime import datetime
from collections import OrderedDict
# import copy
from copy import copy
import operator
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.ndimage.filters import gaussian_filter1d as gs1d
import git
import random
import json
from memory_profiler import profile
from matplotlib.font_manager import FontProperties

from us_state_abbrev import us_state_abbrev
from CovidData import CovidData

g = git.cmd.Git('./COVID-19')
print(g.pull())

dataPath = './COVID-19/csse_covid_19_data/csse_covid_19_time_series'
plotPath = './plots/'
trackingUrl = "https://covidtracking.com/api/v1/states/daily.json"
# trackingUrl = 'https://api.covidtracking.com/v1/states/current.json'
trackingIndex = ['state', 'dates']
confirmedCases = 'time_series_covid19_confirmed_US.csv'
deaths = 'time_series_covid19_deaths_US.csv'
censusData = './nst-est2019-alldata.csv'
stateGovData = './stateOffices.csv'
educationRisk = './educational_attainment.csv'
countyElectionData = './president_county_candidate.csv'
countyElectionWinner = './winning_president_county_candidate.csv'
results2020 = 'partyByCountry2020.json'
stateGovIndex = 'Region'
stateGovExclude = ['2016 presidential election', 'Senior U.S. Senator',
                   'Junior U.S. Senator', 'U.S. House of Representatives',
                   'US House Count']
censusIndex = 'NAME'
censusPopulation = 'POPESTIMATE2019'
censusExclude = ['SUMLEV', 'REGION', 'DIVISION', 'STATE']

config = {'jhuPath': dataPath, 'jhuConfirmed': confirmedCases,
          'jhuDeaths': deaths, 'medUrl': trackingUrl,
          'medIndex': trackingIndex, 'educationRisk': educationRisk,
          'censusData': censusData, 'censusIndex': censusIndex,
          'censusExclude': censusExclude, 'censusPopKey': censusPopulation,
          'stateGovData': stateGovData, 'stateGovIndex': stateGovIndex,
          'countyElectionData': countyElectionData,
          'countyElectionwin': countyElectionWinner,
          'stateGovExclude': stateGovExclude,
          'results2020': results2020}

country = 'US'
currentDate = date.today()
projectionDays = 30
deathDays = 3
begin = 10

# test = covidDf.importCsv('./' + countyElectionData,
#                                         index=['Province_State', 'County'],
#                                         rename={'state': 'Province_State', 'county': 'County'})

class CovidCountryRegion:
    """Class to parse and analize by country and region."""

    def __init__(self, config={}):
        """Initialize default variabled in class CovidCountryRegion."""
        self.dataStore = OrderedDict()
        self.dataStore['currentAggregate'] = {}
        self.dataStore['currentCaseRate'] = {}
        self.dataStore['currentDeathRate'] = {}
        self.dataStore['stateControl'] = {'Republican': {'confirmedNew': None,
                                                         'deathsNew': None,
                                                         'confirmedCounty': [],
                                                         'deathsCounty': []},
                                          'Democratic': {'confirmedNew': None,
                                                         'deathsNew': None,
                                                         'confirmedCounty': [],
                                                         'deathsCounty': []}}
        self.dataStore['testsPerCapita'] = {}
        self.dataStore['casesPerCapita'] = {}
        self.config = config

        self.index = ['Province_State', 'Admin2']
        self.exclude = ['Country_Region', 'UID', 'iso2', 'iso3', 'Last_Update',
                        'Last Update', 'Latitude', 'Lat_', 'Lat', 'Longitude',
                        'Long_', 'Active', 'Combined_Key', 'FIPS', 'code3',
                        'Population', #'Admin2'
                        ]
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
        self.partyByCounty = {}
        self.partyByCounty['confirmed'] = {'Republican': {},'Democratic': {}}
        self.partyByCounty['deaths'] = {'Republican': {},'Democratic': {}}
        self.dataStore['educationLevel'] = {'noHighSchool': {'confirmed': {},
                                                            'deaths': {}}, 
                                            'highSchool': {'confirmed': {},
                                                                'deaths': {}}, 
                                            'bachelors': {'confirmed': {},
                                                                'deaths': {}}, 
                                            'grad': {'confirmed': {},
                                                                'deaths': {}}}
        self.dataStore['educationParty'] = {'confirmed': {'Republican': {},
                                                          'Democratic': {}},
                                            'deaths': {'Republican': {},
                                                       'Democratic': {}}} 
        self.eduRisk = {}
        self.printStatus = False
        self.daysIndex = []
        self.regions = []
        self.confirmed = []
        self.deaths = []
        self.censusPop = None
        self.tracking = None
        self.stateGov = {}
        self.fileText = ''
        self.textPath = './data'

    def resetImportDefs(self):
        """Reset import to defaults."""
        self.index = self.defaultIndex
        self.exclude = self.defaultExclude

    # @profile
    def processing(self, printStatus=True):
        """All import and configuration is complete, process the data."""
        self.printStatus = printStatus
        self.importData()
        self.daysIndex = list(self.confirmed.keys())
        if 'County' in self.daysIndex:
            self.daysIndex.remove('County')
        printText = "Current Date: {} Processing:".format(self.daysIndex[-1:][0])
        print(printText)
        self.fileText += (printText + '\n')
        for region in self.regions:
            self.processRegionResults(region)
        self.getAggregate()
        self.updateCountyParties()
        if printStatus:
            self.sortTopDict('currentCaseRate')
            self.sortTopDict('currentDeathRate')
            self.sortTopDict('casesPerCapita')
            self.sortTopDict('testsPerCapita', reverse=False)
            self.printTop(['currentAggregate', 'currentCaseRate',
                           'casesPerCapita',
                           'currentDeathRate', 'testsPerCapita'], 5)
            self.writeData('stateDetails.txt', self.fileText)

    def changeDfIndex(self, df, index):
        """Change a dataframe index."""
        df.reset_index(inplace=True)
        df.set_index(['Province_State'], inplace=True)
        return df

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
        self.confirmed = self.importCsv(filePath + '/' + file,
                                        index=['Province_State'],
                                        rename={'Admin2': 'County'})
        self.confirmed.fillna(0, inplace=True)
        self.regions = sorted(set(self.confirmed.index))
        file = self.config['jhuDeaths'] if deathFile is None else deathFile
        self.deaths = self.importCsv(filePath + '/' + file,
                                     index=['Province_State'],
                                     rename={'Admin2': 'County'})
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
        self.educationLevelState()  # Load Educational data

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
        self.eduRiskCalc(region)
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

    def educationLevelState(self):
        cd = CovidData()
        self.attainmentSalary = cd.rate['educationAttainment']
        risk = cd.rate['educationRisk']
        eduRisk = self.importCsv(config['educationRisk'], 
                                 index=['Province_State'])
        eduRisk['noHighSchool'] = (eduRisk['No graduate'] + risk['noHighSchool'])/2
        eduRisk['highSchool'] = (eduRisk['High School Only'] + risk['highSchool'])/2
        eduRisk['bachelors'] = (eduRisk['Bachelor only'] + risk['bachelors'])/2
        eduRisk['grad'] = (eduRisk['Advanced only'] + risk['grad'])/2
        self.eduRisk = eduRisk
        
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
        print("Check Party for:", region)
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

    def countyByParty(self, indexUpdate=[]):
        """Breakdown the JHU data by county and party."""
        filename = self.config['countyElectionwin']
        exportname = 'partyByCountry2020.json'
        dfWin = pd.read_csv(filename, index_col=None)
        dfWin.set_index(['Province_State', 'County'], inplace=True)
        dfWin.sort_index(inplace=True)
        dfWin['Party'].replace('REP', 'Republican', regex=True, inplace=True)
        dfWin['Party'].replace('DEM', 'Democratic', regex=True, inplace=True)
        # indexWin = list(dict.fromkeys(dfWin.index.values.tolist()))
        self.confirmed.reset_index(inplace=True)
        self.confirmed.set_index(['Province_State', 'County'], inplace=True)
        self.deaths.reset_index(inplace=True)
        self.deaths.set_index(['Province_State', 'County'], inplace=True)
        if len(indexUpdate) > 0:  # Unpdate existing
            print('Update existing county list')
            daysIndex = indexUpdate
        else:  # Export new
            print('Create existing county list')
            daysIndex = self.daysIndex
        indexJHU = list(dict.fromkeys(self.confirmed.index.values.tolist()))
        targetState = 'NA'
        for day in daysIndex:  # prefill by day to calculate
            self.partyByCounty['confirmed']['Republican'][day] = 0
            self.partyByCounty['confirmed']['Democratic'][day] = 0
            self.partyByCounty['deaths']['Republican'][day] = 0
            self.partyByCounty['deaths']['Democratic'][day] = 0
        for inx in indexJHU:
            # print("Processing:", inx)
            if not targetState == inx[0]:  # Pick a new state
                control = self.getStateGovStats(inx[0])
                targetState = inx[0] 
            try:
                countyWin = dfWin.loc[inx]['Party'][0]
            except:
                countyWin = control
                print("County: {} not found, using state default: {}".format(inx[1], countyWin))
            # print("Processing:", inx, countyWin)
            for day in daysIndex:
                try:
                    self.partyByCounty['confirmed'][countyWin][day] += self.confirmed.loc[inx][day]
                    self.partyByCounty['deaths'][countyWin][day] += self.deaths.loc[inx][day]
                except:
                    continue
        self.exportDaysJson(self.partyByCounty, exportname + '1')
        self.importDaysJson(exportname + '1')

    def exportDaysJson(self, data, exportFile):
        print("Exporting counties by Party:", exportFile)
        for inxKeys in data:  # Convert numeric totals to string
            for inxParty in data[inxKeys].keys():
                for inxDay in data[inxKeys][inxParty].keys():
                    data[inxKeys][inxParty][inxDay] = str(data[inxKeys][inxParty][inxDay])
        with open(exportFile, "w") as outfile:
            json.dump(self.partyByCounty, outfile)
        print('Export Complete')

    def importDaysJson(self, importFile):
        print("Importing counties by Party:", importFile)
        with open(importFile, "r") as infile:
            data = json.loads(infile.read())
        for inxKeys in data:  # Convert string totals to int
            for inxParty in data[inxKeys].keys():
                for inxDay in data[inxKeys][inxParty].keys():
                    data[inxKeys][inxParty][inxDay] = int(data[inxKeys][inxParty][inxDay])
        self.partyByCounty = data

    def updateCountyParties(self, importFile=None):
        if importFile is None:
            importFile = self.config['results2020']
        self.importDaysJson(importFile)
        dataInx = list(list(self.partyByCounty['confirmed']['Republican'].keys()))
        diffInx = diff(dataInx, self.daysIndex)
        diffInx.sort(key=lambda date: datetime.strptime(date, '%m/%d/%y'))
        if len(diffInx) > 0:
            print("County days to process:", diffInx)
            self.countyByParty(indexUpdate=diffInx)
            for party in ['Republican', 'Democratic']:
                for key in ['confirmed', 'deaths']:
                    buffer = list(self.partyByCounty[key][party].values())
                    self.dataStore['stateControl'][party][key+'County'] = [buffer[i] - buffer[i-1] if buffer[i] - buffer[i-1] >= 0 else 0 for i in range(1,len(buffer) -1)]
        # return self.partyByCounty

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
            printText = "\nSummary of {} Regions".format(key)
            print(printText)
            self.fileText += (printText + '\n')
            for region in topCases.keys():
                self.printSummary(region)

    def printSummary(self, region):
        """Print a summary for the region."""
        control = self.dataStore[region]['control']
        printText = '[{}-{} - Pop: {}]\n'.format(region, control[:1], fmtNum(self.dataStore[region]['population']))
        printText += "\tcases/today/rate/max/per1000: {}/{}/{:2.2f}%/{:2.2f}%/{}\t\n".format(fmtNum(self.dataStore[region]['confirmed'][-1:][0]),
                                                                fmtNum(self.dataStore[region]['confirmedNew'][-1:][0]),
                                                                self.dataStore[region]['caseRate'][-1:][0] * 100,
                                                                self.dataStore[region]['maxCaseRate'] * 100,
                                                                int(self.dataStore[region]['casesPerCapita'][-1:][0] * 1000))
        printText += "\tDeaths/total/rate/max: {}/{}/{:2.2f}%/{:2.2f}%\t\n".format(fmtNum(self.dataStore[region]['deaths'][-1:][0]),
                                                               fmtNum(self.dataStore[region]['deathsNew'][-1:][0]),
                                                               self.dataStore[region]['deathRate'][-1:][0] * 100,
                                                               self.dataStore[region]['maxDeathRate'] * 100)
        printText += "\tIncrease Case/Death: {}/{}\n".format(self.dataStore[region]['increasingCases'], self.dataStore[region]['increasingDeaths'])
        printText += "\tTested/Per1000/Hospitalized/Icu/Recovered: {}/{}/{}/{}/{}".format(fmtNum(self.dataStore[region]['totalTests'][-1:][0]),
                                                                        int(self.dataStore[region]['testsPerCapita'] * 1000),
                                                                        fmtNum(self.dataStore[region]['hospitalizedCumulative'][-1:][0]),
                                                                        fmtNum(self.dataStore[region]['onVentilatorCumulative'][-1:][0] + self.dataStore[region]['inIcuCumulative'][-1:][0]),
                                                                        fmtNum(self.dataStore[region]['recovered'][-1:][0]))
        print(printText)
        self.fileText += (printText + '\n')

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

    def importCsv(self, file, index=[], rename={}, exclude=[]):
        """Import csv data based on index, column(s) to rename/exclude."""
        index = index if len(index) > 0 else self.index
        df = pd.read_csv(file, index_col=None)
        exclude = exclude if len(exclude) > 0 else self.exclude
        if len(exclude) > 0:
            for col in exclude:
                try:
                    del df[col]
                except:
                    continue
        if len(rename) > 0:
            try:
                df.rename(columns=rename, inplace=True)
            except:
                print('Missing:', rename)
        df.set_index(index, inplace=True)
        df.sort_index(inplace=True)

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

    def writeData(self, filename, text):
        """Write the results of a run in Text to Filename."""
        print('Writing:', os.path.join(self.textPath, filename))
        with open(os.path.join(self.textPath, filename), "w") as writeToFile:
            writeToFile.writelines(text)

    def addListColsDf(self, state, keys=[]):
        """Modify columns in a Pandas Dataframe."""
        if len(keys) < 1:
            return 0
        result = np.array(self.dataStore[state]['positive'])
        for index in range(1, len(keys)):
            result += np.array(self.dataStore[state][keys[index]])
        return result

    def eduRiskCalc(self, region):
        levels = list(self.dataStore['educationLevel'].keys())
        risk = {}
        try:
            for level in levels:
                risk[level] = self.eduRisk[level][region]
        except:
            print('Region:', region, 'not found')
            return 0  # do not continue if the region does not exist    
        confirmed_1 = 0
        deaths_1 = 0
        for day in self.daysIndex:
            confirmed = sum(self.confirmed.loc[region][day])
            deaths = sum(self.deaths.loc[region][day])
            for level in levels:   
                if region == self.regions[0]:  # prefill by day to calculate 
                    self.dataStore['educationLevel'][level]['confirmed'][day] = 0
                    self.dataStore['educationLevel'][level]['deaths'][day] = 0
                else:
                    today = confirmed - confirmed_1
                    self.dataStore['educationLevel'][level]['confirmed'][day] += today*risk[level]
                    today = deaths - deaths_1
                    self.dataStore['educationLevel'][level]['deaths'][day] += today*risk[level]
            confirmed_1 = copy(confirmed)
            deaths_1 = copy(deaths)
        if region == self.regions[-1:][0]:
            print("Finalize Education Levels")
            for level in levels:
                buffer = list(self.dataStore['educationLevel'][level]['confirmed'].values())
                buffer = [int(i + .5) for i in buffer]
                self.dataStore['educationLevel'][level]['confirmed'] = buffer
                buffer = list(self.dataStore['educationLevel'][level]['deaths'].values())
                buffer = [int(i) for i in buffer]        
                self.dataStore['educationLevel'][level]['deaths'] = buffer
 
            # self.dataStore['educationParty'] = {'confirmed': {'Republican': {},
            #                                                   'Democratic': {}},
            #                                     'deaths': {'Republican': {},
            #                                                'Democratic': {}}} 
            # self.rate['eduPartyDR'] = {'noHighSchool': [46, .54],
            #                            'highSchool': [.46, .54],
            #                            'whiteHS': [.59, .33],
            #                            'bachelors': [.51, .47],
            #                            'someCollege': [.47, .39],
            #                            'grad': [.62, .37],
            #                            'postGrad': [.62, .37]}
            
def diff(li1, li2, exclude=[]):
    """Return the difference of 2 lists, optional exclude unwanted items."""
    result = list(set(li1) - set(li2)) + list(set(li2) - set(li1))
    if len(exclude) > 0:
        for item in exclude:
            result.remove(item)
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
    font = FontProperties(family='ubuntu',
                          weight='bold',
                          style='oblique', size=6.5)
    for party in ['Republican', 'Democratic']:
        for key in ['confirmedNew', 'deathsNew',#]:
                    'confirmedCounty', 'deathsCounty']:
            print('Processing State Party ({}): {}'.format(party, key))
            total = sum(covidDf.dataStore['stateControl'][party][key])
            if smoothed is False:
                vector = covidDf.dataStore['stateControl'][party][key]
            else:
                vector = gs1d(covidDf.dataStore['stateControl'][party][key],
                              sigma=2)
            label, = plt.plot(vector, label="{}-{} Total: {}".format(key.replace('New', ' by State').replace('County', ' by County'), party[:1], fmtNum(total)))
            handles.append(label)
    plt.legend(handles=handles, prop=font)
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

def eduRiskPlot(data, title, yscale=None, smoothed=False, replace=[], gname="educationRisk"):
    """Summarize the affect of education on risk."""
    handles = []
    font = FontProperties(family='ubuntu',
                          weight='bold',
                          style='oblique', size=6.5)
    for level in data.keys():
        for key in ['confirmed', 'deaths']:
            total = sum(data[level][key])
            print("Processing education level:", level, key)
            if smoothed is False:
                vector = data[level][key]
            else:
                vector = gs1d(data[level][key], sigma=2)  
            label, = plt.plot(vector, label="{}-{} Total: {}".format(level, key, fmtNum(total)))
            handles.append(label)           
  
    plt.legend(handles=handles, prop=font)
    if yscale is not None:
        plt.yscale(yscale)
    plt.title(title)
    plt.ylabel('Educatiion level Risk\nCases/Deaths by Day')
    plt.xlabel('Days: {}'.format(len(vector)))
    plt.savefig(plotPath + 'daily_edrisk{}.png'.format(gname.replace(' ', '')),
                bbox_inches="tight",
                pad_inches=0.5 + random.uniform(0.0, 0.25))
    plt.show(block=False)
    plt.clf()
    plt.cla()
    plt.close('all')

              
def calcWin2020(filename):
    df = pd.read_csv(filename, index_col=None)
    df.rename(columns={'state': 'Province_State', 'county': 'County'}, inplace=True)
    df.set_index(['Province_State', 'County'], inplace=True)
    df.sort_index(inplace=True)
    index = list(dict.fromkeys(df.index.values.tolist()))
    outDf =  pd.DataFrame(columns=['Province_State','County','Party','TotalVotes','WinningVotes'])
    for i in range(len(index)):
        county = df.loc[index[i]]
        winningVotes = max(county['total_votes'])
        totalVotes = sum(county['total_votes'])
        winner = county.where(county['total_votes']==winningVotes)['party'][0]
        outDf = outDf.append({'Province_State': index[i][0],
                              'County': index[i][1].replace(' County', '').replace(' city', ''),
                              'Party': winner,
                              'TotalVotes': totalVotes,
                              'WinningVotes': winningVotes},
                             ignore_index = True)
        outDf.to_csv(filename.replace('/', '/winning_'))



    
if __name__ == "__main__":
    covidDf = CovidCountryRegion(config)
    startTime = datetime.today()
    covidDf.educationLevelState()  # Load Educational data
    covidDf.processing()
    gp = git.cmd.Git('./')
    endTime = datetime.today()
    print("Start:", startTime.strftime("%d/%m/%Y %H:%M:%S"))
    print("End:", endTime.strftime("%d/%m/%Y %H:%M:%S"))
    print('Plot State Government')
    statGovPlot('Covid-19 Pandemic by State Government', yscale='symlog',
                smoothed=True)
    eduRiskPlot(covidDf.dataStore['educationLevel'], 
                'Covid-19 Pandemic by Education Level', yscale='symlog',
                smoothed=True)
    # statGovPlot(covidDf.dataStore['educationLevel'], 
    #             'Covid-19 Pandemic by Education Level', yscale='symlog',
    #             smoothed=True)
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
    statePlot(['New York', 'California', 'Texas', 'Florida', 'Louisiana'],
              key='confirmedNew', smoothed=True, name='High')
    print(gp.add('./plots/*'))
    print(gp.add('./data/*'))
    print(gp.commit('-m', "Upload Daily"))
    print(gp.push())
