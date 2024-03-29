#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Nov 29 21:07:52 2020

@author: wrichter
"""

from prettytable import PrettyTable
from prettytable import MSWORD_FRIENDLY
import os

import globals


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
        self.appended = []
        self.severity = {'asymptomatic': 0.42, 'hospitalized': 0.2}
        self.severity['symtomatic'] = 1 - self.severity['asymptomatic']
        self.severity['symtomatic'] -= self.severity['hospitalized']
        self.severityDelta = {'asymptomatic': 0.33, 'hospitalized': 0.4}
        self.severityDelta['symtomatic'] = 1 - self.severityDelta['asymptomatic']
        self.severityDelta['symtomatic'] -= self.severityDelta['hospitalized']
        self.symtomsDelta = {'mild': 0.67, 'upperResp': 0.36, 'taste': 0.28,
                             'fever': 0.21}
        self.deltaDominant = 501
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

    def append(self, records):
        self.appended.append(records)

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
        # Lifetime Salary adjustment based on education level
        self.rate['educationAttainment'] = {'noHighSchool': 0.84,
                                            'highSchool': 1.00, 
                                            'bachelors': 2.00,
                                            'grad': 2.60}
        # Risk adjusted for education
        self.rate['educationRisk'] = {'noHighSchool': 0.396,
                                        'highSchool': 0.315, 
                                        'bachelors': 0.171,
                                        'grad': 0.117}
        self.rate['eduPartyDR'] = {'noHighSchool': [.46, .54],
                                   'highSchool': [.46, .54],
                                   'whiteHS': [.59, .33],
                                   'bachelors': [.52, .48],
                                   'someCollege': [.47, .39],
                                   'grad': [.62, .38],
                                   'postGrad': [.62, .37]}
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

    def logging(self, text, out=True):
        # self.textLog += (text + '\n')
        globals.textLog += (text + '\n')
        if out is True:
            print(text)

    def summary(self, days, caseTotals, deathTotals):
        """Summarize the data based on the current day, infections, deaths."""
        top = '\n+-------------------------------------------------------------------------------------+'
        totalPad = len(top)
        self.logging(top)
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
            self.logging(text)
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
        if len(self.appended) > 0:
            print("Append additional records")
            for record in self.appended:
                self.rawPrint(record)
        self.writeData('DailySummary.txt', self.summaryText)

    def writeData(self, filename, text):
        print('Writing:', os.path.join(self.textPath, filename))
        with open(os.path.join(self.textPath, filename), "w") as writeToFile:
            writeToFile.writelines(text)

    def rawPrint(self, record):
        print('Print Record')
        table = PrettyTable()
        table.border = True
        table.header = True
        title = record['title']
        template = list(record.field.keys())
        table.field_names = [title] + list(template.keys()) + ['Total']

        data = table.get_string() + '\n'
        self.summaryText += data
        print(table)

    def formatPrint(self, dayTotals, template, title):
        """Create a formatted string from a list, display as a table."""
        keyType = list(dayTotals.keys())
        totals = list(dayTotals.values())
        rates = list(template.values())
        table = PrettyTable()
        # table.set_style(MSWORD_FRIENDLY)
        table.border = True
        table.header = True
        table.field_names = [title] + list(template.keys()) + ['Total']
        for j in range(len(keyType)):
            row = [keyType[j]]
            for i in range(len(rates)):
                row.append(fmtNum(rates[i] * totals[j]))
            row.append(fmtNum(totals[j]))
            # print(row)
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
    print("Delta Dominant (Day: {})".format(cd.deltaDominant))
    print('Severity of Infection (Delta Varient)', cd.severityDelta)
    print('Symptoms (Delta)', cd.symtomsDelta)