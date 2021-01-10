#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Mar 14 18:29:19 2020

@author: wrichter
"""

import os
from copy import deepcopy
import matplotlib.pyplot as plt
from datetime import date
# import benfordslaw as bl

from covidModifiers import Modifiers
import globals

globals.initializeStore()

currentDate = date.today()

begin = 3774
days = 450
# days = 200
# baseRate = .142857
baseRate = 1/8
# caseType = 'exponential'
caseType = 'limits'

totalRate = baseRate

# rMax = Maximum growth rate
# K = Carrying Capacity
# N = Population size
def growthLimit(rMax, K, N):
    growth = rMax * ((K - N)/K) * N
    return growth if growth > -1 else 0


class GrowthAndMortality:
    def __init__(self, pop, mortality, maxMortality, survival=.9):
        self.maxMortality = maxMortality
        self.baseMortality = mortality
        self.survival = survival  # rate of survival for those hospitalized
        self.popData = False
        self.modifier = False
        self.rateChange = {}
        self.textLog = ''
        self.textPath = './log'

    def logging(self, text, out=True):
        # self.textLog += (text + '\n')
        globals.textLog += (text + '\n')
        if out is True:
            print(text)

    def initializeQueues(self, availableBeds, inHospital, requireHospital, inIcu,
                         requireIcu):
        self.beds = {}
        self.logging("initializing {} total ICU Beds for {} days.".format(availableBeds * .05, inIcu))
        self.beds['icu'] = {'name': 'icu', 'days': inIcu, 'beds': availableBeds * .05,
                            'require': requireIcu, 'queue': [],
                            'overflow': 0}
        self.logging("initializing {} total hospital Beds for {} days.".format(availableBeds * .95, inHospital))
        self.beds['general'] = {'name': 'general', 'days': inHospital,
                                'beds': availableBeds * .95,
                                'require': requireHospital, 'queue': []}

    def updateBeds(self, cases):
        for bed in self.beds:
            recover = 0
            overflow = 0
            # self.cases = cases
            patients = cases * self.beds[bed]['require']
            if len(self.beds[bed]['queue']) > self.beds[bed]['days']:
                recover = self.beds[bed]['queue'].pop(0)
            inQueue = sum(self.beds[bed]['queue'])
            availableBeds = self.beds[bed]['beds'] - inQueue
            if bed == 'icu':
                patients += recover
            if availableBeds < patients:
                overflow = patients - availableBeds
            self.beds[bed]['queue'].append(patients - overflow)
        recover *= self.survival
        return overflow, recover

    def status(self):
        self.logging("Status Enabled")
        self.logging(str(self.beds['general']))
        self.logging(str(self.beds['icu']))

    def deathsPerDay(self, pop):
        return pop * self.deathRate / 365

    def birthsPerDay(self, pop):
        return pop * self.birthRate / 365

    # add Population deaths and births to the model
    def adjustTotalPop(self, cases):
        births = self.totalPop * self.birthRate
        deaths = self.totalPop * self.deathRate
        self.totalPop -= deaths + births
        caseDeaths = cases / self.workingPop * deaths
        return cases - caseDeaths

    def setPopStats(self, totalPop, births, deaths):
        self.popData = True
        self.totalPop = totalPop
        self.mod = Modifiers(self.totalPop)
        self.workingPop = totalPop
        self.birthRate = births
        self.deathRate = deaths

    def initLists(self):
        self.status()
        self.cases = []
        self.caseGrowth = []
        self.deaths = []
        self.dailyDeaths = []
        self.staticDeaths = []
        self.growthRate = []
        self.overflow = []
        self.recovered = []
        self.modifiedCases = []
        self.modPop = []

    def run(self, days, caseType='limits', distancePop=True):
        self.workingRate = baseRate
        changePoint = 5000000
        case = 1
        overflow = 0
        mortality = self.baseMortality
        self.logging("Total Days: {} Mortality: {} Type:".format(days,
                                                                 mortality,
                                                                 caseType))
        self.herdPoints = {'base': self.workingPop * .42, 'baseFound': False, 'baseDay': 0,
              'floor': self.workingPop * .60, 'floorFound': False, 'floorDay': 0,
              'ceiling': self.workingPop * .80, 'ceilingFound': False, 'ceilingDay': 0}
        self.initLists()

        for day in range(days):
            self.logging('Day: {}'.format(day))
            pinned = ""
            surge = 0
            storeCase = deepcopy(case)
            if caseType == 'exponential': # Exponental Model
                growth = (case * self.workingRate)
                case = case + growth
                if str(day + 1) in self.rateChange.keys():
                    self.logging("Adjust Curve: {}".format(day + 1, case, ))
                    totalRate = self.workingRate + self.rateChange[str(day + 1)]
                    case = storeCase * (1 + totalRate)
                    if case > changePoint:
                        mortality = maxMortality
                    self.logging("Adjust Curve: {} {} {}".format(day + 1, case,
                                                                 totalRate))
            else:  # Limits to Growth Model
                # Add PPE modifier and apply.
                self.workingRate  = self.mod.checkSelfProt(self.caseGrowth)
                # add a modifier based in personal distance from others.
                pop = self.mod.checkDistance(self.workingPop)
                if distancePop is True:
                    self.workingPop = pop
                growth = growthLimit(self.workingRate, self.workingPop, case)
                totalRate = growth / case
                case = self.adjustTotalPop(case + growth)
                overflow, recover = self.updateBeds(growth)
            deaths = case*mortality + overflow
            dailyDeaths = growth*mortality + overflow
            staticDeaths = growth*mortality
            adjustedMortality = 0.0 if int(deaths)  == 0 else deaths / case
            deaths *= .5
            self.cases.append(int(case))
            self.modPop.append(pop)
            self.modifiedCases.append(self.workingRate)
            self.deaths.append(int(deaths))
            self.dailyDeaths.append(abs(int(dailyDeaths)))
            self.staticDeaths.append(abs(int(staticDeaths)))
            self.caseGrowth.append(int(growth))
            self.growthRate.append(totalRate)
            self.overflow.append(overflow)
            self.recovered.append(recover)
            self.workingPop = self.totalPop
            if summary is True:
                self.logging("{}day: {} - Cases/Rate:{}/{:2.2f}%-Mortality/withOverflow:{}/{}-Rate:{:2.4f}%".format(pinned, day + 1, format(int(self.cases[day]), ',d'),
                                                       float(totalRate * 100),
                                                       format(int(self.deaths[day]), ',d'),
                                                       format(int(self.cases[day] * mortality), ',d'),
                                                       adjustedMortality * 100))
                                                   # mortality * 100))
            if self.cases[day] > totalPop:
                self.logging("{}day: {} - Cases Exceed {}, simulation complete!".format(pinned, day +1, format(totalPop, ',d')))
                break
            elif self.herdPoints['baseFound'] == False and self.cases[day] > self.herdPoints['base']:
                self.logging("{}day: {} - Cases Exceed {}, base immunity achieved".format(pinned, day +1, format(int(self.herdPoints['base']), ',d')))
                self.herdPoints['baseFound'] = True
                self.herdPoints['baseDay'] = day
            elif self.herdPoints['floorFound'] == False and self.cases[day] > self.herdPoints['floor']:
                self.logging("{}day: {} - Cases Exceed {}, floor immunity achieved".format(pinned, day +1, format(int(self.herdPoints['floor']), ',d')))
                self.herdPoints['floorFound'] = True
                self.herdPoints['floorDay'] = day
            elif self.herdPoints['ceilingFound'] == False and self.cases[day] > self.herdPoints['ceiling']:
                self.logging("{}day: {} - Cases Exceed {}, ceiling immunity achieved".format(pinned, day +1, format(int(self.herdPoints['ceiling']), ',d')))
                self.herdPoints['ceilingFound'] = True
                self.herdPoints['ceilingDay'] = day
            if len(self.growthRate) > 5 and int(sum(self.growthRate[-5:]) * 3000) == 0 and int(recover + .75) == 0:
                self.logging('Asymtotic curve reached, all US residents infected!\nEnd simulation.')
                break
        if len(self.modPop) > 0:
            plt.plot(self.modPop)
            plt.show()
            plt.plot(self.mod.riskAdjust)
            plt.show()
        return day, totalRate, mortality

    def writeData(self, filename, text):
        print('Writing:', os.path.join(self.textPath, filename))
        with open(os.path.join(self.textPath, filename), "w") as writeToFile:
            writeToFile.writelines(text)

summary = False

if __name__ == "__main__":
    totalPop = 331000000
    mortality = 0.0305
    maxMortality = 0.12
    popDeathRate = 10.542/1000/365
    popBirthRate = 11.08/1000/365
    hospitalizedDays = 16  # Average days in hospital
    icuDays = 11  # Average days in the ICU
    requireHospital = 0.2
    bedOccupancy = 0.6
    requireIcu = .42 * requireHospital  # hospitized that will require ICU
    totalBeds = 924000
    covidBedsTotal = totalBeds * (1 - bedOccupancy)

    hp = GrowthAndMortality(totalPop, mortality, maxMortality)
    hp.initializeQueues(covidBedsTotal, hospitalizedDays, requireHospital,
                        icuDays, requireIcu)
    hp.setPopStats(totalPop, popBirthRate, popDeathRate)
    day, totalRate, mortality = hp.run(days, caseType, distancePop=False)
    hp.writeData('limitsToGrowth.txt', globals.textLog)
    # plt.plot(hp.cases, label='Infected population')
    handles = []
    label, = plt.plot(hp.caseGrowth, label='Daily Infected')
    handles.append(label)
    label, = plt.plot(hp.dailyDeaths, label='Deaths: Overwhelm\n              Healthcare')
    handles.append(label)
    label, = plt.plot(hp.staticDeaths, label='Deaths: Static')
    handles.append(label)
    label = plt.axvline(hp.herdPoints['baseDay'], color='red', label='Herd: Base (' + str(hp.herdPoints['baseDay']) + ')')
    handles.append(label)
    label = plt.axvline(hp.herdPoints['floorDay'], color='purple', label='Herd: Floor (' + str(hp.herdPoints['floorDay']) + ')')
    handles.append(label)
    label = plt.axvline(hp.herdPoints['ceilingDay'], color='salmon', label='Herd: Ceiling (' + str(hp.herdPoints['ceilingDay']) + ')')
    handles.append(label)
    plt.legend(handles=handles, loc='upper left')
    plt.title("Herd Immunity- Patient 0: January 23, 2020")
    plt.xlabel("{} Days\nBenchmark: March 16, 2020 (55 days)\nToday: {}".format(day, currentDate.strftime("%B %d, %Y")))
    plt.ylabel(" Covid-19 US Cases (Mil): {}\nStatic Mortality: {} (Rate: {:2.2f}%)\nOverwhelm Mortality: {} (Rate: {:2.2f}%)".format(format(int(hp.cases[day-1]), ',d'),
                                                           format(int(hp.cases[day-1] * mortality), ',d'), float(mortality * 100),
                                                           format(int(sum(hp.dailyDeaths)), ',d'), float(sum(hp.dailyDeaths) / hp.cases[day-1] * 100)))
