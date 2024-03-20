'''
Loads parameters used in the cstwMPC estimations.
'''

from __future__ import division, print_function

from builtins import range
import numpy as np
import csv
from copy import  deepcopy
import os


# Set basic parameters for the lifecycle micro model
init_age = 24                 # Starting age for agents
Rfree = 1.04**(0.25)          # Quarterly interest factor
working_T = 41*4              # Number of working periods
retired_T = 55*4              # Number of retired periods
T_cycle = working_T+retired_T # Total number of periods
CRRA = 1.0                    # Coefficient of relative risk aversion
DiscFac_guess = 0.99          # Initial starting point for discount factor
UnempPrb = 0.07               # Probability of unemployment while working
UnempPrbRet = 0.0005          # Probabulity of "unemployment" while retired
IncUnemp = 0.15               # Unemployment benefit replacement rate
IncUnempRet = 0.0             # Ditto when retired
BoroCnstArt = 0.0             # Artificial borrowing constraint

# Set grid sizes
PermShkCount = 5              # Number of points in permanent income shock grid
TranShkCount = 5              # Number of points in transitory income shock grid
aXtraMin = 0.00001            # Minimum end-of-period assets in grid
aXtraMax = 20                 # Maximum end-of-period assets in grid
aXtraCount = 20               # Number of points in assets grid
aXtraNestFac = 3              # Number of times to 'exponentially nest' when constructing assets grid
CubicBool = False             # Whether to use cubic spline interpolation
vFuncBool = False             # Whether to calculate the value function during solution
        
# Set simulation parameters
pop_sim_agg_point = 9600      # Total simulated population size, with aggregate shocks, param-point model
pop_sim_agg_dist  = 16800     # Total simulated population size, with aggregate shocks, param-dist model
pop_sim_ind_point = 10000     # Total simulated population size, no aggregate shocks, param-point model
pop_sim_ind_dist  = 14000     # Total simulated population size, no aggregate shocks, param-dist model
T_sim_PY = 1200               # Number of periods to simulate (idiosyncratic shocks model, perpetual youth)
T_sim_LC = 1200               # Number of periods to simulate (idiosyncratic shocks model, lifecycle)
T_sim_agg_shocks = 1200       # Number of periods to simulate (aggregate shocks model)
ignore_periods_PY = 400       # Number of periods to throw out when looking at history (perpetual youth)
ignore_periods_LC = 400       # Number of periods to throw out when looking at history (lifecycle)
T_age = T_cycle + 1           # Don't let simulated agents survive beyond this age
pLvlInitMean_d = np.log(5)    # average initial permanent income, dropouts
pLvlInitMean_h = np.log(7.5)  # average initial permanent income, HS grads
pLvlInitMean_c = np.log(12)   # average initial permanent income, college grads
pLvlInitStd = 0.4             # Standard deviation of initial permanent income
aNrmInitMean = np.log(0.5)    # log initial wealth/income mean
aNrmInitStd  = 0.5            # log initial wealth/income standard deviation

# Set population macro parameters
PopGroFac = 1.01**(0.25)      # Population growth rate
PermGroFacAgg = 1.015**(0.25) # TFP growth rate
d_pct = 0.11                  # proportion of HS dropouts
h_pct = 0.55                  # proportion of HS graduates
c_pct = 0.34                  # proportion of college graduates
TypeWeight_lifecycle = [d_pct,h_pct,c_pct]

# Set indiividual parameters for the infinite horizon model
IndL = 10.0/9.0               # Labor supply per individual (constant)
PermGroFac_i = [1.000**0.25]  # Permanent income growth factor (no perm growth)
DiscFac_i = 0.97              # Default intertemporal discount factor
LivPrb_i = [1.0 - 1.0/160.0]  # Survival probability
PermShkStd_i = [(0.01*4/11)**0.5] # Standard deviation of permanent shocks to income
TranShkStd_i = [(0.01*4)**0.5]    # Standard deviation of transitory shocks to income

# Define the paths of permanent and transitory shocks (from Sabelhaus and Song)
TranShkStd = (np.concatenate((np.linspace(0.1,0.12,17), 0.12*np.ones(17), np.linspace(0.12,0.075,61), np.linspace(0.074,0.007,68), np.zeros(retired_T+1)))*4)**0.5
TranShkStd = np.ndarray.tolist(TranShkStd)
PermShkStd = np.concatenate((((0.00011342*(np.linspace(24,64.75,working_T-1)-47)**2 + 0.01)/(11.0/4.0))**0.5,np.zeros(retired_T+1)))
PermShkStd = np.ndarray.tolist(PermShkStd)

# Set aggregate parameters for the infinite horizon model
PermShkAggCount = 3                # Number of discrete permanent aggregate shocks
TranShkAggCount = 3                # Number of discrete transitory aggregate shocks
PermShkAggStd = np.sqrt(0.00004)   # Standard deviation of permanent aggregate shocks
TranShkAggStd = np.sqrt(0.00001)   # Standard deviation of transitory aggregate shocks
CapShare = 0.36                    # Capital's share of output
DeprFac = 0.025                    # Capital depreciation factor
CRRAPF = 1.0                       # CRRA in perfect foresight calibration
DiscFacPF = 0.99                   # Discount factor in perfect foresight calibration
slope_prev = 1.0                   # Initial slope of kNextFunc (aggregate shocks model)
intercept_prev = 0.0               # Initial intercept of kNextFunc (aggregate shocks model)





# Make a dictionary for the infinite horizon type
init_infinite = {"CRRA":CRRA,
                "Rfree":1.01/LivPrb_i[0],
                "PermGroFac":PermGroFac_i,
                "PermGroFacAgg":1.0,
                "BoroCnstArt":BoroCnstArt,
                "CubicBool":CubicBool,
                "vFuncBool":vFuncBool,
                "PermShkStd":PermShkStd_i,
                "PermShkCount":PermShkCount,
                "TranShkStd":TranShkStd_i,
                "TranShkCount":TranShkCount,
                "UnempPrb":UnempPrb,
                "IncUnemp":IncUnemp,
                "UnempPrbRet":None,
                "IncUnempRet":None,
                "aXtraMin":aXtraMin,
                "aXtraMax":aXtraMax,
                "aXtraCount":aXtraCount,
                "aXtraExtra":[None],
                "aXtraNestFac":aXtraNestFac,
                "LivPrb":LivPrb_i,
                "DiscFac":DiscFac_i, # dummy value, will be overwritten
                "cycles":0,
                "T_cycle":1,
                "T_retire":0,
                'T_sim':T_sim_PY,
                'T_age': 400,
                'IndL': IndL,
                'aNrmInitMean':np.log(0.00001),
                'aNrmInitStd':0.0,
                'pLvlInitMean':0.0,
                'pLvlInitStd':0.0,
                'AgentCount':0, # will be overwritten by parameter distributor
                }

              

def main():
    print("Sorry, SetupParamsCSTWnew doesn't actually do anything on its own.")
    print("This module is imported by cstwMPCnew, providing data and calibrated")
    print("parameters for the various estimations.  Please see that module if")
    print("you want more interesting output.")

if __name__ == '__main__':
    main()

