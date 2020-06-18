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
days = 120
# baseRate = .142857
baseRate = 1/8
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
mortality = 0.025
# mortality = 0.015156
case = 1
xcase = 1
cases = []

for day in range(days):
    pinned = ""
    storeCase = deepcopy(case)
    case = case + (case * baseRate)
    if str(day + 1) in rateChange.keys():
        print("Adjust Curve: {}".format(day + 1, case, ))
        totalRate = baseRate + rateChange[str(day + 1)]
        # case = storeCase + storeCase * totalRate
        case = storeCase * (1 + totalRate)
        print("Adjust Curve: {} {} {}".format(day + 1, case, totalRate))
    cases.append(int(case))
    print("{}day: {} - {} -- Mortality: {} -- Infection Rate: {:2.2f}%".format(pinned, day + 1, format(int(cases[day]), ',d'),
                                           format(int(cases[day] * mortality), ',d'), float(totalRate * 100)))
plt.plot(cases, label='growth')
plt.title("Covid-19 - Patient 0: January 23, 2020")
plt.xlabel("Months ({} Days)\nGrowth per period: {}\nBenchmark: March 16, 2020 (55 days) cases: {}\nToday: {}".format(days, totalRate, begin, currentDate.strftime("%B %d, %Y")))
plt.ylabel(" US Cases (Mil): {}\nMortality: {} (Rate: {:2.2f}%)".format(format(int(cases[days-1]), ',d'),
                                                           format(int(cases[days-1] * mortality), ',d'), float(mortality * 100)))

