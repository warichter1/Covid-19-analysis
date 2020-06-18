#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Apr 23 21:04:53 2020

@author: wrichter
"""
# data source: https://github.com/CSSEGISandData/COVID-19.git
# use git clone to create a local copy

import pandas as pd
import git
import datetime as convdate
from datetime import date, datetime
import time
import csv
# import random
import multiprocessing

from CovidDLModelUSStates_v2 import CovidCountryRegion
from CovidDLModelUSStates_v2 import config
from us_state_abbrev import abbrev_us_state
from us_state_abbrev import us_state_abbrev
from us_state_abbrev import stateIndex

print('Check data source for update: https://github.com/CSSEGISandData/COVID-19.git')
g = git.cmd.Git('./COVID-19')
print(g.pull())

csvFile = './US-data-rows.csv'
csvTraining = './US-data-training.csv'
csvTesting = './US-data-testing.csv'
dataPath = './COVID-19/csse_covid_19_data/csse_covid_19_time_series'
confirmedCases = 'time_series_covid19_confirmed_US.csv'
deaths = 'time_series_covid19_deaths_US.csv'
country = 'US'
currentDate = date.today()
projectionDays = 30
deathDays = 3
begin = 10

indexUsState, StateUsIndex = stateIndex()

class ConvertJHUdata:
    def __init__(self, dataPath, confirmed, deaths, country, out, conf={}):
        self.imported = CovidCountryRegion(conf)
        self.defaultExclude = self.imported.exclude
        self.imported.exclude = ['FIPS', 'iso2', 'iso3', 'code3',
                                 'Combined_Key']
        self.imported.index = 'UID'
        self.converted = ['Admin2', 'Province_State', 'Country_Region',
                          'Lat', 'Long_']
        self.daysIndex = []
        self.header = ['Index', 'date', 'UID']
        self.index = 100
        self.rowCount = 0
        self.country = country

        self.imported.importData(path=dataPath, confirmed=confirmed, deathFile=deaths)
        self.getIndex(self.imported.confirmed.keys())
        print("Current Date:", self.daysIndex[-1:][0], "Processing:")
        print('Output File', out)
        print('Begin:', datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
        with open(out, 'w', newline='\n') as writeFile:
            self.writeFile = csv.writer(writeFile, delimiter=',')
            self.writeFile.writerow(self.header)
            for index, row in self.imported.confirmed.reset_index().dropna().set_index('UID').iterrows():
                self.processDfRow(index, row)
                self.rowCount += 1
        print('End:', datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
        print('Converted:', format(self.rowCount, ',d'), 'rows')
        print('Processing Complete\nRecords:', format(self.index - 101, ',d'))

    def getIndex(self, keys):
        for key in keys:
            if key.count('/') == 2:
                self.daysIndex.append(key)
            else:
                self.header.append(key)
        self.header.append('confirmed')
        self.header.append('deaths')

    def processDfRow(self, index, row):
        rowTemplate = []
        for cell in self.header:
            if cell == 'UID':
                rowTemplate.append(index)
            elif not cell in ['Index', 'date', 'confirmed', 'deaths']:
                rowTemplate.append(row[cell])
        if not index == 'nan':
            for day in self.daysIndex:
                dayInfo = [row[day], self.imported.deaths.loc[index][day]]
                self.writeFile.writerow([self.index, day] + rowTemplate + dayInfo)
                self.index += 1

    def importStates(self):
        print('Importing States')
        print('Begin:', datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
        self.imported.resetImportDefs()
        self.imported.processing(printStatus=False)
        print('End:', datetime.now().strftime("%d/%m/%Y %H:%M:%S"))


class CovidExport:
    def __init__(self, source):
        self.source = source.dataStore
        self.states = self.source['currentCaseRate'].keys()
        self.days = source.daysIndex
        self.trainingKeys = [key for key in self.source.keys() if not key in self.states]
        self.dlKeys = [key for key in self.source['Virginia'].keys() if not key in ['positive', 'negative', 'pending']]
        self.dlKeys = [key for key in self.source['Virginia'].keys() if isinstance(self.source['Virginia'][key], list)]

    def processStates(self, out, dataType):
        print('Exporting States:', dataType, 'data')
        print('Filename:', out)
        print('Begin:', datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
        buffer = self.dlKeys if dataType == "training" else self.trainingKeys
        buffer = ['date', 'timestamp', 'state', 'stateId'] + buffer if dataType == "training" else ['state', 'stateId'] + buffer
        with open(out, 'w', newline='\n') as writeFile:
            self.writeFile = csv.writer(writeFile, delimiter=',')
            self.writeFile.writerow(buffer)  # header
            for state in self.states:
                if dataType == 'training':
                    self.exportDetails(state)
                    # self.writeFile.writerow(self.dlKeys)
                elif dataType == 'testing':
                    self.exportSummaries(state)
                else:
                    # self.writeFile.writerow(self.trainingKeys)
                    print('Unknown Data Type')
        print('End:', datetime.now().strftime("%d/%m/%Y %H:%M:%S"))


    def exportDetails(self, state):
        # print('training:', state)
        for i in range(len(self.days)):
            # print(self.days[i])
            self.buffer = [self.days[i], getTimestamp(self.days[i]), state, StateUsIndex[state]]
            for col in self.dlKeys:
                if not col == 'date':
                    # print(col, i)
                    self.buffer.append(self.source[state][col][i])
            self.writeFile.writerow(self.buffer)

    def exportSummaries(self, state):
        # print('Testing')
        self.buffer = [state, StateUsIndex[state]]
        for col in self.trainingKeys:
            print(state, col)
            self.buffer.append(self.source[col][state])
        self.writeFile.writerow(self.buffer)

    def fieldLen(self, state='Alabama', dataType="training"):
        if dataType == 'training':
            header = self.dlKeys
        else:
            header = self.trainingKeys
        for field in header:
            print("{}: {}: {}".format(field, type(self.source[state][field]),
                                      len(self.source[state][field])))


def getTimestamp(day):
    return time.mktime(convdate.datetime.strptime(day, "%m/%d/%y").timetuple())


class CovidImport:
    def __init__(self, source, index, exclude=[]):
        self.importCsv(source, index, exclude)

    def importCsv(self, file, index, exclude):
        print(file, index, exclude)
        self.df = pd.read_csv(file, index_col=index)
        if len(exclude) > 0:
            for col in exclude:
                del self.df[col]
        print('file:', file, "imported into var: df")


if __name__ == "__main__":
    print("Convert data")
    jobs = [] # list of jobs
    # jobs_num = 5 # number of workers
    convertJHU = ConvertJHUdata(dataPath, confirmedCases, deaths,
                                country, csvFile, conf=config)
    covidDF = CovidImport(csvFile, 'Province_State', ['Country_Region',
                                                          'Index'])
    convertJHU.importStates()

    cvExport = CovidExport(convertJHU.imported)

    pid1 = multiprocessing.Process(target=cvExport.processStates, args=(csvTraining,'training',))
    jobs.append(pid1)
    pid2 = multiprocessing.Process(target=cvExport.processStates, args=(csvTesting,"testing",))
    jobs.append(pid2)
    pid1.start()
    pid2.start()



