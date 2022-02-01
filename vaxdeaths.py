#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Jan 28 21:36:54 2022

@author: wrichter
"""

import csv
import numpy as np

inputfile = "deaths-by-vaccination-status.csv"
outputfile = "full-deaths-by-vaccination-status.csv"


class Expander:
    def __init__(self):
        self.infile = "deaths-by-vaccination-status.csv"
        self.outfile = "full-deaths-by-vaccination-status.csv"
        self.expanded = []
        # self.expand(infile, outfile, endDay=None)

    def fillin(self, line, last):
        """Fill in the blanks for missing days."""
        gap = int(line[0] - last[0])
        padded = []
        #print('Gap:', gap)
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

    def expand(self, infile, outfile, endDay=None):
        """Expand the set to complete missing days."""
        # expanded = []
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
                        print(last[0], row[0])
                        row1 = self.fillin(row, last)
                        self.expanded += row1
                    else:
                        print(row)
                        if row[0] - last[0] == 1:
                            self.expanded += [row]
                    last = row
                else:
                    header = True
                    self.expanded += [row]
                    print(row)
        self.expanded += self.extend(endDay)
        self.writeCsv()
        return self.expanded

    def extend(self, end):
        """Use Past data to forecast data."""
        data = self.expanded
        begin = 572
        last = len(data) - 1
        extended = []
        day = data[last][0] + 1
        arr = np.array(data[-(last - begin):])
        count = end - day
        # loop here
        for index in range(count):
            buffer = [day] + list(arr[index:, 1:].mean(axis=0))
            np.append(arr, buffer)
            extended.append(buffer)
            day += 1
        return extended

    def writeCsv(self):
        print("writing:", self.outfile)
        with open(self.outfile, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile, dialect='unix')
            for row in self.expanded:
                writer.writerow(row)

if __name__ == "__main__":
    norm = Expander()
    result = norm.expand(inputfile, outputfile, endDay=741)
    print(result)