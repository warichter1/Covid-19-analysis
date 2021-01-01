#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Nov 29 21:07:52 2020

@author: wrichter
"""

from prettytable import PrettyTable
from prettytable import MSWORD_FRIENDLY
import os


class CovidData:
    """Data for various details of Covid."""

    def __init__(self, population=331000000, summary=False, textPath='./data'):
        """Covid data class initializers."""
        self.baseRate = 1/8
        self.summaryText = ""
        self.textPath = textPath
        self.rate = {}
        self.party = {}
        self.population = population
        self.protection = {}
        self.rate = {}
        self.ageDeathRate = {}
        self.raceDeathRate = {}
        self.infectionByAge = {}
        self.infectionByLength = {}
        self.curve = {}
        self.human = {}
        self.severity = {'asymptomatic': 0.42, 'hospitalized': 0.2}
        self.severity['symtomatic'] = 1 - self.severity['asymptomatic']
        self.severity['symtomatic'] -= self.severity['hospitalized']
        self.addHumanity()
        self.addRiskData()
        self.calcModifiers()
        self.addAgeDeathRate()
        self.addRaceDeathRate()
        self.infectionsByAgeRate()
        self.deathsSex()
        self.infectionLength()
        if summary is True:
            self.summary()

    def infectionLength(self):
        """Length of illness, inclusing Long Haulers"""
        self.infectionByLength['0-1'] = 0.42
        self.infectionByLength['2-3'] = 0.35
        self.infectionByLength['4'] = 0.133
        self.infectionByLength['5-8'] = 0.045
        self.infectionByLength['9-12'] = 0.023
        self.infectionByLength['13-plus'] = 1- sum(self.infectionByLength.values())

    def addAgeDeathRate(self):
        """Death rate by age range."""
        self.ageDeathRate['0-17'] = 0.0006
        self.ageDeathRate['18-44'] = 0.039
        self.ageDeathRate['45-64'] = 0.224
        self.ageDeathRate['65-74'] = 0.249
        self.ageDeathRate['75-plus'] = 0.487

    def addRaceDeathRate(self):
        """Death rate by race."""
        self.raceDeathRate['white'] = 0.533
        self.raceDeathRate['black'] = 0.23
        self.raceDeathRate['hispanic'] = 0.051
        self.raceDeathRate['Asian'] = 0.165
        self.raceDeathRate['other'] = 0.014
        self.raceDeathRate['Native American'] = 0.006

    def infectionsByAgeRate(self):
        """Infection rate by age range."""
        self.infectionByAge['5-9'] = 0.0016
        self.infectionByAge['10-19'] = 0.00039
        self.infectionByAge['20-49'] = 0.0092
        self.infectionByAge['50-64'] = 0.14
        self.infectionByAge['65-plus'] = 0.56

    def deathsSex(self):
        self.deathsBySex = {'male': 0.618, 'female': 0.382}

    def addHumanity(self):
        """Variables that affect ability to control Covid."""
        self.human['mortality'] = 0.0305
        self.human['maxMortality'] = 0.12
        self.human['popDeathRate'] = 10.542/1000/365
        self.human['popBirthRate'] = 11.08/1000/365
        self.human['hospitalizedDays'] = 16  # Average days in hospital
        self.human['icuDays'] = 11  # Average days in the ICU
        requireHospital = 0.2
        self.human['requireHospital'] = requireHospital
        bedOccupancy = 0.6
        self.human['bedOccupancy'] = bedOccupancy
        # hospitized that will require ICU
        self.human['requireIcu'] = .42 * requireHospital
        totalBeds = 924000
        self.human['totalBeds'] = totalBeds
        self.human['covidBedsTotal'] = totalBeds * (1 - bedOccupancy)

    def addRiskData(self):
        """Risks."""
        self.protection['modifier'] = {'mask': 1 - 0.65, 'eyeLow': 0.06,
                                       'eyeHigh': 0.16}
        self.protection['active'] = {'mask': False, 'eyeLow': False,
                                     'eyeHigh': False}
        self.rate = {'base': self.baseRate, "risk": 7, 'riskRise': .25,
                     'riskLower': .2, 'sciTrustRD': [.53, .31]}
        self.rate['distance'] = {}
        # Change the contact rate with others in the population
        self.rate['distance']['modifier'] = {'contact': -0.15,
                                             'lockdown': 0.40,
                                             'oneMeter': 0.13,
                                             'twoMeter': 0.30}
        self.rate['distance']['active'] = {'contact': False, 'lockdown': False,
                                           'oneMeter': False,
                                           'twoMeter': False}
        self.rate['distance']['lockdownDuration'] = {'0': 0, '1': .009,
                                                     '2': .01,
                                                     '3': .02, '4': .0205,
                                                     '5': .0227, '6': .0261,
                                                     'default': .0275}

        # Change the risk tolerance rate
        self.rate['education'] = {'highSchool': (1 - .6128), 'whiteHS': .601,
                                  'someCollege': .6128,
                                  'associate': .1018, 'bachelors': .3498,
                                  'masters': .0957, 'professional': .0144,
                                  'phd': .0203}
        self.rate['eduPartyDR'] = {'highSchool': [.46, .45],
                                   'whiteHS': [.59, .33],
                                   'someCollege': [.47, .39],
                                   'postGrad': [.57, .35]}
        self.rate['cognitive'] = {'hs': .4324, 'college': .6508}
        self.curve['daysToPeak'] = 30
        self.curve['declineRate'] = 1.5
        self.curve['focusLoss'] = 60

    def calcModifiers(self):
        """Parse data to create scientific trust and education with party."""
        pop = self.population
        edu = self.rate['education']
        self.party['d'] = {'sciTrust': [pop * self.rate['sciTrustRD'][0],
                                        self.rate['sciTrustRD'][0]]}
        self.party['r'] = {'sciTrust': [pop * self.rate['sciTrustRD'][1],
                                        self.rate['sciTrustRD'][1]]}
        self.party['d']['level'] = {}
        self.party['r']['level'] = {}
        hs = edu['highSchool'] * pop
        hsw = hs * edu['whiteHS']
        hsm = hs - hsw
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
        c = (edu['masters'] + edu['phd'] + edu['professional']) * pop
        self.party['d']['level']['postGrad'] = [c * p, p]
        p = self.rate['eduPartyDR']['postGrad'][1]
        self.party['r']['level']['postGrad'] = [c * p, p]
        self.party['d']['percentage'], total = self.countParty('d')
        self.party['r']['percentage'], total = self.countParty('r')

    def countParty(self, party):
        """Calculate policial party."""
        total = sum([i[0] for i in self.party[party]['level'].values()])
        return total/self.population, total

    def summary(self, days, caseTotals, deathTotals):
        """Summarize the data based on the current day, infections, deaths."""
        top = '\n+--------------------------------------------------------------------------+'
        totalPad = len(top)
        print(top)
        self.summaryText += (top + '\n')
        lenStr = len(top) - 2
        dates = list(days.keys())
        number = list(days.values())
        for i in range(len(dates)):
            text = "| {} summary for day {} ({}):".format(list(caseTotals.keys())[i],
                                                          fmtNum(number[i]),
                                                          dates[i])
            text += " "*(lenStr - len(text))
            text += '|'
            print(text)
            self.summaryText += (text + '\n')
            infected = list(caseTotals.values())
            dead = list(deathTotals.values())
            text = '| Total infections: {}, Deaths: {}'.format(fmtNum(infected[i]),
                                                            fmtNum(dead[i]))
            text += " "*(lenStr - len(text))
            text += '|'
            print(text)
            self.summaryText += (text + '\n')

        self.formatPrint(caseTotals, self.infectionByAge, 'Infections by Age')
        self.formatPrint(caseTotals, self.severity, 'Infections by severity')
        self.formatPrint(caseTotals, self.infectionByLength,
                         'Infection Length (Wk)')
        self.formatPrint(deathTotals, self.ageDeathRate,
                         'Death Rate by Age Range')
        self.formatPrint(deathTotals, self.raceDeathRate, 'Death Rate by Race')
        self.formatPrint(deathTotals, self.deathsBySex, 'Death Rate by Sex')
        self.writeData('DailySummary.txt', self.summaryText)

    def writeData(self, filename, text):
        print('Writing:', os.path.join(self.textPath, filename))
        with open(os.path.join(self.textPath, filename), "w") as writeToFile:
            writeToFile.writelines(text)

    def formatPrint(self, dayTotals, template, title):
        """Create a formatted string from a list, display as a table."""
        keyType = list(dayTotals.keys())
        totals = list(dayTotals.values())
        rates = list(template.values())
        table = PrettyTable()
        # table.set_style(MSWORD_FRIENDLY)
        table.border = True
        table.header = True
        table.field_names = [title] + list(template.keys())
        for j in range(len(keyType)):
            row = [keyType[j]]
            for i in range(len(rates)):
                row.append(fmtNum(rates[i] * totals[j]))
            table.add_row(row)
        data = table.get_string() + '\n'
        self.summaryText += data
        print(table)


def fmtNum(num):
    """Formatter to convert int to number with commas by thousand."""
    return format(int(num), ',d')


if __name__ == "__main__":
    cd = CovidData()
    print('Data:')
    print('Rates:', cd.rate)
    print('Curve:', cd.curve)
    print('Human:', cd.human)
    print('Party', cd.party)
    print('Death By Age', cd.ageDeathRate)
    print('Death by Race', cd.raceDeathRate)
    print('Infections by Age', cd.infectionByAge)
    print('Severity of Infection', cd.severity)
