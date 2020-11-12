#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Sep  6 22:27:27 2020

@author: wrichter
"""
import random
from goals import Svm


class Modifiers:
    """Projection modifiers for population and protection calulations."""

    def __init__(self, population, protection, rate, curve):
        self.population = population
        self.protection = protection
        self.rate = rate
        self.curve = curve
        self.rise = True
        self.riseDays = 0
        self.fallDays = 0
        self.lockdown = {'day': 0, 'active': False}
        self.changeDays = 10
        self.rateMod = 0
        self.distanceMod = 1
        self.trigger = False  # One Time shot, process trigger then disable
        self.peak = 0
        svm = Svm()
        self.riskAdjust = svm.getUncalibrated(expandBy=4)['fop']
        self.lockdownAdjust = svm.getUncalibrated(expandBy=6)['fop']
        self.calcModifiers()

    def checkDirection(self, growth):
        """Check for increasing or decreasing infections."""
        days = len(growth)
        change = None
        if days > 2:
            direction = growth[-2:]
            print('Rise:', self.rise, self.riseDays,"Fall:", self.fallDays, "Direction:", direction)
            if direction[0] > direction[1]:  # cases have hit a daily peak
                self.fallDays += 1
                self.riseDays = 0
                if self.fallDays > self.curve['focusLoss'] and self.checkRisk() is True:
                    self.rise = False
                    self.trigger = True
                    self.fallDays = 0
                    self.peak += 1
                    self.checkPeak()
                    print('Reset - Fall:', self.riseDays, self.fallDays, direction)
            else:  # Change in behavior as peak has occurred
                self.rise = True
                self.fallDays = 0
                self.riseDays += 1
                if self.riseDays > self.curve['daysToPeak'] and self.checkRisk() is True:
                    self.trigger = self.rise = True
                    self.riseDays = 0
                    print('Reset - Rise:', self.riseDays, self.fallDays, direction)

    def checkPeak(self):
        if self.peak > 1:
            toleranceIncrease = random.uniform(0, self.rate['riskRise'])
            self.rate['risk'] += toleranceIncrease
            print('Additional Peak detected, tolerance:', toleranceIncrease)

    def checkRisk(self, max=10):
        num = random.randint(0, max)
        return True if num > self.rate['risk'] else False

    def checkProbableRisk(self, risk, max=10):
        days = self.riseDays if self.riseDays > 0 else self.fallDays
        adjust = self.riskAdjust[days] if len(self.riskAdjust) > days else 1
        num = random.randint(0, max) * adjust
        # print("Debug:", days, "adjust:", adjust, "final:", num, "Risk:", self.rate['risk'], "Rise:", self.rise)
        return True if num > self.rate['risk'] else False

    def checkSelfProt(self, growth, distance=True):  # distabce always True, never disables trigger
        """Caller for PPE caculation of spread rate."""
        self.distance = distance
        rate = self.rate['base']
        rate = rate if self.rateMod == 0 else rate * self.rateMod
        self.checkDirection(growth)
        if self.rise is True:
            self.checkRise()
        elif self.rise is False:
            self.checkFall()
        elif self.checkRisk():  # determine if risk is overcome
            self.checkProtect(max=10)
        # print(self.rate['base'] - rate, rate)
        return rate

    def checkProtect(self, max=20):
        """Param max: DESCRIPTION, defaults to 20."""
        if self.trigger is True:
            if self.checkRisk(max=max) is True:
                self.getProtect()
                print('Rise', self.rise, self.rate['risk'], self.rateMod)

    def checkRise(self):
        """add changes here rising rate here."""
        if self.distance is False:
            self.trigger = False
        self.getProtect()

    def checkFall(self):
        """add changes to falling rate here."""
        if self.distance is False:
            self.trigger = False
        self.getProtect()

    def getProtect(self):
        value = not self.rise
        modifier = self.protection['modifier']
        if self.rise is True:
            modifier = reversed(list(modifier))
        if value in self.protection['active'].values():
            for key in modifier:
                if self.protection['active'][key] is value:
                    self.protection['active'][key] = self.rise
                    if self.rise is True:
                        self.rateMod += self.protection['modifier'][key]
                    else:
                        self.rateMod -= self.protection['modifier'][key]
                    return 0

    def checkDistance(self, currentPop):
        """Self distancing calculations for spread in a population."""
        self.distanceMod = 1.0
        distance = list(self.rate['distance']['modifier'].keys())
        if self.trigger is True:
            print('hit', 'Peak' if self.rise is True else "Trough")
            self.checkDistanceModifier(list(distance))
            self.trigger = False
        else:
            self.checkDistanceModifier(list(distance))
        return int(self.distanceMod * currentPop)

    def checkDistanceModifier(self, distance):
        if self.rise is True:
            distance = list(distance[1:])
        else:
            print('Going Down')
            distance = list(reversed(distance))
        self.distanceModifier(distance)

    def distanceModifier(self, distance):
        """Check Direction and assign the appropriate population modifier."""
        if self.checkProbableRisk(self.riskAdjust) is True:
            for modifier in distance:
                if modifier == 'lockdown':
                    self.inLockdown(modifier)
                    return 0
                print('-->Trigger Mod:', modifier, distance, self.rate['distance']['active'], self.rate['distance']['active'][modifier] , self.rise)
                # Determine whether infections are rising or falling and set.
                if not self.rate['distance']['active'][modifier] is self.rise:
                    direction = 'Down' if self.rise is False else 'Up'
                    self.rate['distance']['active'][modifier] = self.rise
                    self.distanceMod = 1 - self.rate['distance']['modifier'][modifier]
                    print("XXXXXX-Match", modifier, self.rate['distance']['active'][modifier], direction, self.distanceMod)
                    return 0
        elif self.lockdown['active'] is True:
            self.inLockdown('check')

    def inLockdown(self, modifier, max=10):
        """Activate lockdown under special conditions."""
        if modifier == 'lockdown':
            if self.lockdown['active'] is False and self.lockdown['day'] < 1:
                print("Entering Lockdown")
                self.lockdown['active'] = True
                self.rate['distance']['active'][modifier] = True
        elif self.lockdown['active'] is True:
            self.lockdown['day'] += 1
            self.lockdownModifier()
            days = self.lockdown['day']
            adjust = self.lockdownAdjust[days] if len(self.lockdownAdjust) > days else 1
            num = random.randint(0, max) * adjust
            # print("Debug:", days, "adjust:", adjust, "final:", num, "Risk:", self.rate['risk'], "Rise:", self.rise)
            if num > self.rate['risk']:
                print('Exiting Lockdown')
                self.lockdown['active'] = False
        return self.lockdown['active']

    def lockdownModifier(self):
        week = str(int(self.lockdown['day'] % 7))
        if week in self.rate['distance']['lockdownDuration'].keys():
            mod = self.rate['distance']['lockdownDuration'][week]
        else:
            mod = self.rate['distance']['lockdownDuration']['default']
        self.distanceMod = 1 - (mod + self.rate['distance']['modifier']['lockdown'])

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
