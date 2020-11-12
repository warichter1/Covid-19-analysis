#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Mar 14 18:29:19 2020

@author: wrichter
"""

from copy import deepcopy
import matplotlib.pyplot as plt
from datetime import date
# import benfordslaw as bl

from covidModifiers import Modifiers

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
        # self.population = pop
        self.maxMortality = maxMortality
        self.baseMortality = mortality
        self.survival = survival  # rate of survival for those hospitalized
        self.popData = False
        self.modifier = False
        self.rateChange = {}

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
        self.workingPop -= deaths + births
        self.totalPop -= deaths + births
        caseDeaths = cases / self.workingPop * deaths
        # print(caseDeaths, births, deaths)
        return cases - caseDeaths

    def setPopStats(self, totalPop, births, deaths):
        self.popData = True
        self.totalPop = totalPop
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

    def run(self, days, caseType='limits', distancePop=False):
        self.workingRate = baseRate
        changePoint = 5000000
        case = 1
        mortality = self.baseMortality
        print("Total Days:", days, "Mortality:", mortality, "Type:", caseType)
        self.herdPoints = {'base': self.workingPop * .42, 'baseFound': False, 'baseDay': 0,
              'floor': self.workingPop * .60, 'floorFound': False, 'floorDay': 0,
              'ceiling': self.workingPop * .80, 'ceilingFound': False, 'ceilingDay': 0}
        self.initLists()

        for day in range(days):
            print('Day:', day)
            pinned = ""
            surge = 0
            storeCase = deepcopy(case)
            if caseType == 'exponential': # Exponental Model
                growth = (case * self.workingRate)
                case = case + growth
                if str(day + 1) in self.rateChange.keys():
                    print("Adjust Curve: {}".format(day + 1, case, ))
                    totalRate = self.workingRate + self.rateChange[str(day + 1)]
                    case = storeCase * (1 + totalRate)
                    if case > changePoint:
                        mortality = maxMortality
                    print("Adjust Curve: {} {} {}".format(day + 1, case, totalRate))
            else:  # Limits to Growth Model
                growth = growthLimit(self.workingRate, self.workingPop, case)
                # if growth < 0:
                #     growth = 0
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
            # Add PPE modifier and apply.
            modifier = self.mod.checkSelfProt(self.caseGrowth)
            # add a modifier based in personal distance from others.
            pop = self.mod.checkDistance(self.workingPop)
            self.modPop.append(pop)
            if distancePop is True:
                self.workingPop = pop
            self.workingRate = modifier
            self.modifiedCases.append(modifier)
            self.deaths.append(int(deaths))
            self.dailyDeaths.append(dailyDeaths)
            self.staticDeaths.append(staticDeaths)
            self.caseGrowth.append(int(growth))
            self.growthRate.append(totalRate)
            self.overflow.append(overflow)
            self.recovered.append(recover)
            if summary is True:
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
        plt.plot(self.modPop)
        plt.show()
        return day, totalRate, mortality
        # cases, growthRate, caseGrowth, deaths

    def setModifier(self, protection, rate, curve):
        self.mod = Modifiers(self.totalPop, protection, rate, curve)


summary = False

if __name__ == "__main__":
    totalPop = 331000000
    # riskRise = 0.25
    protection = {}
    # change the infection rate
    protection['modifier'] = {'mask': 1 - 0.65, 'eyeLow': 0.06,
                              'eyeHigh': 0.16}
    protection['active'] = {'mask': False, 'eyeLow': False, 'eyeHigh': False}
    rateModifier = {'base': baseRate, "risk": 7, 'riskRise': .25,
                    'riskLower': .2, 'sciTrustRD': [.53, .31]}
    rateModifier['distance'] = {}
    # Change the contact rate with others in the population
    rateModifier['distance']['modifier'] = {'contact': -0.15, 'lockdown': 0.40,
                                            'oneMeter': 0.13,
                                            'twoMeter': 0.30,}
    rateModifier['distance']['active'] = {'contact': False, 'lockdown': False,
                                          'oneMeter': False,
                                          'twoMeter': False}
    rateModifier['distance']['lockdownDuration'] = {'0': 0, '1': .009, '2': .01,
                                                    '3': .02, '2': .0205,
                                                    '5': .0227, '6': .0261,
                                                    'default': .0275}

    # Change the risk tolerance rate
    rateModifier['education'] = {'highSchool': (1 - .6128), 'whiteHS': .601,
                                 'someCollege': .6128,
                                 'associate': .1018, 'bachelors': .3498,
                                 'masters': .0957, 'professional': .0144,
                                 'phd': .0203}
    rateModifier['eduPartyDR'] = {'highSchool': [.46, .45],
                                  'whiteHS': [.59, .33],
                                  'someCollege': [.47, .39],
                                  'postGrad': [.57, .35]}
    rateModifier['cognitive'] = {'hs': .4324, 'college': .6508}
    curveAdjust = {'daysToPeak': 30, 'declineRate': 1.5, 'focusLoss': 60}
    mortality = 0.0305
    # mortality = 0.045
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
    hp.setPopStats(totalPop, popBirthRate, popDeathRate)
    hp.setModifier(protection, rateModifier, curveAdjust)
    # day, cases, growthRate, caseGrowth, deaths =
    day, totalRate, mortality = hp.run(days, caseType, distancePop=False)
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
