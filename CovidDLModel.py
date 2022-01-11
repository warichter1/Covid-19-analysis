#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Mar 22 16:18:30 2020

@author: wrichter
"""

# data source: https://github.com/CSSEGISandData/COVID-19.git
# use git clone to create a local copy
import sys
import os
import copy
from datetime import date
from datetime import datetime
from math import sqrt
from math import pi
import pandas as pd
import numpy as np
import matplotlib
# import tornado
# import tkinter
# matplotlib.use('TkAgg')
# matplotlib.use('webAgg')
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
from scipy.ndimage.filters import gaussian_filter1d as gs1d
import random
import git
from statistics import mean

from CovidData import CovidData
import globals

globals.initializeStore()

plotUiResults = True
if len(sys.argv) > 1:
    print('Command Line run')
    plotUiResults = False

g = git.cmd.Git('./COVID-19')
print(g.pull())
g = git.cmd.Git('covid-19-data')
print(g.pull())

gp = git.cmd.Git('./')


vaccine = 'covid-19-data/public/data/vaccinations/us_state_vaccinations.csv'
vaccineExclude = ['total_vaccinations',
                  'distributed_per_hundred', 'total_vaccinations_per_hundred',
                  'people_vaccinated', 'people_vaccinated_per_hundred',
                  'people_fully_vaccinated_per_hundred',
                  'daily_vaccinations_raw', 'share_doses_used']
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


def importVaccine(infile, indexin, inexclude=[]):
    """Import the Owid data files based on the index and exclude list."""
    cv = pd.read_csv(infile)
    cv['date'] = pd.to_datetime(cv.date.astype(str),
                        format="%Y/%m/%d").dt.strftime('%m/%d/%y')
    if len(inexclude) > 0:
        for col in inexclude:
            del cv[col]
    return cv.fillna(0).set_index(indexin)

def importVaccineDose(indexin, renameKeys=[], inexcludes=[]):
    cv = pd.read_json('https://data.cdc.gov/resource/saz5-9hgg.json')
    cv += pd.read_json('https://data.cdc.gov/resource/b7pe-5nws.json')
    changeKey = {}
    deleteKey = []
    for cvKey in cv.keys():
        for rename in renameKeys:
            if rename in cvKey:
                date = cvKey.replace(rename, "").replace('_', '-').replace('of-', '')
                date += '-20' if date[:+2] == '12' else '-21'
                changeKey[cvKey] = date
        for exclude in inexcludes:
            if exclude in cvKey:
                # date = cvKey.replace(exclude, "").replace('_', '-')
                # date += '-20' if date[:+2] == '12' else '-21'
                deleteKey.append(cvKey)
    # print(deleteKey)
    cv.rename(changeKey, axis=1, inplace=True)
    for col in deleteKey:
        del cv[col]
    return cv.fillna(0)



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
           inauguration=365, plotType='cases', scenarios=True, lw=0.5, pw=0.75):
    """# Ugly I know, just a simple plot."""
    labels = []
    legend = {}
    font = FontProperties(family='ubuntu',
                          weight='bold',
                          style='oblique', size=6.5)
    iCases = format(int(dailyCases[inauguration]), ',d')
    iDeaths = format(int(dailyDeaths[365]), ',d')
    legend['Forecast: {} Days->'.format(projectionDays)] = (intoday, 'green', 1)
    legend['Biden Passes 270: 11/7'] = (291, 'blue', lw)
    legend['Safe Harbor: 12/8'] = (322, 'cyan', lw)
    legend['States Confirm Biden: 12/14'] = (328, 'coral', lw)
    legend['Congress Confirms Biden: 1/6'] = (351, 'crimson', lw)
    legend['Inauguration Day 2021\nCases: {}, Deaths: {}'.format(iCases, iDeaths)] = (inauguration, 'violet', lw)
    legend['Delta Identified: 4/24'] = (443, 'purple', lw)
    legend['Delta Dominant: 6/5'] = (501, 'red', lw)
    legend['Vaccine Mandate: 9/9'] = (597, 'crimson', lw)
    legend['Omicron Identified: 11/25'] = (674, 'Silver', lw)
    legend['Omicron Dominant 12/20'] = (699, 'Olive', lw)
    if showTotal is True:
        label, = plt.plot(cases,  color='red', label='Cases')
        labels.append(label)
        label, = plt.plot(growthRates, color='magenta', label='Growth')
        labels.append(label)
    if plotType == 'deaths':
        label, = plt.plot(dailyDeaths, color='black', 
                          label='Daily Deaths {:2.2f}%'.format(100*deathRate[intoday]),
                          linewidth=pw)
        labels.append(label)
        average = gs1d(dailyDeaths, sigma=2)
        label, = plt.plot(average, color='Red', label='7 Day Average',
                          linewidth=1)
        labels.append(label)
        peak = max(average[:intoday])
        peaknum = format(int(peak), ',d')
        label = plt.axhline(peak, color='steelblue', label='Peak average {}'.format(peaknum), 
                            linewidth=lw)
        labels.append(label)
    else:
        label, = plt.plot(dailyCases, color='magenta',
                          label='Current: {:2.2f}%'.format(100*growthRates[intoday]), lw=pw)
        labels.append(label)
        for i in range(scenarioNumber):
            text = None
            if i == scenarioNumber - 1:
                text = '7 day Raw Average: {:2.2f}%'.format(100 * weekRates[i])
            elif scenarios is True:
                text = 'Scenario: {:2.2f}%'.format(100 * weekRates[i])
            if text is not None:
                label, = plt.plot(scenario[i], label=text, linewidth=pw, 
                                  ls='dashed')
                labels.append(label)
        average = gs1d(scenario[i], sigma=2)
        label, = plt.plot(average, color='gold',
                          label='7 day Average', linewidth=pw)
        labels.append(label)
        peak = max(average[:intoday])
        peaknum = format(int(peak), ',d')
        label = plt.axhline(peak, color='steelblue', label='Peak average {}'.format(peaknum), 
                            linewidth=lw)
        labels.append(label)        
    for key in legend:
        label = plt.axvline(legend[key][0], color=legend[key][1], label=key, 
                            linewidth=legend[key][2])
        labels.append(label)
    plt.legend(handles=labels, prop=font, loc='upper left')
    plt.yscale(yscale)
    plt.title('Covid-19 - "Confirmed" Patient 0: January 21, 2020')
    plt.xlabel("Time ({} Days)\nGrowth per Last Period: {:2.2f}%\nToday: {}".format(inday, caseRate * 100, currentDate.strftime("%B %d, %Y")))
    plt.ylabel(" US Cases (Mil): {}\nMortality: {} (Rate: {:2.2f}%)".format(format(int(cases[day-2]), ',d'),
                                                               format(int(deaths[cdate]), ',d'), float(deathRate[-1:][0] * 100)))
    plt.savefig(plotPath + 'daily_{}.png'.format(plotType),
                bbox_inches="tight",
                pad_inches=0.5 + random.uniform(0.0, 0.25))
    plt.show(block=False)
    plt.clf()
    plt.cla()
    plt.close()


