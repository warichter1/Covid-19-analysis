#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Mar 22 16:18:30 2020

@author: wrichter
"""

# data source: https://github.com/CSSEGISandData/COVID-19.git
# use git clone to create a local copy

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import date
from datetime import datetime
from math import sqrt
from math import pi
import git

g = git.cmd.Git('./COVID-19')
print(g.pull())

dataPath = './COVID-19/csse_covid_19_data/csse_covid_19_time_series/'
# confirmedCases = 'time_series_covid19_confirmed_US.csv'
confirmedCases = 'time_series_covid19_confirmed_global.csv'
deathsFile = 'time_series_covid19_deaths_global.csv'
# deathsFile = 'time_series_covid19_deaths_US.csv'
index = 'Country/Region'
excludeFields = ['Lat', 'Long', 'Province/State']
country = 'US'
currentDate = date.today()
timestamp = datetime.timestamp(datetime.now())
oneDay = 60 * 60 * 24
projectionDays = 106
deathDays = 3
begin = 10


def importCsv(file, country, index, exclude):
    cv = pd.read_csv(file, index_col=index)
    if len(exclude) > 0:
        for col in exclude:
            del cv[col]
    return cv.loc[country]


def limit(begin, day, rate):
    if day >= begin:
        return 1/(sqrt((2*pi)))*rate*day
    return rate


def calcChange(values, type=None):
    if type is not None:
        if type == 'avg2':
            return [(values[-1:][0] - values[-2:][0]) for i in range(len(values))]
        elif type == 'avgAll':
            return [(sum(values) / len(values)) for i in range(len(values))]
        elif type == 'today':
            return [0 for i in range(len(values))]
        elif type == 'avgDiff':
            return [(sum(np.diff(values)) / len(np.diff(values))) for i in range(len(values))]
    return np.diff(values) - 1
    # return np.exp(np.diff(np.log(values))) - 1


# Ugly I know, just a simple plot
def plotUS(day, today, cdate, currentDate, cases, caseRate, growthRates,
           deaths, dailyDeaths, deathRate, showTotal=False):
    labels = []
    if showTotal is True:
        label, = plt.plot(cases,  color='red', label='Cases')
        labels.append(label)
        label, = plt.plot(deathRate, color='blue', label='Mortality')
        label, = plt.plot(growthRates, color='magenta', label='Growth')
        labels.append(label)
    label, = plt.plot(dailyDeaths, color='blue', label='Daily Deaths')
    labels.append(label)
    label, = plt.plot(dailyCases, color='magenta', label='Daily Cases')
    labels.append(label)
    label = plt.axvline(today, color='green', label='Projection->')
    labels.append(label)
    plt.legend(handles=labels)
    plt.yscale('log')
    plt.title('Covid-19 - "Confirmed" Patient 0: January 21, 2020')
    plt.xlabel("Time ({} Days)\nGrowth per Last Period: {:2.2f}%\nToday: {}".format(day, caseRate * 100, currentDate.strftime("%B %d, %Y")))
    plt.ylabel(" US Cases (Mil): {}\nMortality: {} (Rate: {:2.2f}%)".format(format(int(cases[day-2]), ',d'),
                                                               format(int(deaths[cdate]), ',d'), float(deathRate[-1:][0] * 100)))



if __name__ == "__main__":
    file = "{}/{}".format(dataPath, confirmedCases)
    us = importCsv(file, country, index, excludeFields)
    file = "{}/{}".format(dataPath, deathsFile)
    deaths = importCsv(file, country, index, excludeFields)
    cases = []
    growthRates = []
    dailyCases = []
    dailyDeaths = []
    deathRate = []
    totalDeaths = []
    day = 1
    lastDay = 1
    yesterday = 0
    yesterdayDeaths = 0
    # rateChange = 'avg2'
    # rateChange = 'avgAll'
    # rateChange = None
    # rateChange = 'avgDiff'
    rateChange = 'today'
    for cdate in us.keys():
        caseRate = us[cdate] / lastDay - 1
        growthRates.append(caseRate)
        deathRate.append(deaths[cdate] / us[cdate])
        cases.append(us[cdate])
        now = us[cdate] - yesterday
        nowDeaths = deaths[cdate] - yesterdayDeaths
        dailyCases.append(now)
        yesterday = us[cdate]
        yesterdayDeaths = deaths[cdate]
        dailyDeaths.append(nowDeaths)
        totalDeaths.append(deaths[cdate])
        print("Day: {} ({}) - Cases/today/Infection Rate: {}/{}/{:2.2f}% - Mortality/Today/Rate: {}/{}/{:2.2f}% ".format(day, cdate, format(us[cdate], ',d'), format(now, ',d'), caseRate * 100, format(deaths[cdate], ',d'), format(nowDeaths, ',d'), deathRate[-1:][0] * 100))
        lastDay = us[cdate]
        today = day
        day += 1
    avgDeathRate = deathRate[-1:][0]
    # avgDeathRate = sum(deathRate[-deathDays:]) / deathDays
    drate = calcChange(deathRate[-deathDays:], rateChange)
    grate = calcChange(growthRates[-deathDays:], rateChange)
    projDay = 0

    print("Projection: {} days".format(projectionDays))
    for day in range(day, day + projectionDays):
        if caseRate + grate[projDay] <= 0:
            grate = calcChange(growthRates[-deathDays:], rateChange)
            # print('reset')
        # else:
        caseRate = abs(caseRate + grate[projDay])
        # print(grate)
        current = int(cases[-1:][0] * (1 + caseRate))
        cases.append(current)
        now = current - yesterday
        dailyCases.append(now + (now - dailyCases[-3:][0])*.97)
        yesterday = current
        growthRates.append(caseRate)
        dailyDeaths.append(int(now * avgDeathRate) - dailyDeaths[-4:][0])
        if avgDeathRate + drate[projDay] <= 0:
            drate = calcChange(deathRate[-deathDays:], rateChange)
        avgDeathRate = abs(avgDeathRate + drate[projDay])
        deathRate.append(avgDeathRate)
        totalDeaths.append(dailyDeaths[-1:][0])
        projDay = 0 if projDay >= deathDays - 2 else projDay + 1
        pdate = datetime.fromtimestamp(timestamp).strftime("%m/%d/%y")
        timestamp += oneDay
        print("Projected Day: {} ({}) - Cases/Today/Infection Rate: {}/{}/{:2.2f}% - Mortality/Today/Rate: {}/{}/{:2.2f}% ".format(day, pdate, format(cases[-1:][0], ',d'), format(now, ',d'),caseRate * 100, format(int(cases[-1:][0] * avgDeathRate), ',d'), format(dailyDeaths[-1:][0], ',d'), avgDeathRate* 100))

    plotUS(day, today, cdate, currentDate, cases, caseRate, growthRates,
           deaths, dailyDeaths, deathRate)

    result = []
    x = 1
    for day in range(600):
        x = 1/sqrt((2*pi))*x*1.2
        result.append(x * day)

