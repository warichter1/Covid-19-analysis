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

def fillin(line, last):
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
    # padded.append(line)
    return padded

def expand(infile, outfile, endDay=None):
    """Expand the set to complete missing days."""
    expanded = []
    header = False
    last = [0, 0, 0, 0]

    with open(infile, newline='') as csvfile:
        reader = csv.reader(csvfile, delimiter=' ', quotechar='|')
        for row in reader:
            row = row[0].split(',')
            if header  is True:
                row = [float(ele) for ele in row]
                row[0] = int(row[0])
                if row[0] - last[0] > 1:
                    print(last[0], row[0])
                    row1 = fillin(row, last)
                    expanded += row1
                else:
                    print(row)
                    if row[0] - last[0] == 1:
                        expanded += [row]
                last = row
            else:
                header = True
                expanded += [row]
                print(row)
    writeCsv(outfile, expanded)
    return expanded

def extend(end, data):
    """Use Past data to forecast data."""
    begin = 572
    last = len(data) - 1
    extended = []
    day = data[last][0] + 1
    arr = np.array(data[-(last - begin):])
    npIndex = 0
    # loop here
    buffer = [day] + list(arr[npIndex].mean(axis=0)[1:])
    np.append(arr, buffer)
    npIndex += 1



def writeCsv(outfile, file):
    print("writing:", outfile)
    with open(outfile, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile, dialect='unix')
        for row in file:
            writer.writerow(row)

result = expand(inputfile, outputfile, endDay=859)
print(result)