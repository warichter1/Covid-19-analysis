#!/bin/sh

cd /home/wrichter/Documents/Code/Projects/Python/Covid-19-analysis/

/usr/local/anaconda3/bin/python CovidDLModel.py True
/usr/local/anaconda3/bin/python CovidDLModelUSStates_v2.py True
# git pull
# git add ./plots/*
# git add ./data/*
# git commit -c "Add Daily Results"
# git push

