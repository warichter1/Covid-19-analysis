#!/bin/sh
currentDate=`date`
echo $currentDate

cd /home/wrichter/Documents/Code/Projects/Python/Covid-19-analysis/

/usr/bin/python3 CovidDLModel.py True
/usr/bin/python3 CovidDLModelUSStates_v2.py True
# git pull
# git add ./plots/*
# git add ./data/*
# git commit -c "Add Daily Results"
# git push