def vaccinePlot(title, plotType, sources=[], plotLabels=[], yscale='log', 
                dates=[None, None, None], lw=.75, ls=':'):
    """Plot Vaccine deployment."""
    totalVaccine, VacFullDaily, vacDistributedDaily
    labels = []
    font = FontProperties(family='ubuntu',
                      weight='bold',
                      style='normal', size=6.5)
    for num in range(len(sources)):
        width = lw
        style = ls
        if num == 0:
            style = 'solid'
            width = 2
        elif num == 1:
            style = 'dashed'
            width = 1.25
        label, = plt.plot(sources[num], label=plotLabels[num], lw=width, 
                          ls=style)
        labels.append(label)
    plt.xlabel("Time ({} Days)\nVaccine shipments started on day: {}\nBeginning: {}, Current: {}".format(len(sources[0]),dates[0],dates[1],dates[2]))
    plt.ylabel("Covid Vaccine Doses - unfinished")
    plt.legend(handles=labels, prop=font, loc='upper left')
    plt.yscale(yscale)
    plt.title(title)
    plt.savefig(plotPath + 'daily_{}.png'.format(plotType),
                bbox_inches="tight",
                pad_inches=0.5 + random.uniform(0.0, 0.25))
    plt.show(block=False)
    plt.clf()
    plt.cla()
    plt.close()


def fmtInt(num):
    """Format an integer to thousands."""
    return format(int(num), ',d')


def padStrDate(date):
    """If a date/Month is not appended with a leading 0, add."""
    return '0' + date if date[1] == '/' else date


def stripZeros(theList):
    """Remove leading 0 from using numpy array and trim_zeros."""
    npArray = np.trim_zeros(np.array(theList), 'f')
    return npArray, len(theList) - len(npArray)


def returnDaily(theList):
    """Calculate the daily results from the total."""
    npArray = np.trim_zeros(np.array(theList), 'f')
    dailyList = []
    for daily in npArray:
        buffer = 0
        if len(dailyList) > 0:
            if daily > 0:
                buffer = daily - dailyList[-1:][0]
        else:
            buffer = daily
        dailyList.append(abs(buffer))
    return dailyList


