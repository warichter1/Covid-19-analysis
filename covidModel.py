#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Mar 14 18:29:19 2020

@author: wrichter
"""

from copy import deepcopy
import matplotlib.pyplot as plt
from datetime import date
import random
import benfordslaw as bl

currentDate = date.today()

begin = 3774
days = 100
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
        # self.population = pop
        self.maxMortality = maxMortality
        self.baseMortality = mortality
        self.survival = survival  # rate of survival for those hospitalized
        self.popData = False
        self.modifier = False

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

    def run(self, days, caseType='limits'):
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
            pinned = ""
            surge = 0
            storeCase = deepcopy(case)
            if caseType == 'exponential':
                growth = (case * self.workingRate)
                case = case + growth
                if str(day + 1) in rateChange.keys():
                    print("Adjust Curve: {}".format(day + 1, case, ))
                    totalRate = self.workingRate + rateChange[str(day + 1)]
                    case = storeCase * (1 + totalRate)
                    if case > changePoint:
                        mortality = maxMortality
                    print("Adjust Curve: {} {} {}".format(day + 1, case, totalRate))
            else:
                growth = growthLimit(self.workingRate, self.workingPop, case)
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
            self.modifiedCases.append(self.mod.check(self.cases))
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

    def setModifier(self, protection, rate, curve):
        self.mod = Modifiers(self.totalPop, protection, rate, curve)

class Modifiers:
    def __init__(self, population, protection, rate, curve):
        self.population = population
        self.protection = protection
        self.rate = rate
        self.curve = curve
        self.rise = True
        # self.fall = False
        self.riseDays = 0
        self.fallDays = 0
        self.changeDays = 10
        self.rateMod = 0
        self.trigger = None
        self.peak = 0
        self.calcModifiers()

    def checkDirection(self, growth):
        days = len(growth)
        change = None
        # if self.rise is True:
        #    self.riseDays += 1
        if days > 2:
            direction = growth[-2:]
            if direction[0] > direction[1]:  # cases have hit a daily peak
                self.fallDays += 1
                self.riseDays = 0
                if self.fallDays > self.curve['focusLoss'] and self.checkRisk() is True:
                    self.trigger = self.rise = True
                    self.fallDays = 0
                    self.peak += 1
                    self.checkPeak()
                    print('Reset - Fall:', self.fallDays, self.peak)
            else:  # Change in behavior as peak has occured
                self.fallDays = 0
                self.riseDays += 1
                if self.riseDays > self.curve['daysToPeak'] and self.checkRisk() is True:
                    self.trigger = self.rise = False
                    self.riseDays = 0
                    print('Reset - Rise:', self.riseDays)

    def checkPeak(self):
        if self.peak > 1:
            print('')
            toleranceIncrease = random.uniform(0, self.rate['riskRise'])
            self.rate['risk'] += toleranceIncrease
            print('Additional Peak detected, tolerance:', toleranceIncrease)

    def checkRisk(self, max=10):
        return True if random.randint(0, max) > self.rate['risk'] else False

    def check(self, growth):
        # check = 0.0
        self.checkDirection(growth)
        if self.trigger is True:
            self.checkRise()
        elif self.trigger is False:
            self.checkFall()
        elif self.checkRisk():  # determine if risk is overcome
            self.checkProtect()
        return self.rateMod

    def checkProtect(self, max=20):
        if self.trigger is not None:
            if self.checkRisk(max=max) is True:
                self.getProtect()
                print('Rise', self.rise, self.rate['risk'], self.rateMod)

    def checkRise(self):
        # add changes here rising rate here
        self.trigger = None
        self.getProtect()

    def checkFall(self):
        # add changes to falling rate here
        self.trigger = None
        self.getProtect()

    def getProtect(self, value=None):
        value = value if value is not None else self.rise
        modifier = self.protection['modifier']
        if value is True:
            modifier = reversed(list(modifier))
        print('keys:', self.protection['active'].values(), value)
        if value in self.protection['active'].values():
            for key in modifier:
                if self.protection['active'][key] is value:
                    if value is True:
                        self.rateMod -= self.protection['modifier'][key]
                    else:
                        self.rateMod += self.protection['modifier'][key]
                    print('set:', self.rateMod, self.protection['modifier'][key])
                    self.protection['active'][key] = not value

    def calcModifiers(self):
        pop = self.population
        edu = self.rate['education']
        self.party = {}
        self.party['d'] = {'sciTrust': [pop * self.rate['sciTrustRD'][0],
                                        self.rate['sciTrustRD'][0]]}
        self.party['r'] = {'sciTrust': [pop * self.rate['sciTrustRD'][1],
                                        self.rate['sciTrustRD'][1]]}
        self.party['d']['level'] = {}
        self.party['r']['level'] = {}
        hs = edu['highSchool'] * pop
        hsw = hs * edu['whiteHS']
        hsm = hs - hsw
        # hwAvg = hsw / hs
        # hmAvg = hsm / hs
        p = self.rate['eduPartyDR']['highSchool'][0]
        self.party['d']['level']['hswhite'] = [hsw * p, p]
        self.party['d']['level']['hsminority'] = [hsm * p, p]
        p = self.rate['eduPartyDR']['highSchool'][1]
        self.party['r']['level']['hswhite'] = [hsw * p, p]
        self.party['r']['level']['hsminority'] = [hsm * p, p]
        p = self.rate['eduPartyDR']['highSchool'][0]
        c = edu['someCollege'] * pop
        self.party['d']['level']['college'] = [c * p, p]
        p = self.rate['eduPartyDR']['someCollege'][1]
        self.party['r']['level']['college'] = [c * p, p]
        p = self.rate['eduPartyDR']['postGrad'][0]
        c = (edu['masters'] + edu['phd'] + edu['professional'])* pop
        self.party['d']['level']['postGrad'] = [c * p, p]
        p = self.rate['eduPartyDR']['postGrad'][1]
        self.party['r']['level']['postGrad'] = [c * p, p]
        self.party['d']['percentage'], total = self.countParty('d')
        self.party['r']['percentage'], total = self.countParty('r')

    def countParty(self, party):
        total = sum([i[0] for i in self.party[party]['level'].values()])
        return total/self.population, total

if __name__ == "__main__":
    totalPop = 331000000
    riskRise = 0.25
    protection = {}
    protection['modifier'] = {'mask': 1 - 0.65, 'eyeLow': 0.06,
                              'eyeHigh': 0.16}
    protection['active'] = {'mask': False, 'eyeLow': False, 'eyeHigh': False}
    rateModifier = {'base': baseRate, "risk": 2, 'riskRise': .25,
                    'sciTrustRD': [.53, .31]}
    rateModifier['distance'] = {}
    rateModifier['distance']['modifier'] = {'contact': -0.15,
                                            'oneMeter': 0.13 - baseRate,
                                            'twoMeter': 0.03 - baseRate}
    rateModifier['distance']['active'] = {'contact': False,
                                          'oneMeter': False, 'owoMeter': False}
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
    hp.setPopStats(totalPop, popBirthRate, popDeathRate)
    hp.setModifier(protection, rateModifier, curveAdjust)
    # day, cases, growthRate, caseGrowth, deaths =
    day, totalRate, mortality = hp.run(days, caseType)
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
