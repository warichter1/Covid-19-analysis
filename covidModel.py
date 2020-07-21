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
    def __init__(self, pop, mortality, maxMortality, beds,
                 hospitalPercent, icuPercent):
        self.Population = pop
        self.maxMortality = maxMortality
        self.hospitalPercent = hospitalPercent
        self.icuPercent = icuPercent
        self.icubeds = beds * icuPercent
        self.generalBeds = beds - self.icubeds
        self.baseMortality = mortality
        self.maxMortality = maxMortality

    def initializeQueues(self, inHospital, inIcu):
        self.icuDays = {'days': inIcu, 'queue': []}
        self.generalDays = {'days': inHospital, 'queue': []}

    def updateQueue(self, cases, maxBeds, maxDays, queue):
        fifo = 0
        overflow = 0
        queue = deepcopy(queue)
        inQueue = sum(queue)
        if len(queue) > maxDays:
            fifo = queue.pop(0)
            inQueue = inQueue - fifo
        availableBeds = maxBeds - inQueue
        if availableBeds < cases:
            overflow = cases - availableBeds
        queue.append(cases - overflow)
        return queue, fifo

    def updateBeds(self, todayCases):
        icu = todayCases * self.icuPercent
        hospitized = todayCases * self.hospitalPercent - icu



mortality = 0.045
maxMortality = 0.12
changePoint = 5000000
# mortality = 0.015156
case = 1
xcase = 1
cases = []
caseGrowth = []
deaths = []
totalPop = 331000000
hospitized = 16  # Average days in hospital
icu = 11  # Average days in the ICU
require
requireIcu = .3  # Number hospitized that will require ICU
totalBeds = 924000
icuBeds = totalBeds * .05
generalBeds = totalBeds - icuBeds
herdPoints = {'base': totalPop * .42, 'baseFound': False,
              'floor': totalPop * .60, 'floorFound': False,
              'ceiling': totalPop * .80, 'ceilingFound': False}
for day in range(days):
    pinned = ""
    surge = 0
    storeCase = deepcopy(case)
    if caseType == 'exponential':
        growth = (case * baseRate)
        case = case + growth
        # print(format(int(case), ',d'),
        #    format(int(growthLimit(baseRate, totalPop, case)), ',d'))
        if str(day + 1) in rateChange.keys():
            print("Adjust Curve: {}".format(day + 1, case, ))
            totalRate = baseRate + rateChange[str(day + 1)]
            # case = storeCase + storeCase * totalRate
            case = storeCase * (1 + totalRate)
            if case > changePoint:
                mortality = maxMortality
            print("Adjust Curve: {} {} {}".format(day + 1, case, totalRate))
    else:
        growth = growthLimit(baseRate, totalPop, case)
        totalRate = growth / case
        case = case + growth

    cases.append(int(case))
    deaths.append(int(growth*mortality))
    caseGrowth.append(int(growth))
    print("{}day: {} - Cases/Rate/Mortality/Rate: {}/{:2.2f}%/{}/{:2.2f}%".format(pinned, day + 1, format(int(cases[day]), ',d'),
                                           float(totalRate * 100),
                                           format(int(cases[day] * mortality), ',d'),
                                           mortality * 100))
    if cases[day] > totalPop:
        print("{}day: {} - Cases Exceed {}, simulation complete!".format(pinned, day +1, format(totalPop, ',d')))
        break
    elif herdPoints['baseFound'] == False and cases[day] > herdPoints['base']:
        print("{}day: {} - Cases Exceed {}, base immunity achieved".format(pinned, day +1, format(int(herdPoints['base']), ',d')))
        herdPoints['baseFound'] = True
    elif herdPoints['floorFound'] == False and cases[day] > herdPoints['floor']:
        print("{}day: {} - Cases Exceed {}, floor immunity achieved".format(pinned, day +1, format(int(herdPoints['floor']), ',d')))
        herdPoints['floorFound'] = True
    elif herdPoints['ceilingFound'] == False and cases[day] > herdPoints['ceiling']:
        print("{}day: {} - Cases Exceed {}, ceiling immunity achieved".format(pinned, day +1, format(int(herdPoints['ceiling']), ',d')))
        herdPoints['ceilingFound'] = True
plt.plot(cases, label='growth')
plt.title("Covid-19 - Patient 0: January 23, 2020")
plt.xlabel("{} Days\nGrowth per period: {}\nBenchmark: March 16, 2020 (55 days) cases: {}\nToday: {}".format(day, totalRate, begin, currentDate.strftime("%B %d, %Y")))
plt.ylabel(" US Cases (Mil): {}\nMortality: {} (Rate: {:2.2f}%)".format(format(int(cases[day-1]), ',d'),
                                                           format(int(cases[day-1] * mortality), ',d'), float(mortality * 100)))

