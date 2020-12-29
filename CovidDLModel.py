#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Mar 22 16:18:30 2020

@author: wrichter
"""

# data source: https://github.com/CSSEGISandData/COVID-19.git
# use git clone to create a local copy
import sys
import copy
from datetime import date
from datetime import datetime
from math import sqrt
from math import pi
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
import random
import git

from CovidData import CovidData

plotUiResults = True
if len(sys.argv) > 1:
    print('Command Line run')
    plotUiResults = False

g = git.cmd.Git('./COVID-19')
gp = git.cmd.Git('./')
print(g.pull())

dataPath = './COVID-19/csse_covid_19_data/csse_covid_19_time_series/'
plotPath = './plots/'
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
projectionDays = 120
deathDays = 3
begin = 10


def importCsv(infile, incountry, indexin, inexclude):
    """Import the JHU data files based on the index and exclude list."""
    cv = pd.read_csv(infile, index_col=indexin)
    if len(inexclude) > 0:
        for col in inexclude:
            del cv[col]
    return cv.loc[incountry]


def limit(daybegin, dayLimit, rate):
    """Limits to growth calculation."""
    if dayLimit >= daybegin:
        return 1 / (sqrt((2 * pi))) * rate * dayLimit
    return rate


def calcChange(values, projectType=None):
    """Multiple methods of adjusting projected trends."""
    if projectType is not None:
        if projectType == 'avg2':
            return [(values[-1:][0] - values[-2:][0]) for i in range(len(values))]
        elif projectType == 'avgAll':
            return [(sum(values) / len(values)) for i in range(len(values))]
        elif projectType == 'today':
            return [0 for i in range(len(values))]
        elif projectType == 'avgDiff':
            return [(sum(np.diff(values)) / len(np.diff(values))) for i in range(len(values))]
    return np.diff(values) - 1


def plotUS(inday, intoday, cdate, currentDate, cases, caseRate, growthRates,
           deaths, dailyDeaths, deathRate, showTotal=False, yscale='log',
           inauguration=365, plotType='cases'):
    """# Ugly I know, just a simple plot."""
    labels = []
    ecBiden270 = 291
    ecSafeHarbor = 322
    ecStateConfirm = 328
    ecCongressConfirm = 351
    font = FontProperties(family='sans-serif',
                          weight='normal',
                          style='oblique', size=8)

    if showTotal is True:
        label, = plt.plot(cases,  color='red', label='Cases')
        labels.append(label)
        label, = plt.plot(deathRate, color='blue', label='Mortality')
        label, = plt.plot(growthRates, color='magenta', label='Growth')
        labels.append(label)
    if plotType == 'deaths':
        label, = plt.plot(dailyDeaths, color='black', label='Daily Deaths', linewidth=1)
        labels.append(label)
    else:
        label, = plt.plot(dailyCases, color='magenta',
                          label='Current: {:2.2f}%'.format(100*growthRates[intoday]))
        labels.append(label)

        for i in range(scenarioNumber):
            if i == scenarioNumber - 1:
                text = 'Weekly Average: {:2.2f}%'.format(100 * weekRates[i])
            else:
                text = 'Scenario: {:2.2f}%'.format(100 * weekRates[i])

            label, = plt.plot(scenario[i], label=text, linewidth=1)
            labels.append(label)
    label = plt.axvline(intoday, color='green',
                        label='Forecast: {} Days->'.format(projectionDays), linewidth=1)
    labels.append(label)
    iCases = format(int(dailyCases[inauguration]), ',d')
    iDeaths = format(int(dailyDeaths[365]), ',d')
    label = plt.axvline(ecBiden270, color='blue', label='EC Biden Passes 270: 11/7', linewidth=1)
    labels.append(label)
    label = plt.axvline(ecSafeHarbor, color='cyan', label='EC Safe Harbor: 12/8', linewidth=1)
    labels.append(label)
    label = plt.axvline(ecStateConfirm, color='coral', label='EC States Confirm Biden: 12/14', linewidth=1)
    labels.append(label)
    label = plt.axvline(ecCongressConfirm, color='crimson', label='EC Congress Confirms Biden: 1/6', linewidth=1)
    labels.append(label)
    label = plt.axvline(inauguration, color='violet',
                        label='Inauguration Day 2021\nCases: {}, Deaths: {}'.format(iCases, iDeaths), linewidth=1)
    labels.append(label)
    plt.legend(handles=labels, prop=font)
    plt.yscale(yscale)
    plt.title('Covid-19 - "Confirmed" Patient 0: January 21, 2020')
    plt.xlabel("Time ({} Days)\nGrowth per Last Period: {:2.2f}%\nToday: {}".format(inday, caseRate * 100, currentDate.strftime("%B %d, %Y")))
    plt.ylabel(" US Cases (Mil): {}\nMortality: {} (Rate: {:2.2f}%)".format(format(int(cases[day-2]), ',d'),
                                                               format(int(deaths[cdate]), ',d'), float(deathRate[-1:][0] * 100)))
    plt.savefig(plotPath + 'daily_{}.png'.format(plotType),
                bbox_inches="tight",
                pad_inches=0.5 + random.uniform(0.0, 0.25))
    # if plotUiResults is True:
    plt.show(block=False)
    plt.clf()
    plt.cla()
    plt.close()

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
    scenario = []
    scenarioNumber = 7
    scenarioAverage = 0
    inaugurationDay = 365
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
        cases.append(int(us[cdate]))
        now = int(us[cdate] - yesterday)
        nowDeaths = int(deaths[cdate]) - yesterdayDeaths
        dailyCases.append(now)
        yesterday = (us[cdate])
        yesterdayDeaths = int(deaths[cdate])
        dailyDeaths.append(nowDeaths)
        totalDeaths.append(int(deaths[cdate]))
        print("Day: {} ({}) Cases/today/Infection Rate: {}/{}/{:2.2f}% - Mortality/Today/Rate: {}/{}/{:2.2f}% ".format(day, cdate,
                                                                                                                         format(int(us[cdate]), ',d'),
                                                                                                                         format(now, ',d'), caseRate * 100,
                                                                                                                         format(int(deaths[cdate]), ',d'),
                                                                                                                         format(nowDeaths, ',d'),
                                                                                                                         deathRate[-1:][0] * 100))
        lastDay = us[cdate]
        today = day
        day += 1
    avgDeathRate = deathRate[-1:][0]
    # avgDeathRate = sum(deathRate[-deathDays:]) / deathDays
    drate = calcChange(deathRate[-deathDays:], rateChange)
    grate = calcChange(growthRates[-deathDays:], rateChange)
    projDay = 0

    for i in range(scenarioNumber):
        scenario.append(copy.deepcopy(dailyCases))
    weekRates = growthRates[-scenarioNumber:]
    # average of last 7 days
    weekRates[len(weekRates)-1] = (sum(weekRates) / len(weekRates))

    print("Forecast Details: {} days".format(projectionDays))
    for day in range(day, day + projectionDays):
        if caseRate + grate[projDay] <= 0:
            grate = calcChange(growthRates[-deathDays:], rateChange)
            # print('reset')
        # else:
        caseRate = abs(caseRate + grate[projDay])
        # print(grate)
        current = int(cases[-1:][0] * (1 + caseRate))
        cases.append(current)
        now = int(current - yesterday)
        dailyCases.append(now + (now - dailyCases[-3:][0])*.97)
        for i in range(scenarioNumber):
            total = sum(scenario[i])
            currentScenario = total * (1 + weekRates[i])
            nowScenario = currentScenario - total
            scenario[i].append(nowScenario + (now - scenario[i][-3:][0])*.97)
        growthRates.append(caseRate)
        growthRates.append(current / yesterday - 1)
        yesterday = current
        dailyDeaths.append(int(now * avgDeathRate) - dailyDeaths[-4:][0])
        if avgDeathRate + drate[projDay] <= 0:
            drate = calcChange(deathRate[-deathDays:], rateChange)
        avgDeathRate = abs(avgDeathRate + drate[projDay])
        deathRate.append(totalDeaths[-1:][0] / current)
        # deathRate.append(avgDeathRate)
        totalDeaths.append(totalDeaths[-1:][0] + dailyDeaths[-1:][0])
        projDay = 0 if projDay >= deathDays - 2 else projDay + 1
        pdate = datetime.fromtimestamp(timestamp).strftime("%m/%d/%y")
        timestamp += oneDay
        print("Forecast: {} ({}) Cases/Today/Infection Rate: {}/{}/{:2.2f}% - Mortality/Today/Rate: {}/{}/{:2.2f}% ".format(day, pdate,
                                                                                                                                   format(cases[-1:][0], ',d'), format(now, ',d'),
                                                                                                                                   growthRates[-1:][0] * 100, format(int(cases[-1:][0] * avgDeathRate), ',d'), format(dailyDeaths[-1:][0], ',d'), deathRate[-1:][0]* 100))

    plotUS(day, today, cdate, currentDate, cases, caseRate, growthRates,
           deaths, dailyDeaths, deathRate, yscale='linear')
    plotUS(day, today, cdate, currentDate, cases, caseRate, growthRates,
           deaths, dailyDeaths, deathRate, yscale='linear', plotType='deaths')
    gp.add('./plots/*')
    gp.commit('-m', "Upload Daily")
    gp.push()
    cd = CovidData()
    days = {cdate: today, pdate: len(cases)}
    totalCases = {'Current': cases[today - 1],
                  'Forecast': int(cases[len(cases) -1])}
    totalDead = {'Current': totalDeaths[today - 1],
                 'Forecast': int(totalDeaths[len(totalDeaths) - 1])}
    cd.summary(days, totalCases, totalDead)
    gp.add('./data/*')
    gp.commit('-m', "Upload Daily")
    gp.push()

    cd.summary(today, cases[today - 1], totalDeaths[today - 1], dataType="Current")
    cd.summary(day, int(cases[len(cases) -1]), int(totalDeaths[len(totalDeaths) - 1]), dataType="Forecast")
