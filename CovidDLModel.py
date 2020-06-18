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
projectionDays = 30
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
    else:
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
            [(sum(np.diff(values)) / len(np.diff(values))) for i in range(len(values))]
    return np.diff(values) - 1
    # return np.exp(np.diff(np.log(values))) - 1


if __name__ == "__main__":
    file = "{}/{}".format(dataPath, confirmedCases)
    us = importCsv(file, country, index, excludeFields)
    file = "{}/{}".format(dataPath, deathsFile)
    deaths = importCsv(file, country, index, excludeFields)
    cases = []
    growthRates = []
    dailyDeaths = []
    deathRate = []
    day = 1
    lastDay = 1

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
        dailyDeaths.append(deaths[cdate])
        print("Day: {} - {} Cases/Infection Rate: {}/{:2.2f}% - Mortality/Rate: {}/{:2.2f}% ".format(day, cdate, format(us[cdate], ',d'), caseRate * 100, format(deaths[cdate], ',d'), deathRate[-1:][0] * 100))
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
        cases.append(int(cases[-1:][0] * (1 + caseRate)))
        growthRates.append(caseRate)
        dailyDeaths.append(int(cases[-1:][0] * avgDeathRate))
        if avgDeathRate + drate[projDay] <= 0:
            drate = calcChange(deathRate[-deathDays:], rateChange)
        avgDeathRate = abs(avgDeathRate + drate[projDay])
        deathRate.append(avgDeathRate)
        projDay = 0 if projDay >= deathDays - 2 else projDay + 1
        print("Projected Day: {} - Cases/Infection Rate: {}/{:2.2f}% - Mortality/Rate: {}/{:2.2f}% ".format(day, format(cases[-1:][0], ',d'), caseRate * 100, format(int(cases[-1:][0] * avgDeathRate), ',d'), avgDeathRate* 100))

    labelCase, = plt.plot(cases,  color='red', label='Cases')
    labelDeaths, = plt.plot(dailyDeaths, color='blue', label='Deaths')
    labelGrowth, = plt.plot(growthRates, color='magenta', label='Growth Rate')
    labelDeathRate, = plt.plot(deathRate, color='blue', label='Death Rate')
    labelProject = plt.axvline(today, color='green', label='Projection->')
    plt.legend(handles=[labelCase, labelDeaths, labelGrowth, labelDeathRate, labelProject])
    plt.yscale('log')
    plt.title('Covid-19 - "Confirmed" Patient 0: January 21, 2020')
    plt.xlabel("Months ({} Days)\nGrowth per Last Period: {:2.2f}%\nToday: {}".format(day, caseRate * 100, currentDate.strftime("%B %d, %Y")))
    plt.ylabel(" US Cases (Mil): {}\nMortality: {} (Rate: {:2.2f}%)".format(format(int(cases[day-2]), ',d'),
                                                               format(int(cases[day-2] * deaths[cdate]), ',d'), float(deathRate[-1:][0] * 100)))

    result = []
    x =1
    for day in range(600):
        x = 1/sqrt((2*pi))*x*1.2
        result.append(x * day)

