#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Jun  4 20:48:14 2020

@author: wrichter
"""


from __future__ import print_function
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split
import scipy
from scipy.ndimage.filters import gaussian_filter1d as gs1d
from datetime import date, datetime
import csv
from datetime import datetime
from datetime import date

import tensorflow as tf
from keras.backend.tensorflow_backend import set_session
init = tf.global_variables_initializer()
sess = tf.Session(config=tf.ConfigProto(log_device_placement=True))
sess.run(init)

import keras
from keras.models import Sequential
from keras.layers import LTSM
from keras.layers import Dense
from keras import regularizers
from keras.optimizers import SGD
from keras import utils
from keras.utils.np_utils import to_categorical
from keras.layers.core import Dense, Dropout, Flatten
from keras.layers import Conv2D

import git

from copy import deepcopy
from collections import OrderedDict
import operator

from CovidDLModelUSStatesConvert import CovidImport
from CovidDLModelUSStatesConvert import csvTraining, csvTesting


if __name__ == "__main__":
    cvTraining = CovidImport(csvTraining, 'stateId', exclude=['state'])
    cvTesting = CovidImport(csvTesting, 'stateId', exclude=['state'])
    cvTraining.df['date'] = pd.to_datetime(cvTraining.df['date'])

    # x: Features use to predict labels
    # y: labels -what we want to predict
    y = cvTraining.df.drop(columns=['confirmed', 'deaths', 'recovered',
                                    'positive', 'negative', 'pending'])

    x = cvTraining.df.drop(columns=['confirmedNew', 'deathsNew', 'totalTests',
                                    'caseRate', 'deathRate',
                                    'hospitalizedCumulative',
                                    'onVentilatorCumulative',
                                    'inIcuCumulative', 'casesPerCapita'])
    # Split the data into training and test sets
    numTraindays = cvTraining.df.timestamp.nunique()
    numTrainHours = numTraindays * 28
    # x[date] = pd.to_datetime(x['date'])
    # y[date] = pd.to_datetime(y['date'])
    x = x.values
    y = y.values
    # x = x.astype('float32')
    # y = y.astype('float32')

    x_train,x_test,y_train,y_test=train_test_split(x,y,test_size=0.2)
    # x_train /= 1024
    # x_test /= 1024
    # y_train /= 1024
    # y_test /= 1024

    batch_size = 32
    num_classes = 5000
    look_back = 1
    # num_classes = len(set(y_train))
    epochs = 5
    # Convert class vectors to binary class matrices.
    y_train = keras.utils.to_categorical(y_train, num_classes)
    y_test = keras.utils.to_categorical(y_test, num_classes)
    # y_train = keras.utils.to_categorical(y_train, 5000)
    # y_test = keras.utils.to_categorical(y_test)
    model = Sequential()
    model.add(LTSM)
    model.add(Dense(8, input_dim=look_back, activation='relu'))
    model.add(Dense(1))
    model.compile(loss='mean_squared_error', optimizer='adam')
    # model.fit(x_train, y_train, epochs=200, batch_size=2, verbose=2)





