#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Oct  9 21:23:44 2020

@author: wrichter
"""

# Source: https://machinelearningmastery.com/how-to-score-probability-predictions-in-python/
# other: https://github.com/DrTol/GoalSeek_Python
#        https://machinelearningmastery.com/lasso-regression-with-python/

from sklearn.metrics import log_loss
from sklearn.metrics import brier_score_loss
from sklearn.metrics import roc_curve
from sklearn.datasets import make_classification
from sklearn.linear_model import LogisticRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import train_test_split
from matplotlib import pyplot
# from numpy import array

def logLoss(goal=30, step=0.01, value=False, plot=False):
    # plot impact of logloss for single forecasts
    # predictions as 0 to 1 in 0.01 increments
    yhat = [x*step for x in range(0, goal)]
    # evaluate predictions for a 0 true value
    losses = [log_loss([value], [x], labels=[0,1]) for x in yhat]
    # plot input to loss
    if plot is True:
        pyplot.plot(yhat, losses, label='true=0')
        pyplot.legend()
        pyplot.show()
    return {'yhat': yhat, 'losses': losses}

def brierScore(goal=30, step=0.01, value=False, plot=False):
    # plot impact of brier for single forecasts
    # predictions as 0 to 1 in 0.01 increments
    yhat = [x*step for x in range(0, 101)]
    # evaluate predictions for a 1 true value
    losses = [brier_score_loss([value], [x], pos_label=[1]) for x in yhat]
    # plot input to loss
    if plot is True:
        pyplot.plot(yhat, losses, label='true=0')
        pyplot.legend()
        pyplot.show()
    return {'yhat': yhat, 'losses': losses}

# plot impact of brier score with balanced datasets
def balanceBrierScore(goal=30, plot=False):
    # define a balanced dataset
    testy = [0 for x in range(goal)] + [1 for x in range(goal)]
    # brier score for predicting different fixed probability values
    predictions = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
    losses = [brier_score_loss(testy, [y for x in range(len(testy))]) for y in predictions]
    # plot predictions vs loss
    if plot is True:
        pyplot.plot(predictions, losses)
        pyplot.show()
    return {'predictions': predictions, 'losses': losses}

def unbalanceBrierScore(goal=20, plot=False):
    # plot impact of brier score with imbalanced datasets
    # define an imbalanced dataset
    testy = [0 for x in range(goal)] + [1 for x in range(10)]
    # brier score for predicting different fixed probability values
    predictions = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
    losses = [brier_score_loss(testy, [y for x in range(len(testy))]) for y in predictions]
    # plot predictions vs loss
    if plot is True:
        pyplot.plot(predictions, losses)
        pyplot.show()
    return {'predictions': predictions, 'losses': losses}

    # BS: Brier skill of model
    # BS_ref: Brier skill of the naive prediction
    # Brier Skill Score reports the relative skill of the probability
    # prediction over the naive forecast.
def brierScoreLoss(bs, bsRef):
    return 1 - (bs / bsRef)

# roc curve
# fpr: Lower curve
# tpr: Upper curve
def rocCurve(samples=1000, plot=False):
    # generate 2 class dataset
    X, y = make_classification(n_samples=samples, n_classes=2, random_state=1)
    # split into train/test sets
    trainX, testX, trainy, testy = train_test_split(X, y, test_size=0.5,
                                                    random_state=2)
    # fit a model
    model = LogisticRegression(solver='lbfgs')
    model.fit(trainX, trainy)
    # predict probabilities
    probs = model.predict_proba(testX)
    # keep probabilities for the positive outcome only
    probs = probs[:, 1]
    # calculate roc curve
    fpr, tpr, thresholds = roc_curve(testy, probs)
    # plot no skill
    if plot is True:
        pyplot.plot([0, 1], [0, 1], linestyle='--')
        # plot the roc curve for the model
        pyplot.plot(fpr, tpr)
        # show the plot
        pyplot.show()
    return {'fpr': fpr, 'tpr': tpr}

def rocAuc(samples=1000):
    # generate 2 class dataset
    X, y = make_classification(n_samples=samples, n_classes=2, random_state=1)
    # split into train/test sets
    trainX, testX, trainy, testy = train_test_split(X, y, test_size=0.5,
                                                    random_state=2)
    # fit a model
    model = LogisticRegression(solver='lbfgs')
    model.fit(trainX, trainy)
    # predict probabilities
    probs = model.predict_proba(testX)
    # keep probabilities for the positive outcome only
    probs = probs[:, 1]
    # calculate roc auc
    return roc_auc_score(testy, probs)
