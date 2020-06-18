#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Mar 27 18:16:15 2020

@author: wrichter
"""

import pandas as pd
import matplotlib.pyplot as plt
from datetime import date
from math import sqrt
from math import pi
import git
from os import listdir
from os.path import isfile, join
import sys
import glob
from pprint import pprint
from copy import deepcopy
from collections import OrderedDict

from us_state_abbrev import abbrev_us_state

# from CovidDLModel import importCsv

g = git.cmd.Git('./COVID-19')
print(g.pull())

dataPath = './COVID-19/csse_covid_19_data/csse_covid_19_daily_reports'
country = 'US'
currentDate = date.today()
projectionDays = 30
deathDays = 3
begin = 10


class CovidCountryRegion:
    def __init__(self, dataPath, country):
        self.dataStore = OrderedDict()
        self.cases = OrderedDict()
        self.growthRates = OrderedDict()
        self.dailyDeaths = OrderedDict()
        self.deathRate = OrderedDict()
        self.caseRate = OrderedDict()
        self.country = country
        self.index = ['Country/Region', 'Country_Region']
        self.exclude = ['Last_Update', 'Last Update', 'Latitude',
                        'Lat_', 'Lat', 'Longitude', 'Long_', 'Active',
                        'Combined_Key', 'FIPS']
        self.rename = {'Province_State': 'Province/State',
                       'Country_Region': 'Country/Region',}
        self.regionKey = 'Province/State'
        self.subkeys = {'Confirmed': 0, 'Deaths': 0}
        self.importData()
        self.previousDay = ""

    def importData(self):
        self.regionFiles = sorted(glob.glob(dataPath + '/*.csv'))
        total = 0
        for file in self.regionFiles:
            # print(file)
            self.region, self.ind = self.importCsv(file)
            self.region.fillna(0, inplace=True)
            # print(self.regions)
            self.region.rename(columns={'Province_State': self.regionKey},
                                      inplace=True)
            # print("Checked: {}".format(self.regionKey))
            try:
                # print("try Unique")
                self.checkDataStore(self.region[self.regionKey].unique())
                # print("Value:", self.region.keys())
            except:
                if '01-22-2020' in file:  # outlier, first US case
                    self.addStateInDataStore('Washington')
                elif '01-23-2020' in file:  # outlier, first US case
                    print("Special Case")
                else:
                    # print("try no unique")
                    self.region.rename({'Province_State', self.regionKey}, axis='columns',
                                      inplace=True)
                    # print("Value Except:", self.regionKey, self.region.keys())
                    self.checkDataStore(self.region[self.regionKey])
                    # print('checked')

            self.getDayResults(file)
            total += 1
            # print("Import complete: {}".format(file))
        print("Processed {} Files".format(total))

    def getDayResults(self, day):
        # print("GetDayResults")
        day = day.split('/')[-1:][0].replace('.csv', '')
        print('Import Day:', day)
        for dsKey in self.dataStore.keys():
            if day in ['01-22-2020', '01-23-2020']:
                for key in self.subkeys.keys():
                    self.dataStore[dsKey][key][day] = deepcopy(self.subkeys[key])
                    if dsKey == 'Washington' and key == 'Confirmed':
                        self.dataStore[dsKey][key]['Confirmed'] = 1

            else:
                results = self.region.loc[self.region[self.regionKey] == dsKey].sum()
                for key in self.subkeys.keys():
                    self.dataStore[dsKey][key][day] = int(results[key])
        # print("Complete: GetDayResults")

    def processRegionResults(self, region):
        day = 1
        lastDay = 1
        # limits = []
        confirmed = self.dataStore[region]['Confirmed']
        deaths = self.dataStore[region]['Deaths']
        for day in sorted(confirmed):
            print(day, confirmed[day])
            if lastDay - 1 > 0:
                self.caseRate[region] = confirmed[day] / lastDay - 1
            self.growthRates[region].append(self.caseRate[region])
            if confirmed[day] > 0:
                self.deathRate[region].append(deaths[day] / confirmed[day])
            self.cases[region].append(confirmed[day])
            self.dailyDeaths[region].append(deaths[day])



    def importCsv(self, file, rename=[]):
        # print("import: {}, country: {}".format(file, self.country))
        for ind in self.index:
            try:
                cv = pd.read_csv(file, index_col=ind)
                # print("Found Index:", ind)
                continue
            except:
                # print('Failed:', ind)
                continue
        if len(self.exclude) > 0:
            for col in self.exclude:
                try:
                    del cv[col]
                except:
                    continue
                    # print('No Col:', col)
        if len(rename) > 0:
            try:
                for col in rename:
                    cv.rename({col: rename[col]}, axis='columns')
            except:
                print('Missing:', col)
        # print("Completed importCsv:", file)
        return (cv.loc[self.country], ind)

    def checkDataStore(self, data):
        # print('CheckDS')
        current = self.dataStore.keys()
        for region in data:
            region = self.getRegion(region)
            if not region in current and region not in ['Recovered', 'US']:
                self.addStateInDataStore(region)
        # print('CheckDS Complete')

    def addStateInDataStore(self, region):
        print("Add:", region)
        self.dataStore[region] = {}
        self.cases[region] = []
        self.growthRates[region] = []
        self.dailyDeaths[region] = []
        self.deathRate[region] = []
        self.caseRate[region] = []
        if len(self.subkeys) > 0:
            for key in self.subkeys:
                self.dataStore[region][key] = {}

    def getRegion(self, text):
        if 'Diamond Princess' in text:
            return 'Diamond Princess'
        if 'Virgin Islands' in text:
            return 'Virgin Islands'
        if 'Chicago' in text:
            return 'Illinois'
        if len(text) < 2:
            print(text)
            print(self.regions)
            sys.exit(1)
        if 'U.S.' in text:
            return text.split(',')[0].strip()
        text = text.replace('.', '')
        if ',' in text:
            result = text.split(',')[1].strip()
            if ' (' in result:
                result = result.split(' (')[0].strip()
            return abbrev_us_state[result]
        else:
            return text


if __name__ == "__main__":
    # dailyCases = '03-17-2020.csv'
    # dailyCases = '03-25-2020.csv'
    dailyCases = '03-27-2020.csv'

    usFile = "{}/{}".format(dataPath, dailyCases)

    covidDf = CovidCountryRegion(dataPath, country)
    pprint(covidDf.dataStore.keys())

    # onlyfiles = [f for f in listdir(dataPath) if isfile(join(dataPath, f))]
