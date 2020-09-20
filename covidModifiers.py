#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Sep  6 22:27:27 2020

@author: wrichter
"""
import random


class Modifiers:
    def __init__(self, population, protection, rate, curve):
        self.population = population
        self.protection = protection
        self.rate = rate
        self.curve = curve
        self.rise = True
        self.riseDays = 0
        self.fallDays = 0
        self.changeDays = 10
        self.rateMod = 0
        self.distanceMod = 0
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
            # print(direction)
            if direction[0] > direction[1]:  # cases have hit a daily peak
                # print('fall')
                self.fallDays += 1
                self.riseDays = 0
                if self.fallDays > self.curve['focusLoss'] and self.checkRisk() is True:
                    self.trigger = self.rise = True
                    self.fallDays = 0
                    self.peak += 1
                    self.checkPeak()
                    print('Reset - Fall:', self.fallDays, self.peak, direction)
            else:  # Change in behavior as peak has occured
                # print('rise')
                self.fallDays = 0
                self.riseDays += 1
                if self.riseDays > self.curve['daysToPeak'] and self.checkRisk() is True:
                    self.trigger = self.rise = False
                    self.riseDays = 0
                    print('Reset - Rise:', self.riseDays, direction)

    def checkPeak(self):
        if self.peak > 1:
            # print('')
            toleranceIncrease = random.uniform(0, self.rate['riskRise'])
            self.rate['risk'] += toleranceIncrease
            print('Additional Peak detected, tolerance:', toleranceIncrease)

    def checkRisk(self, max=10):
        num = random.randint(0, max)
        # print(num, self.rate['risk'] )
        return True if num > self.rate['risk'] else False

    def checkSelfProt(self, growth, distance=True):
        self.distance = distance
        rate = self.rate['base']
        rate = rate if self.rateMod == 0 else rate * self.rateMod
        self.checkDirection(growth)
        if self.trigger is True:
            self.checkRise()
        elif self.trigger is False:
            self.checkFall()
        elif self.checkRisk():  # determine if risk is overcome
            self.checkProtect(max=20)
        print(self.rate['base'] - rate, rate)
        return rate

    def checkProtect(self, max=20):
        if self.trigger is not None:
            if self.checkRisk(max=max) is True:
                self.getProtect()
                print('Rise', self.rise, self.rate['risk'], self.rateMod)

    def checkRise(self):
        # add changes here rising rate here
        if self.distance is False:
            self.trigger = None
        self.getProtect()

    def checkFall(self):
        # add changes to falling rate here
        if self.distance is False:
            self.trigger = None
        self.getProtect()

    def getProtect(self, value=None):
        value = value if value is not None else self.rise
        modifier = self.protection['modifier']
        if value is True:
            modifier = reversed(list(modifier))
        # print('keys:', self.protection['active'].values(), value)
        if value in self.protection['active'].values():
            for key in modifier:
                if self.protection['active'][key] is value:
                    if value is True:
                        self.rateMod -= self.protection['modifier'][key]
                    else:
                        self.rateMod += self.protection['modifier'][key]
                    print('set:', self.rateMod, self.protection['modifier'][key])
                    self.protection['active'][key] = not value
                    return 0

    def checkDistance(self, currentPop):
        print("Check Distance:", currentPop, self.trigger)
        distance = list(self.rate['distance']['modifier'].keys())
        if self.trigger is True:
            self.distanceModifier( currentPop, list(distance)[1:])
            print('hit peak')
            self.trigger = None
        elif self.trigger is False:
            self.distanceModifier( currentPop, list(reversed(distance)))
            print('Hit a trough')
            self.trigger = None
        else:
            self.checkDistanceModifier(currentPop)

    def checkDistanceModifier(self, pop):
        print('Non-Trigger', self.rise)

    def distanceModifier(self, pop, distance):
        if self.checkRisk() is True:
            print('-> Modify Distance', distance)
            for modifier in distance:
                if not self.rate['distance']['active'][modifier] == self.rise:
                    self.rate['distance']['active'][modifier] = self.rise
                    self.distanceMod = self.rate['distance']['modifier'][modifier]


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
