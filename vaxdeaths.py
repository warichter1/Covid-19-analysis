#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Jan 28 21:36:54 2022

@author: wrichter
"""

import csv
import numpy as np
from statistics import mean, median, mode
from scipy import stats

inputfile = "deaths-by-vaccination-status.csv"
outputfile = "full-deaths-by-vaccination-status.csv"


class Expander:
    def __init__(self):
        self.infile = "deaths-by-vaccination-status.csv"
        self.outfile = "full-deaths-by-vaccination-status.csv"
        self.expanded = []
        self.party = {'raw': {}, 'vaxxed': {}, 'unvaxxed': {}}
        self.party['raw']['democratic'] = 0.92
        self.party['raw']['democraticunvax'] = 0.08
        self.party['raw']['republican'] = 0.58
        self.party['raw']['republicanunvax'] = 0.42
        self.party['raw']['independent'] = 0.68
        self.party['raw']['independentunvax'] = 0.32
        self.partyStatus = {}
        total = sum(self.party['raw'].values())
        for key in ['democratic', 'republican', 'independent']:
            self.party['vaxxed'][key] = self.party['raw'][key] / total
            self.party['unvaxxed'][key] = self.party['raw'][key + 'unvax'] / total
        self.processed = False

    def fill(self, line, last):
        """Fill in the blanks for missing days."""
        gap = int(line[0] - last[0])
        padded = []
        if gap < 2:
            print("Nothing to do")
            return [line]
        else:
            unvax = (line[1] - last[1])/gap
            vax = (line[2] - last[2])/gap
            boost = (line[3] - last[3])/gap
        for entry in range(gap):
            padded.append([last[0] + entry + 1, last[1] + unvax*entry, last[2] + vax*entry,
                          last[2] + boost*entry])
        return padded

    def expand(self, endDay=None):
        """Expand the set to complete missing days."""
        expanded = []
        header = False
        last = [0, 0, 0, 0]
        with open(self.infile, newline='') as csvfile:
            reader = csv.reader(csvfile, delimiter=' ', quotechar='|')
            for row in reader:
                row = row[0].split(',')
                if header  is True:
                    row = [float(ele) for ele in row]
                    row[0] = int(row[0])
                    if row[0] - last[0] > 1:
                        row1 = self.fill(row, last)
                        self.expanded += row1
                    else:
                        if row[0] - last[0] == 1:
                            self.expanded += [row]
                    last = row
                else:
                    header = True
                    self.expanded += [row]
        self.inlist = self.expanded.copy()
        self.expanded += self.extend(endDay)
        self.writeCsv()
        return self.expanded

    def extend(self, end):
        """Use Past data to forecast data."""
        data = self.inlist
        begin = 572
        last = len(data) - 1
        extended = []
        day = data[last][0] + 1
        arr = np.array(data[-(last - begin):])
        count = end - day
        for index in range(count):
            # buffer = np.array([day] + list(arr[index:, 1:].mean(axis=0)))
            # buffer = np.array([day] + list(stats.mode(arr[index:, 1:])[0][0]))
            # buffer = np.array([day] + list(np.median(arr[1:, 1:], axis=0)))
            # buffer = np.array([day] + list(np.std(arr[1:, 1:], axis=0)))
            buffer = np.array([day] + list(np.amax(arr[1:, 1:], axis=0)))
            # print('line:', index, list(buffer))
            # arr = np.append(arr, buffer)
            arr = np.vstack([arr, buffer])
            extended.append([day] + list(buffer[1:]))
            # print('Buffer:', day, buffer)
            day += 1
        return extended

    def writeCsv(self):
        print("writing:", self.outfile)
        with open(self.outfile, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile, dialect='unix')
            for row in self.expanded:
                writer.writerow(row)

    def processData(self, data):
        labels = ['unvaxxed', 'vaxxed', 'boosted']
        self.sourceVector = np.array(data)
        transpose = list(zip(*self.expanded[1:]))
        del transpose[0]
        self.statusMatrix = np.array(transpose)
        result = []
        for row in self.statusMatrix:
            result.append(np.multiply(row, self.sourceVector))
        self.status = dict(zip(labels, result))
        self.processed = True
        return self.status

    def getParties(self):
        """Break vax/unvaxxed down by party affiliation."""
        if self.processed is False:
            print('Process Data First')
            return None
        status = {'unvaxxed': self.status['unvaxxed']}
        status['vaxxed'] = np.add(self.status['vaxxed'],
                                  self.status['boosted'])
        self.percent = {'unvaxxed': {}, 'vaxxed': {}}
        for key in status.keys():
            self.partyStatus[key] = {}
            for party in self.party[key].keys():
                self.partyStatus[key][party] = status[key]*self.party[key][party]
                self.percent[key][party] = '%.2f' % (self.party[key][party]*100)
                self.percent[key][party] += '%'
        return self.partyStatus




if __name__ == "__main__":
    vax = Expander()
    result = vax.expand(endDay=700)
    vax.processData(deaths)
    print(result)