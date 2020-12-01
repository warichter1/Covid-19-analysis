#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Nov 29 21:07:52 2020

@author: wrichter
"""


class CovidData:
    def __init__(self):
        self.baseRate = 1/8
        self.rate = {}
        self.party = {}
        self.population = 331000000
        self.protection = {}
        self.rate = {}
        self.ageDeathRate = {}
        self.raceDeathRate = {}
        self.infectionByAge = {}
        self.curve = {}
        self.human = {}
        self.addHumanity()
        self.addRiskData()
        self.calcModifiers()
        self.addAgeDeathRate()
        self.addRaceDeathRate()
        self.infectionsByAgeRate()

    def addAgeDeathRate(self):
        self.ageDeathRate['0-1'] = 0.00008
        self.ageDeathRate['1-4'] = 0.00005
        self.ageDeathRate['5-14'] = 0.00013
        self.ageDeathRate['14-34'] = 0.00121
        self.ageDeathRate['34-44'] = 0.00676
        self.ageDeathRate['45-54'] = 0.04815
        self.ageDeathRate['55-64'] = 0.11909
        self.ageDeathRate['65-74'] = 0.20769
        self.ageDeathRate['75-84'] = 0.26640
        self.ageDeathRate['85-plus'] = 0.33322

    def addRaceDeathRate(self):
        self.raceDeathRate['white'] = 0.533
        self.raceDeathRate['black'] = 0.23
        self.raceDeathRate['Native American'] = 0.006
        self.raceDeathRate['hispanic'] = 0.051
        self.raceDeathRate['Asian'] = 0.165
        self.raceDeathRate['other'] = 0.014

    def infectionsByAgeRate(self):
        self.infectionByAge['5-9'] = 0.000016
        self.infectionByAge['10-19'] = 0.0000039
        self.infectionByAge['20-49'] = 0.000092
        self.infectionByAge['50-64'] = 0.0014
        self.infectionByAge['65-plus'] = 0.0056

    def addHumanity(self):
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
        self.protection['modifier'] = {'mask': 1 - 0.65, 'eyeLow': 0.06,
                              'eyeHigh': 0.16}
        self.protection['active'] = {'mask': False, 'eyeLow': False,
                                     'eyeHigh': False}
        self.rate = {'base': self.baseRate, "risk": 7, 'riskRise': .25,
                        'riskLower': .2, 'sciTrustRD': [.53, .31]}
        self.rate['distance'] = {}
        # Change the contact rate with others in the population
        self.rate['distance']['modifier'] = {'contact': -0.15, 'lockdown': 0.40,
                                                'oneMeter': 0.13,
                                                'twoMeter': 0.30,}
        self.rate['distance']['active'] = {'contact': False, 'lockdown': False,
                                              'oneMeter': False,
                                              'twoMeter': False}
        self.rate['distance']['lockdownDuration'] = {'0': 0, '1': .009, '2': .01,
                                                        '3': .02, '2': .0205,
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
        total = sum([i[0] for i in self.party[party]['level'].values()])
        return total/self.population, total

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

