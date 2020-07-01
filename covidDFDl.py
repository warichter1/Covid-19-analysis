#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Jun  4 20:48:14 2020

@author: wrichter
"""


from __future__ import print_function
import numpy as np
import pandas as pd
from pandas import DataFrame
from pandas import Series
from pandas import concat
import matplotlib.pyplot as plt
from sklearn.metrics import mean_squared_error
from sklearn.model_selection import train_test_split
from pandas import datetime
from pandas import read_csv
from sklearn.metrics import mean_squared_error
from sklearn.preprocessing import MinMaxScaler
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
from keras.layers import Dense
from keras.layers import LSTM
from keras import regularizers
from keras.optimizers import SGD
from keras import utils
from keras.utils.np_utils import to_categorical
from keras.layers.core import Dense, Dropout, Flatten
from keras.layers import Conv2D
from math import sqrt
import git

from copy import deepcopy
from collections import OrderedDict
import operator

from CovidDLModelUSStatesConvert import CovidImport
from CovidDLModelUSStatesConvert import csvTraining, csvTesting


# LSTM = tf.keras.layers.LSTM(4)

# date-time parsing function for loading the dataset
def parser(x):
	return datetime.strptime(x, '%m/%d/%y')

# frame a sequence as a supervised learning problem
def timeseries_to_supervised(data, lag=1):
    df = DataFrame(data)
    columns = [df.shift(i) for i in range(1, lag+1)]
    columns.append(df)
    df = concat(columns, axis=1)
    return df

# create a differenced series
def difference(dataset, interval=1):
    diff = list()
    for i in range(interval, len(dataset)):
        print(i, dataset[i], dataset[i - interval])
        value = dataset[i] - dataset[i - interval]
        diff.append(value)
    return Series(diff)

# invert differenced value
def inverse_difference(history, yhat, interval=1):
    return yhat + history[-interval]

# scale train and test data to [-1, 1]
def scale(train, test):
    # fit scaler
    scaler = MinMaxScaler(feature_range=(-1, 1))
    scaler = scaler.fit(train)
    # transform train
    train = train.reshape(train.shape[0], train.shape[1])
    train_scaled = scaler.transform(train)
    # transform test
    test = test.reshape(test.shape[0], test.shape[1])
    test_scaled = scaler.transform(test)
    return scaler, train_scaled, test_scaled

# inverse scaling for a forecasted value
def invert_scale(scaler, X, yhat):
    new_row = [x for x in X] + [yhat]
    array = np.array(new_row)
    array = array.reshape(1, len(array))
    inverted = scaler.inverse_transform(array)
    return inverted[0, -1]

# fit an LSTM network to training data
def fit_lstm(train, batch_size, nb_epoch, neurons, timesteps):
    X, y = train[:, 0:-1], train[:, -1]
    X = X.reshape(X.shape[0], timesteps, 11)
    model = Sequential()
    model.add(LSTM(neurons, batch_input_shape=(batch_size, X.shape[1], X.shape[2]), stateful=True))
    model.add(Dense(1))
    model.compile(loss='mean_squared_error', optimizer='adam')
    for i in range(nb_epoch):
        model.fit(X, y, epochs=1, batch_size=batch_size, verbose=0, shuffle=False)
        model.reset_states()
        return model

# make a one-step forecast
def forecast_lstm(model, batch_size, X):
    X = X.reshape(1, len(X), 1)
    yhat = model.predict(X, batch_size=batch_size)
    return yhat[0,0]

# run a repeated experiment
def experiment(repeats, series, timesteps):
    # transform data to be stationary
    # raw_values = series.values
    # diff_values = difference(raw_values, 1)
    values = series.values
    values = values.reshape((len(values), len(values[0])))
    # transform data to be supervised learning
    supervised = timeseries_to_supervised(values, timesteps)
    # supervised = timeseries_to_supervised(diff_values, timesteps)
    supervised_values = supervised.values[timesteps:,:]
    # split data into train and test-sets
    train, test = supervised_values[0:-12, :], supervised_values[-12:, :]
    # transform the scale of the data
    scaler, train_scaled, test_scaled = scale(train, test)
    # run experiment
    error_scores = list()
    for r in range(repeats):
        # fit the base model
        lstm_model = fit_lstm(train_scaled, 1, 500, 1, timesteps)
        # forecast test dataset
        predictions = list()
        for i in range(len(test_scaled)):
            # predict
            X, y = test_scaled[i, 0:-1], test_scaled[i, -1]
            yhat = forecast_lstm(lstm_model, 1, X)
            # invert scaling
            yhat = invert_scale(scaler, X, yhat)
            # invert differencing
            yhat = inverse_difference(values, yhat, len(test_scaled)+1-i)
            # yhat = inverse_difference(raw_values, yhat, len(test_scaled)+1-i)
            # store forecast
            predictions.append(yhat)
        # report performance
        # rmse = sqrt(mean_squared_error(raw_values[-12:], predictions))
        rmse = sqrt(mean_squared_error(values[-12:], predictions))
        print('%d) Test RMSE: %.3f' % (r+1, rmse))
        error_scores.append(rmse)
    return error_scores

# execute the experiment
def run(exclude=[]):
    # load dataset
    # series = CovidImport(csvTraining, 'stateId', exclude=['state'])
    series = read_csv(csvTraining, header=0, parse_dates=[0], index_col=0, squeeze=True, date_parser=parser)
    if len(exclude) > 0:
        for col in exclude:
            del series[col]
    # experiment
    repeats = 10
    results = DataFrame()
    # run experiment
    timesteps = 1
    # return series
    results['results'] = experiment(repeats, series, timesteps)
    # summarize results
    print(results.describe())
    # save results
    results.to_csv('experiment_timesteps_1.csv', index=False)


if __name__ == "__main__":
    series = run(['timestamp', 'state', 'positive', 'negative', 'pending',
         'onVentilatorCumulative', 'inIcuCumulative'])
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
    # y_train = keras.utils.to_categorical(y_train, num_classes)
    # y_test = keras.utils.to_categorical(y_test, num_classes)
    # y_train = keras.utils.to_categorical(y_train, 5000)
    # y_test = keras.utils.to_categorical(y_test)




