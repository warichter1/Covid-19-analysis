#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Mar 14 18:29:19 2020

@author: wrichter
"""

from copy import deepcopy
import matplotlib.pyplot as plt
from datetime import date

currentDate = date.today()

begin = 3774
days = 365
# baseRate = .142857
baseRate = 1/8
# caseType = 'exponential'
caseType = 'limits'

# baseRate = 0.2831  # US rate on 3/15
# baseRate = 0.1143 # World Rate 4/18
# baseRate = .16478  # at Day 54
totalRate = baseRate
rateChange = {}
# rateChange['55'] = .0694  # 03162020
# rateChange['56'] = .2132  # 03172020
# rateChange['57'] = .04465  # 03182020
# rateChange['58'] = .5961  # 03192020 - Testing jump day 1???
# rateChange['59'] = .2393  # 03202020 - Testing jump day 2???
# rateChange['60'] = .1624   # 03212020
# rateChange['61'] = .1445  # 03222020
# rateChange['62'] = .1445   # Reference
# rateChange['63'] = .1445   # Reference
# rateChange['64'] = .1445   # Reference
# rateChange['65'] = .1445   # Reference

# rMax = Maximum growth rate
# K = Carrying Capacity
# N = Population size
def growthLimit(rMax, K, N):
    return rMax * ((K - N)/K) * N


class GrowthAndMortality:
    def __init__(self, pop, mortality, maxMortality, survival=.9):
        self.Population = pop
        self.maxMortality = maxMortality
        self.baseMortality = mortality
        self.survival = survival  # rate of survival for those hospitalized

    def initializeQueues(self, availableBeds, inHospital, requireHospital, inIcu,
                         requireIcu):
        self.beds = {}
        print("initializing {} total ICU Beds for {} days.".format(availableBeds * .05, inIcu))
        self.beds['icu'] = {'name': 'icu', 'days': inIcu, 'beds': availableBeds * .05,
                        'require': requireIcu, 'queue': [],
                        'overflow': 0}
        print("initializing {} total hospital Beds for {} days.".format(availableBeds * .95, inHospital))
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
        print("Status Enabled")
        print(self.beds['general'])
        print(self.beds['icu'])

    def deathsPerDay(self, pop):
        return pop * self.deathRate / 365

    def birthsPerDay(self, pop):
        return pop * self.birthRate / 365

    # add Population deaths and births to the model
    def adjustPop(self, cases):
        births = self.totalPop * self.birthRate
        deaths = self.totalPop * self.deathRate
        self.totalPop -= deaths + births
        caseDeaths = cases / self.totalPop * deaths
        # print(caseDeaths, births, deaths)
        return cases - caseDeaths

    def setPopStats(self, totalPop, births, deaths):
        self.popData = True
        self.totalPop = totalPop
        self.birthRate = births
        self.deathRate = deaths

    def initLists(self):
        self.status()
        self.popData = False
        self.cases = []
        self.caseGrowth = []
        self.deaths = []
        self.dailyDeaths = []
        self.staticDeaths = []
        self.growthRate = []
        self.overflow = []
        self.recovered = []

    def run(self, days, totalPop, caseType='limits'):
        changePoint = 5000000
        case = 1
        mortality = self.baseMortality
        print("Total Days:", days, "Mortality:", mortality, "Type:", caseType)
        self.herdPoints = {'base': totalPop * .42, 'baseFound': False, 'baseDay': 0,
              'floor': totalPop * .60, 'floorFound': False, 'floorDay': 0,
              'ceiling': totalPop * .80, 'ceilingFound': False, 'ceilingDay': 0}
        self.initLists()

        for day in range(days):
            pinned = ""
            surge = 0
            storeCase = deepcopy(case)
            if caseType == 'exponential':
                growth = (case * baseRate)
                case = case + growth
                if str(day + 1) in rateChange.keys():
                    print("Adjust Curve: {}".format(day + 1, case, ))
                    totalRate = baseRate + rateChange[str(day + 1)]
                    case = storeCase * (1 + totalRate)
                    if case > changePoint:
                        mortality = maxMortality
                    print("Adjust Curve: {} {} {}".format(day + 1, case, totalRate))
            else:
                growth = growthLimit(baseRate, totalPop, case)
                totalRate = growth / case
                case = case + growth
            case = self.adjustPop(case)
            overflow, recover = self.updateBeds(growth)
            deaths = case*mortality + overflow
            dailyDeaths = growth*mortality + overflow
            staticDeaths = growth*mortality
            adjustedMortality = 0.0 if int(deaths)  == 0 else deaths / case
            deaths *= .5
            # print(int(case), int(deaths), int(growth*mortality + .5), overflow, adjustedMortality * 100)
            self.cases.append(int(case))
            self.deaths.append(int(deaths))
            self.dailyDeaths.append(dailyDeaths)
            self.staticDeaths.append(staticDeaths)
            self.caseGrowth.append(int(growth))
            self.growthRate.append(totalRate)
            self.overflow.append(overflow)
            self.recovered.append(recover)
            print("{}day: {} - Cases/Rate:{}/{:2.2f}%-Mortality/withOverflow:{}/{}-Rate:{:2.4f}%".format(pinned, day + 1, format(int(self.cases[day]), ',d'),
                                                   float(totalRate * 100),
                                                   format(int(self.deaths[day]), ',d'),
                                                   format(int(self.cases[day] * mortality), ',d'),

                                                   adjustedMortality * 100))
                                                   # mortality * 100))
            if self.cases[day] > totalPop:
                print("{}day: {} - Cases Exceed {}, simulation complete!".format(pinned, day +1, format(totalPop, ',d')))
                break
            elif self.herdPoints['baseFound'] == False and self.cases[day] > self.herdPoints['base']:
                print("{}day: {} - Cases Exceed {}, base immunity achieved".format(pinned, day +1, format(int(self.herdPoints['base']), ',d')))
                self.herdPoints['baseFound'] = True
                self.herdPoints['baseDay'] = day
            elif self.herdPoints['floorFound'] == False and self.cases[day] > self.herdPoints['floor']:
                print("{}day: {} - Cases Exceed {}, floor immunity achieved".format(pinned, day +1, format(int(self.herdPoints['floor']), ',d')))
                self.herdPoints['floorFound'] = True
                self.herdPoints['floorDay'] = day
            elif self.herdPoints['ceilingFound'] == False and self.cases[day] > self.herdPoints['ceiling']:
                print("{}day: {} - Cases Exceed {}, ceiling immunity achieved".format(pinned, day +1, format(int(self.herdPoints['ceiling']), ',d')))
                self.herdPoints['ceilingFound'] = True
                self.herdPoints['ceilingDay'] = day
            if len(self.growthRate) > 5 and int(sum(self.growthRate[-5:]) * 3000) == 0 and int(recover + .75) == 0:
                print('Asymtotic curve reached, all US residents infected!\nEnd simulation.')
                break
        return day, totalRate, mortality
        # cases, growthRate, caseGrowth, deaths

    def setModifier(self, protection, rate):
        self.protection = protection
        self.rateAdjust = rate

if __name__ == "__main__":
    totalPop = 331000000
    protectionMultiplier = {'mask': 1 - 0.65, 'eyeLow': 0.06, 'eyeHigh': 0.16}
    rateModifier = {'directContact': 0.15 - baseRate,
                    'distanceOneMeter': 0.13 - baseRate,
                'distanceTwoMeter': 0.03 - baseRate}
    mortality = 0.045
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

    # icuBeds = covidBedsTotal * .05
    # generalBeds = covidBedsTotal - icuBeds

    hp = GrowthAndMortality(totalPop, mortality, maxMortality)
    hp.initializeQueues(covidBedsTotal, hospitalizedDays, requireHospital,
                        icuDays, requireIcu)
    hp.setModifier(protectionMultiplier, rateModifier)
    hp.setPopStats(totalPop, popBirthRate, popDeathRate)
    # day, cases, growthRate, caseGrowth, deaths =
    day, totalRate, mortality = hp.run(days, totalPop, caseType)
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
