
import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np
import pandas as pd
import os
import sys 
from HARK.utilities import make_figs

cwd             = os.getcwd()
folders         = cwd.split(os.path.sep)
top_most_folder = folders[-1]
if top_most_folder == 'FromPandemicCode':
    Abs_Path = cwd
    figs_dir = '../../../Figures'
    res_dir = '../Results'
else:
    Abs_Path = cwd + '\\FromPandemicCode'
    figs_dir = '../../Figures'
    res_dir = 'Results'
sys.path.append(Abs_Path)

plt.style.use('classic')

plotToMake = [0,1,2]
# 0 = Data + model with Splurge = 0
# 1 = Data + model with Splurge = estimated
# 2 = Data + both models

# Define the agg MPCx targets from Fagereng et al. Figure 2; first element is same-year response, 2nd element, t+1 response etcc
Agg_MPCX_data = np.array([0.5056845, 0.1759051, 0.1035106, 0.0444222, 0.0336616])

resFileSplEst = open(res_dir+'/AllResults_CRRA_2.0_R_1.01.txt', 'r')  

for line in resFileSplEst:
    if "IMPCs" in line:
        theIMPCstr = line[line.find('[')+1:line.find(']')].split(', ')
        IMPCsSplEst = []
        for ii in range(0,len(theIMPCstr)):
            IMPCsSplEst.append(float(theIMPCstr[ii]))

resFileSplZero = open(res_dir+'/AllResults_CRRA_2.0_R_1.01_Splurge0.txt', 'r')

for line in resFileSplZero:
    if "IMPCs" in line:
        theIMPCstr = line[line.find('[')+1:line.find(']')].split(', ')
        IMPCsSplZero = []
        for ii in range(0,len(theIMPCstr)):
            IMPCsSplZero.append(float(theIMPCstr[ii]))

for thePlots in plotToMake:
    fig = plt.figure(figsize=(7,6))
    xAxis = np.arange(0,5)
    
    theLegend = []
    if thePlots==0 or thePlots==2:
        plt.plot(xAxis, IMPCsSplZero, 'r:', linewidth=2)
        theLegend.append('Model w/splurge=0')
    if thePlots == 1 or thePlots==2:
        plt.plot(xAxis, IMPCsSplEst, 'b-', linewidth=2)
        theLegend.append('Model w/estimated splurge')
    
    plt.scatter(xAxis, Agg_MPCX_data, c='black', marker='o')
    theLegend.append('Fagereng, Holm and Natvik (2021)')
    plt.xticks(np.arange(min(xAxis), max(xAxis)+1, 1.0))
    plt.xlabel('Year')
    plt.ylabel('% of lottery win spent')
    plt.legend(theLegend, loc='upper right', fontsize=12)
    plt.grid(True)

    if thePlots==0:
        make_figs('IMPCs_wSplZero', True , False, target_dir=figs_dir)
    elif thePlots==1:
        make_figs('IMPCs_wSplEstimated', True , False, target_dir=figs_dir)
    else:
        make_figs('IMPCs_both', True , False, target_dir=figs_dir)

plt.show()