if __name__ == "__main__":
    file = "{}/{}".format(dataPath, confirmedCases)
    us = importCsv(file, country, index, excludeFields)
    vacUS = importVaccine(vaccine, 'date', inexclude=vaccineExclude)
    file = "{}/{}".format(dataPath, deathsFile)
    deaths = importCsv(file, country, index, excludeFields)
    cases = []
    growthRates = []
    dailyCases = []
    dailyDeaths = []
    deathRate = []
    totalDeaths = []
    scenario = []
    totalVaccine = []
    totalVacFull = []
    vacDistributed = []
    scenarioNumber = 7
    scenarioAverage = 0
    inaugurationDay = 365
    vaxBegin = None
    vaxLast = None
    vaxDay = None
    day = 1
    lastDay = 1
    yesterday = 0
    yesterdayDeaths = 0
    printText = 'Daily Details for US Cases, Mortaility and Rates\n'
    # rateChange = 'avg2'
    # rateChange = 'avgAll'
    # rateChange = None
    # rateChange = 'avgDiff'
    vaxDates = list(set(list(vacUS.index)))  # Remove dupes
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
        vacToday = 0
        distToday = 0
        fullToday = 0
        padDate = padStrDate(cdate)
        if padDate in vaxDates:
            if vaxBegin is None:
                vaxBegin = cdate
                vaxDay = len(dailyCases)
            vaxLast = cdate
            vacAllUS = vacUS.loc[[padDate]]
            # vacAllUS = vacAllUS.loc[vacAllUS['location']=='United States']
            # distToday1 = vacAllUS.loc[vacAllUS['location']=='United States'].total_distributed
            # fullToday1 = vacAllUS.loc[vacAllUS['location']=='United States'].people_fully_vaccinated
            try:
                vacToday1 = vacAllUS.loc[vacAllUS['location']=='United States'].daily_vaccinations
                distToday1 = vacAllUS.loc[vacAllUS['location']=='United States'].total_distributed
                fullToday1 = vacAllUS.loc[vacAllUS['location']=='United States'].people_fully_vaccinated
                vacToday1 = int(vacToday1[0])
                distToday1 = int(distToday1[0])
                fullToday1 = int(fullToday1[0])
                vacToday = vacUS.loc[[padDate]].daily_vaccinations
                distToday = vacUS.loc[[padDate]].total_distributed
                fullToday = vacUS.loc[[padDate]].people_fully_vaccinated

                # print(padDate, vacToday.values, distToday.values)
                if len(vacToday) == 1:
                    vacToday = int(vacToday[0])
                else:
                    vacToday = int(sum(vacToday))
                if len(fullToday) == 1:
                    fullToday = int(fullToday[0])
                else:
                    fullToday = int(sum(fullToday))
                if len(distToday) == 1:
                    distToday = int(distToday[0])
                else:
                    distToday = int(sum(distToday))
            except:
                vacToday = 0
                vacToday1 = 0
                distToday = 0
                distToday1 = 0
                fullToday= 0
                fullToday1 = 0
                print('Vax Error:', cdate)
        if vaxBegin is not None:
            totalVacFull.append(fullToday1)
            vacDistributed.append(distToday1)
            totalVaccine.append(vacToday1)
        text = "Day: {} ({}) Cases/today/Infection Rate: {}/{}/{:2.2f}% - Mortality/Today/Rate: {}/{}/{:2.2f}% ".format(day, cdate,
                                                                                                                         format(int(us[cdate]), ',d'),
                                                                                                                         format(now, ',d'), caseRate * 100,
                                                                                                                         format(int(deaths[cdate]), ',d'),
                                                                                                                         format(nowDeaths, ',d'),
                                                                                                                         deathRate[-1:][0] * 100)
        print(text)
        printText += (text + '\n')
        lastDay = us[cdate]
        today = day
        day += 1
    avgDeathRate = deathRate[-1:][0]
    drate = calcChange(deathRate[-deathDays:], rateChange)
    grate = calcChange(growthRates[-deathDays:], rateChange)
    projDay = 0
    vacDistributedDaily = returnDaily(vacDistributed)
    VacFullDaily = returnDaily(totalVacFull)
    totalVaccine = totalVaccine[-len(vacDistributedDaily):]
    for i in range(scenarioNumber):
        scenario.append(copy.deepcopy(dailyCases))
    weekRates = growthRates[-scenarioNumber:]
    # average of last 7 days
    weekRates[len(weekRates)-1] = (sum(weekRates) / len(weekRates))

    text = "Forecast Details: {} days".format(projectionDays)
    print(text)
    printText += ('\n' + text + '\n')
    for day in range(day, day + projectionDays):
        if caseRate + grate[projDay] <= 0:
            grate = calcChange(growthRates[-deathDays:], rateChange)
        caseRate = abs(caseRate + grate[projDay])
        last = cases[-1:][0]
        current = int(cases[-1:][0] * (1 + caseRate))
        cases.append(current)
        now = int(current - yesterday)
        dailyCases.append((now + (now - dailyCases[-3:][0])*.97) if (now + (now - dailyCases[-3:][0])*.97) > 0 else 0)
        for i in range(scenarioNumber):
            total = sum(scenario[i])
            currentScenario = total * (1 + weekRates[i])
            nowScenario = currentScenario - total
            scenario[i].append(nowScenario + (now - scenario[i][-3:][0])*.97)
        growthRates.append(caseRate)
        growthRates.append(current / yesterday - 1)
        yesterday = current
        avgDeathRate = abs(avgDeathRate + drate[projDay])
        # current = int(dailyDeaths[-1:][0] * (1 + deathRate[-1:][0]))
        # now = dailyDeaths[-1:][0]
        # buffer = now*avgDeathRate + (now*avgDeathRate - dailyDeaths[-3:][0])*.95
        # buffer = (now*avgDeathRate - dailyDeaths[-3:][0])*.5
        buffer = int(mean(dailyDeaths[-7:])*1.006)
        # print(last, avgDeathRate, last*avgDeathRate, totalDeaths[-1:][0], last*avgDeathRate - totalDeaths[-1:][0])
        # print(last, buffer, mean(dailyDeaths[-3:]))
        # buffer = mean(dailyDeaths[-3:])
        dailyDeaths.append(int(buffer if buffer > 0 else 0))
        if avgDeathRate + drate[projDay] <= 0:
            drate = calcChange(deathRate[-deathDays:], rateChange)
        # avgDeathRate = abs(avgDeathRate + drate[projDay])
        deathRate.append(totalDeaths[-1:][0] / current)
        totalDeaths.append(totalDeaths[-1:][0] + buffer)
        projDay = 0 if projDay >= deathDays - 2 else projDay + 1
        pdate = datetime.fromtimestamp(timestamp).strftime("%m/%d/%y")
        timestamp += oneDay
        text = "Forecast: {} ({}) Cases/Today/Infection Rate: {}/{}/{:2.2f}% - Mortality/Today/Rate: {}/{}/{:2.2f}% ".format(day, pdate,
                                                                                                                                   format(cases[-1:][0], ',d'), format(now, ',d'),
                                                                                                                                   growthRates[-1:][0] * 100, format(int(cases[-1:][0] * avgDeathRate), ',d'), format(dailyDeaths[-1:][0], ',d'), deathRate[-1:][0]* 100)
        print(text)
        printText += (text + '\n')
    plotUS(day, today, cdate, currentDate, cases, caseRate, growthRates,
           deaths, dailyDeaths, deathRate, yscale='linear', scenarios=False)
    plotUS(day, today, cdate, currentDate, cases, caseRate, growthRates,
           deaths, dailyDeaths, deathRate, yscale='linear', plotType='deaths')
    vaccinePlot("Covid-19 Vaccine Deployment", "Vaccine",
                [totalVaccine, VacFullDaily, vacDistributedDaily],
                ["Total Vaccinations ({})".format(fmtInt(sum(totalVaccine))),
                 "Fully Vacinated ({})".format(fmtInt(totalVacFull[-1:][0])),
                 "Vaccine Distributed ({})".format(fmtInt(vacDistributed[-1:][0]))],
                dates=[vaxDay, vaxBegin, vaxLast])
    print(gp.add('./plots/*'))
    cd = CovidData()
    days = {cdate: today, pdate: len(cases)}
    totalCases = {'Current': cases[today - 1],
                  'Forecast': int(cases[len(cases) -1])}
    totalDead = {'Current': totalDeaths[today - 1],
                 'Forecast': int(totalDeaths[len(totalDeaths) - 1])}
    cd.summary(days, totalCases, totalDead)
    cd.writeData('DailyDetailsProjection.txt', printText)
    # cd.summary(today, cases[today - 1], totalDeaths[today - 1], dataType="Current")
    # cd.summary(day, int(cases[len(cases) -1]), int(totalDeaths[len(totalDeaths) - 1]), dataType="Forecast")
    print(gp.add('./data/*'))
    print(gp.commit('-m', "Upload Daily"))
    print(gp.push())

# cvb = importVaccineDose("", renameKeys=['doses_allocated_week_of_', 'doses_distribution_week_of_', 'doses_allocated_for_week_'], inexcludes=['second_dose_shipment_', 'second_doses_shipment_', 'first_doses_'])
