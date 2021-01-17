#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Sep  6 22:27:27 2020

@author: wrichter
"""
import random
from goals import Svm
from CovidData import CovidData
import globals

class Modifiers:
    """Projection modifiers for population and protection calulations."""

    def __init__(self, population):
        cd = CovidData(population)
        self.population = population
        self.protection = cd.protection
        self.rate = cd.rate
        self.curve = cd.curve
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
        self.party = cd.party
        # self.textLog = logging
        # print(globals.textPrint)

    def logging(self, text, out=True):
        globals.textLog += (text + '\n')
        if out is True:
            print(text)

    def checkDirection(self, growth):
        """Check for increasing or decreasing infections."""
        days = len(growth)
        change = None
        if days > 2:
            direction = growth[-2:]
            # print('Rise:', self.rise, self.riseDays,"Fall:", self.fallDays, "Direction:", direction)
            if direction[0] > direction[1]:  # cases have hit a daily peak
                self.fallDays += 1
                self.riseDays = 0
                if self.fallDays > self.curve['focusLoss'] and self.checkRisk() is True:
                    self.rise = False
                    self.trigger = True
                    self.fallDays = 0
                    self.peak += 1
                    self.checkPeak()
                    self.logging('Reset - Fall: {} {} {}'.format(self.riseDays,
                                                                 self.fallDays,
                                                                 direction))
            else:  # Change in behavior as peak has occurred
                self.rise = True
                self.fallDays = 0
                self.riseDays += 1
                if self.riseDays > self.curve['daysToPeak'] and self.checkRisk() is True:
                    self.trigger = self.rise = True
                    self.riseDays = 0
                    self.logging('Reset - Rise: {} {} {}'.format(self.riseDays,
                                                                 self.fallDays,
                                                                 direction))

    def checkPeak(self):
        """Has the current nunber of daily infections hit a peak."""
        if self.peak > 1:
            toleranceIncrease = random.uniform(0, self.rate['riskRise'])
            self.rate['risk'] += toleranceIncrease
            self.logging('Additional Peak detected, tolerance: {}'.format(toleranceIncrease))

    def checkRisk(self, max=10):
        """Is the risk floor been reached."""
        num = random.randint(0, max)
        return True if num > self.rate['risk'] else False

    def checkProbableRisk(self, risk, max=10):
        """If the risk level is met, do something."""
        days = self.riseDays if self.riseDays > 0 else self.fallDays
        adjust = self.riskAdjust[days] if len(self.riskAdjust) > days else 1
        # num = random.randint(0, max) * adjust
        guess = random.randint(0, max)
        num = guess * adjust
        self.logging("[Debug] {} Rand: {} adjust: {} final: {} Risk: {} Rise: {}".format(days, guess, adjust, num, self.rate['risk'], self.rise), out=False)
        return True if num > self.rate['risk'] else False

    def checkSelfProt(self, growth, distance=True):  # distance always True, never disables trigger
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
        self.logging('Adjusted Rate: {} {}'.format(self.rate['base'] - rate,
                                                   rate), out=True)
        return rate

    def checkProtect(self, max=20):
        """Param max: DESCRIPTION, defaults to 20."""
        if self.trigger is True:
            if self.checkRisk(max=max) is True:
                self.getProtect()
                self.logging('Rise', self.rise, self.rate['risk'],
                             self.rateMod)

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
            self.logging('hit', 'Peak' if self.rise is True else "Trough")
            self.checkDistanceModifier(list(distance))
            self.trigger = False
        else:
            self.checkDistanceModifier(list(distance))
        return int(self.distanceMod * currentPop)

    def checkDistanceModifier(self, distance):
        if self.rise is True:
            distance = list(distance[1:])
        else:
            self.logging('Going Down', False)
            distance = list(reversed(distance))
        self.distanceModifier(distance)

    def distanceModifier(self, distance):
        """Check Direction and assign the appropriate population modifier."""
        if self.checkProbableRisk(self.riskAdjust) is True:
            for modifier in distance:
                if modifier == 'lockdown' and self.inLockdown(modifier) is True:
                    return 0
                self.logging('-->Trigger Mod: {} {} {} {} {}'.format(modifier,
                                                                     distance,
                                                                     self.rate['distance']['active'], self.rate['distance']['active'][modifier] , self.rise))
                # Determine whether infections are rising or falling and set.
                if self.rise is True and self.rate['distance']['active'][modifier] is False:
                    self.rate['distance']['active'][modifier] = True
                    self.changeDistance(modifier)
                    return 0
                elif self.rise is False and self.rate['distance']['active'][modifier] is True:
                    self.rate['distance']['active'][modifier] = False
                    self.changeDistance(modifier)
                    return 0
        elif self.lockdown['active'] is True:
            self.inLockdown('check')

    def changeDistance(self, modifier):
        direction = 'Down' if self.rise is False else 'Up'
        self.distanceMod = 1 - self.rate['distance']['modifier'][modifier]
        self.logging("XXXXXX-Match {} {} {} {}".format(modifier, self.rate['distance']['active'][modifier], direction, self.distanceMod), out=False)

    def inLockdown(self, modifier, max=10):
        """Activate lockdown under special conditions."""
        if modifier == 'lockdown':
            if self.lockdown['active'] is False and self.lockdown['day'] < 1:
                self.logging("--> Entering Lockdown")
                self.lockdown['active'] = True
                self.rate['distance']['active'][modifier] = True
                self.distanceMod = 1 - self.rate['distance']['modifier'][modifier]
        elif self.lockdown['active'] is True:
            self.lockdown['day'] += 1
            self.lockdownModifier()
            days = self.lockdown['day']
            adjust = self.lockdownAdjust[days] if len(self.lockdownAdjust) > days else 1
            num = random.randint(0, max) * adjust
            self.logging("Debug: {} adjust: {} final: {} Risk: {} Rise: {}".format(days, adjust, num, self.rate['risk'], self.rise))
            if num > self.rate['risk']:
                self.logging('Exiting Lockdown <--')
                self.lockdown['active'] = False
        return self.lockdown['active']

    def lockdownModifier(self):
        week = str(int(self.lockdown['day'] % 7))
        if week in self.rate['distance']['lockdownDuration'].keys():
            mod = self.rate['distance']['lockdownDuration'][week]
        else:
            mod = self.rate['distance']['lockdownDuration']['default']
        self.distanceMod = 1 - (mod + self.rate['distance']['modifier']['lockdown'])
