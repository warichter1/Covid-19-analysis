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
from math import sqrt
from numpy import concatenate
from sklearn.metrics import mean_squared_error
from sklearn.model_selection import train_test_split
from pandas import datetime
from pandas import read_csv
from pandas import concat
from sklearn.metrics import mean_squared_error
from sklearn.preprocessing import MinMaxScaler
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error
from sklearn.preprocessing import LabelEncoder

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
        # print(i, dataset[i], dataset[i - interval])
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
    scaler = scaler.fit(train.values)
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
    X = X.reshape(X.shape[0], timesteps, 10)
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
    raw_values = series.values
    values = difference(raw_values, 1)
    ## values = series.values
    # values = values.reshape((len(values), len(values[0])))
    # transform data to be supervised learning
    supervised = timeseries_to_supervised(values, timesteps)
    supervised.fillna(0, inplace=True)
    # supervised = timeseries_to_supervised(diff_values, timesteps)
    # supervised_values = supervised.values[timesteps:,:]
    # split data into train and test-sets
    train, test = supervised[0:-12], supervised[-12:]
    # train, test = supervised[0:-12, :], supervised[-12:, :]
    # train, test = supervised_values[0:-12, :], supervised_values[-12:, :]
    # transform the scale of the data
    scaler, train_scaled, test_scaled = scale(train.values, test.values)
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

# convert series to supervised learning
def series_to_supervised(data, n_in=1, n_out=1, dropnan=True):
    n_vars = 1 if type(data) is list else data.shape[1]
    df = DataFrame(data)
    cols, names = list(), list()
    # input sequence (t-n, ... t-1)
    for i in range(n_in, 0, -1):
        cols.append(df.shift(i))
        names += [('var%d(t-%d)' % (j+1, i)) for j in range(n_vars)]
    # forecast sequence (t, t+1, ... t+n)
    for i in range(0, n_out):
        cols.append(df.shift(-i))
        if i == 0:
            names += [('var%d(t)' % (j+1)) for j in range(n_vars)]
        else:
            names += [('var%d(t+%d)' % (j+1, i)) for j in range(n_vars)]
    # put it all together
    agg = concat(cols, axis=1)
    agg.columns = names
    # drop rows with NaN values
    if dropnan:
        agg.dropna(inplace=True)
    return agg

# convert an array of values into a dataset matrix
def create_dataset(dataset, look_back=1):
    dataX, dataY = [], []
    for i in range(len(dataset)-look_back-1):
        a = dataset[i:(i+look_back), 0]
        dataX.append(a)
        dataY.append(dataset[i + look_back, 0])
    return np.array(dataX), np.array(dataY)

# execute the experiment
def run(exclude=[]):
    # load dataset
    # series = CovidImport(csvTraining, 'stateId', exclude=['state'])
    dataset = read_csv(csvTraining, header=0, parse_dates=[0],
                      index_col=0, squeeze=True, date_parser=parser)
    if len(exclude) > 0:
       for col in exclude:
           del dataset[col]

    values = dataset.values
    # integer encode direction
    encoder = LabelEncoder()
    values[:,4] = encoder.fit_transform(values[:,4])
    # ensure all data is float
    values = values.astype('float32')
    scaler = MinMaxScaler(feature_range=(0, 1))
    scaled = scaler.fit_transform(values)
    reframed = series_to_supervised(scaled, 1, 1)
    # drop columns we don't want to predict
    # reframed.drop(reframed.columns[[9,10,11,12,13,14,15]], axis=1, inplace=True)
    print(reframed.head())
    values = reframed.values
    n_train_hours = 365 * 24
    train = values[:n_train_hours, :]
    test = values[n_train_hours:, :]
    # split into input and outputs
    train_X, train_y = train[:, :-1], train[:, -1]
    test_X, test_y = test[:, :-1], test[:, -1]
    # reshape input to be 3D [samples, timesteps, features]
    train_X = train_X.reshape((train_X.shape[0], 1, train_X.shape[1]))
    test_X = test_X.reshape((test_X.shape[0], 1, test_X.shape[1]))
    print(train_X.shape, train_y.shape, test_X.shape, test_y.shape)

    # design network
    model = Sequential()
    model.add(LSTM(50, input_shape=(train_X.shape[1], train_X.shape[2])))
    model.add(Dense(1))
    model.compile(loss='mae', optimizer='adam')

    # fit network
    history = model.fit(train_X, train_y, epochs=50, batch_size=72,
                        validation_data=(test_X, test_y), verbose=2,
                        shuffle=False)
    # plot history
    plt.plot(history.history['loss'], label='train')
    plt.plot(history.history['val_loss'], label='test')
    plt.legend()
    plt.show()

    repeats = 10
    timesteps = 1
    results = DataFrame()
    # run experiment
    results['results'] = prediction(model, test_X, test_y, repeats, timesteps)

# make a one-step forecast
def forecast_lstm(model, batch_size, X):
    X = X.reshape(1, len(X), 1)
    yhat = model.predict(X, batch_size=batch_size)
    return yhat[0,0]


def prediction(model, test_X, test_y, repeats, timesteps):
    # make a prediction
    yhat = model.predict(test_X)
    test_X = test_X.reshape((test_X.shape[0], test_X.shape[2]))
    # invert scaling for forecast
    inv_yhat = concatenate((yhat, test_X[:, 1:]), axis=1)
    scaler = MinMaxScaler(feature_range=(0, 1)).fit(inv_yhat)
    inv_yhat = scaler.inverse_transform(inv_yhat)
    inv_yhat = inv_yhat[:,0]
    # invert scaling for actual
    test_y = test_y.reshape((len(test_y), 1))
    inv_y = concatenate((test_y, test_X[:, 1:]), axis=1)
    scaler = MinMaxScaler(feature_range=(0, 1)).fit(inv_y)
    inv_y = scaler.inverse_transform(inv_y)
    inv_y = inv_y[:,0]
    # calculate RMSE
    rmse = sqrt(mean_squared_error(inv_y, inv_yhat))
    print('Test RMSE: %.3f' % rmse)

# split into train and test sets
    # train_size = int(len(values) * 0.67)
    # test_size = len(values) - train_size
    # train, test = values[0:train_size,:], values[train_size:len(values),:]
    # print(len(train), len(test))

    # data = df.values
    # split into input and output elements
    # X, y = data[:, :-1], data[:, -1]

    # X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.33, random_state=1)
    # fit the model
    # model = LinearRegression()
    # model.fit(X_train, y_train)
    # evaluate the model
    # yhat = model.predict(X_test)
    # evaluate predictions
    # mae = mean_absolute_error(y_test, yhat)
    # print('MAE: %.3f' % mae)
    # experiment
    # repeats = 10
    # results = DataFrame()
    # run experiment
    # timesteps = 1
    # return series
    # results['results'] = experiment(repeats, series, timesteps)
    # summarize results
    # print(results.describe())
    # save results
    # results.to_csv('experiment_timesteps_1.csv', index=False)


if __name__ == "__main__":
    exclude = ['timestamp', 'state', 'positive', 'negative', 'pending',
                  'onVentilatorCumulative', 'inIcuCumulative', 'recovered']
    repeats = 10
    series = run(exclude)
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




