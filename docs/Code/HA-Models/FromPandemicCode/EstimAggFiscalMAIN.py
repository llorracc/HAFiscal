'''
This is the main script for estimating the discount factor distributions.
'''
import time
import sys 
import os 
from importlib import reload 
import numpy as np
import matplotlib.pyplot as plt
from copy import deepcopy
from collections import namedtuple 
import pickle
import random 
from HARK.distribution import DiscreteDistribution, Uniform
from HARK import multi_thread_commands, multi_thread_commands_fake
from HARK.utilities import get_percentiles, get_lorenz_shares
from HARK.estimation import minimize_nelder_mead

cwd             = os.getcwd()
folders         = cwd.split(os.path.sep)
top_most_folder = folders[-1]
if top_most_folder == 'FromPandemicCode':
    Abs_Path = cwd
    figs_dir = '../../../Figures'
    res_dir = '../Results'
else:
    Abs_Path = cwd + '/Code/HA-Models/FromPandemicCode'
    figs_dir = '../../Figures'
    res_dir = 'Results'
    os.chdir(Abs_Path)
sys.path.append(Abs_Path)

import EstimParameters as ep
reload(ep)  # Force reload in case the code is running from commandline for different values 

from EstimParameters import init_dropout, init_highschool, init_college, init_ADEconomy, DiscFacDstns,\
     DiscFacCount, CRRA, Splurge, IncUnemp, IncUnempNoBenefits, AgentCountTotal, base_dict, \
     UBspell_normal, data_LorenzPts, data_LorenzPtsAll, data_avgLWPI, data_LWoPI, \
     data_medianLWPI, data_EducShares, data_WealthShares, Rfree_base, \
     GICmaxBetas, theGICfactor, minBeta
from AggFiscalModel import AggFiscalType, AggregateDemandEconomy
mystr = lambda x : '{:.2f}'.format(x)
mystr4 = lambda x : '{:.4f}'.format(x)

print('Parameters: R = '+str(round(Rfree_base[0],3))+', CRRA = '+str(round(CRRA,2))
      +', IncUnemp = '+str(round(IncUnemp,2))+', IncUnempNoBenefits = '+str(round(IncUnempNoBenefits,2))
      +', Splurge = '+str(Splurge))


# -----------------------------------------------------------------------------
def calcEstimStats(Agents):
    '''
    Calculate the average LW/PI-ratio and total LW / total PI for each education
    type. Also calculate the 20th, 40th, 60th, and 80th percentile points of the
    Lorenz curve for (liquid) wealth for all agents. 
    Assumption: Agents is organized by EducType and there are DiscFacCount
    AgentTypes of each EducType. 
    
    Parameters
    ----------
    Agents : [AgentType]
        List of AgentTypes in the economy.
        
    Returns
    -------
    Stats : namedtuple("avgLWPI", "LWoPI", "LorenzPts")
    avgLWPI : [float] 
        The weighted average of LW/PI-ratio for each education type.
    LWoPI : [float]
        Total liquid wealth / total permanent income for each education type. 
    LorenzPts : [float]
        The 20th, 40th, 60th, and 80th percentile points of the Lorenz curve for 
        (liquid) wealth.
    '''

    aLvlAll = np.concatenate([ThisType.state_now["aLvl"] for ThisType in Agents])
    numAgents = 0
    for ThisType in Agents: 
        numAgents += ThisType.AgentCount
    weights = np.ones(numAgents) / numAgents      # just using equal weights for now

    # Lorenz points:
    LorenzPts = 100*get_lorenz_shares(aLvlAll, weights=weights, percentiles = [0.2, 0.4, 0.6, 0.8] )

    avgLWPI = [0]*num_types
    LWoPI = [0]*num_types 
    medianLWPI = [0]*num_types 
    for e in range(num_types):
        aNrmAll_byEd = []
        aNrmAll_byEd = np.concatenate([(1-ThisType.Splurge)*ThisType.state_now['aNrm'] for ThisType in \
                          Agents[e*DiscFacCount:(e+1)*DiscFacCount]])
        weights = np.ones(len(aNrmAll_byEd))/len(aNrmAll_byEd)
        avgLWPI[e] = np.dot(aNrmAll_byEd, weights) * 100
        
        aLvlAll_byEd = []
        aLvlAll_byEd = np.concatenate([ThisType.state_now["aLvl"] for ThisType in \
                          Agents[e*DiscFacCount:(e+1)*DiscFacCount]])
        pLvlAll_byEd = []
        pLvlAll_byEd = np.concatenate([ThisType.state_now['pLvl'] for ThisType in \
                          Agents[e*DiscFacCount:(e+1)*DiscFacCount]])
        LWoPI[e] = np.dot(aLvlAll_byEd, weights) / np.dot(pLvlAll_byEd, weights) * 100

        medianLWPI[e] = 100*get_percentiles(aNrmAll_byEd,weights=weights,percentiles=[0.5])

    Stats = namedtuple("Stats", ["avgLWPI", "LWoPI", "medianLWPI", "LorenzPts"])

    return Stats(avgLWPI, LWoPI, medianLWPI, LorenzPts) 
# -----------------------------------------------------------------------------
def calcWealthShareByEd(Agents):
    '''
    Calculate the share of total wealth held by each education type. 
    Assumption: Agents is organized by EducType and there are DiscFacCount
    AgentTypes of each EducType. 
    
    Parameters
    ----------
    Agents : [AgentType]
        List of all AgentTypes in the economy. They are assumed to differ in 
        their EducType attribute.

    Returns
    -------
    WealthShares : np.array(float)
        The share of total liquid wealth held by each education type. 
    '''
    aLvlAll = np.concatenate([ThisType.state_now["aLvl"] for ThisType in Agents])
    totLiqWealth = np.sum(aLvlAll)
    
    WealthShares = [0]*num_types
    for e in range(num_types):
        aLvlAll_byEd = []
        aLvlAll_byEd = np.concatenate([ThisType.state_now["aLvl"] for ThisType in \
                                       Agents[e*DiscFacCount:(e+1)*DiscFacCount]])
        WealthShares[e] = np.sum(aLvlAll_byEd)/totLiqWealth * 100
    
    return np.array(WealthShares)
# -----------------------------------------------------------------------------
def calcLorenzPts(Agents):
    '''
    Calculate the 20th, 40th, 60th, and 80th percentile points of the
    Lorenz curve for (liquid) wealth for the given set of Agents. 

    Parameters
    ----------
    Agents : [AgentType]
        List of AgentTypes.

    Returns
    -------
    LorenzPts : [float]
        The 20th, 40th, 60th, and 80th percentile points of the Lorenz curve for 
        (liquid) wealth.
    '''
    aLvlAll = np.concatenate([ThisType.state_now["aLvl"] for ThisType in Agents])
    numAgents = 0
    for ThisType in Agents: 
        numAgents += ThisType.AgentCount
    weights = np.ones(numAgents) / numAgents      # just using equal weights for now
    
    # Lorenz points:
    LorenzPts = 100*get_lorenz_shares(aLvlAll, weights=weights, percentiles = [0.2, 0.4, 0.6, 0.8] )

    return LorenzPts
# -----------------------------------------------------------------------------
def calcMPCbyEd(Agents):
    '''
    Calculate the average MPC for each education type. 
    Assumption: Agents is organized by EducType and there are DiscFacCount
    AgentTypes of each EducType. 
    
    Parameters
    ----------
    Agents : [AgentType]
        List of all AgentTypes in the economy. They are assumed to differ in 
        their EducType attribute.

    Returns
    -------
    MPCs : namedtuple("MPCsQ", "MPCsA")    
    MPCsQ : [float]
        The average MPC for each education type - Quarterly, ignores splurge.
    MPCsA : [float]
        The average MPC for each education type - Annualized, taking splurge into account. 
        (Only splurge in the first quarter.)
    '''
    MPCsQ = [0]*(num_types+1)   # MPC for each eduation type + for whole population
    MPCsA = [0]*(num_types+1)   # Annual MPCs with splurge (each ed. type + population)
    for e in range(num_types):
        MPC_byEd_Q = []
        MPC_byEd_Q = np.concatenate([ThisType.MPCnow for ThisType in \
                                       Agents[e*DiscFacCount:(e+1)*DiscFacCount]])

        MPC_byEd_A = Splurge + (1-Splurge)*MPC_byEd_Q
        for qq in range(3):
            MPC_byEd_A += (1-MPC_byEd_A)*MPC_byEd_Q
        
        MPCsQ[e] = np.mean(MPC_byEd_Q)
        MPCsA[e] = np.mean(MPC_byEd_A)
        
    MPC_all_Q = np.concatenate([ThisType.MPCnow for ThisType in Agents])
    MPC_all_A = Splurge + (1-Splurge)*MPC_all_Q
    for qq in range(3):
        MPC_all_A += (1-MPC_all_A)*MPC_all_Q
    
    MPCsQ[e+1] = np.mean(MPC_all_Q)
    MPCsA[e+1] = np.mean(MPC_all_A)

    MPCs = namedtuple("MPCs", ["MPCsQ", "MPCsA"])
 
    return MPCs(MPCsQ,MPCsA)
 
# -----------------------------------------------------------------------------
def calcMPCbyWealth(Agents):
    '''
    Calculate the average MPC for each wealth quartile. 
    Assumption: Agents is organized by EducType and there are DiscFacCount
    AgentTypes of each EducType. 
    
    Parameters
    ----------
    Agents : [AgentType]
        List of all AgentTypes in the economy. They are assumed to differ in 
        their EducType attribute.

    Returns
    -------
    MPCs : namedtuple("MPCsQ", "MPCsA")    
    MPCsQ : [float]
        The average MPC for each wealth quartile - Quarterly, ignores splurge.
    MPCsA : [float]
        The average MPC for each wealth quartile - Annualized, taking splurge into account. 
        (Only splurge in the first quarter.)
    '''
    WealthNow = np.concatenate([ThisType.state_now["aLvl"] for ThisType in Agents])
    
    # Get wealth quartile cutoffs and distribute them to each consumer type
    quartile_cuts = get_percentiles(WealthNow,percentiles=[0.25,0.50,0.75])
    WealthQsAll = np.array([])
    for ThisType in Agents:
        WealthQ = np.zeros(ThisType.AgentCount,dtype=int)
        for n in range(3):
            WealthQ[ThisType.state_now["aLvl"] > quartile_cuts[n]] += 1
        ThisType(WealthQ = WealthQ)
        WealthQsAll = np.concatenate([WealthQsAll, WealthQ])
    
    MPC_agents_Q = np.concatenate([ThisType.MPCnow for ThisType in Agents])
    # Annual MPC: first Q includes Splurge, other three Qs do not
    MPC_agents_A = Splurge+(1-Splurge)*MPC_agents_Q
    for qq in range(3):
        MPC_agents_A += (1-MPC_agents_A)*MPC_agents_Q

    MPCsQ = [0]*(4+1)       # MPC for each quartile + for whole population
    MPCsA = [0]*(4+1)       # Annual MPCs with splurge (each quartile + population)
    # Mean MPCs for each of the 4 quartiles of wealth + all agents         
    for qq in range(4):
        MPCsQ[qq] = np.mean(MPC_agents_Q[WealthQsAll==qq])
        MPCsA[qq] = np.mean(MPC_agents_A[WealthQsAll==qq])
    MPCsQ[4] = np.mean(MPC_agents_Q)
    MPCsA[4] = np.mean(MPC_agents_A)
    
    MPCs = namedtuple("MPCs", ["MPCsQ", "MPCsA"])
 
    return MPCs(MPCsQ,MPCsA)    
 
# -----------------------------------------------------------------------------
def checkDiscFacDistribution(beta, nabla, GICfactor, educ_type, print_mode=False, print_file=False, filename='DefaultResultsFile.txt'):
    '''
    Calculate max and min discount factors in discrete approximation to uniform 
    distribution of discount factors. Also report if most patient agents satisfies 
    the growth impatience condition. 
    
    Parameters
    ----------
    beta : float
        Central value of the discount factor distribution for this education group.
    nabla : float
        Half the width of the discount factor distribution.
    GICfactor : float
        How close to the GIC-imposed upper bound the highest beta is allowed to be.
    educ_type : int 
        Denotes the education type (either 0, 1 or 2). 
    print_mode : boolean, optional
        If true, results are printed to the screen. The default is False.
    print_file : boolean, optional
        If true, statistics are appended to the file filename. The default is False. 
    filename : str
        Filename for printing calculated statistics. The default is DefaultResultsFile.txt.
    
    Returns
    -------
    dfCheck : namedtuple("betaMin", "betaMax", "GICsatisfied")    
    betaMin : float
        Minimum value in discrete approximation to discount factor distribution.
    betaMax : float
        Maximum value in discrete approximation to discount factor distribution.
    GICsatisfied : boolean
        True if betaMax satisfies the GIC for this education group. 
    '''
    DiscFacDstnBase = Uniform(beta-nabla, beta+nabla).discretize(DiscFacCount)
    betaMin = DiscFacDstnBase.atoms[0][0]
    betaMax = DiscFacDstnBase.atoms[0][DiscFacCount-1]
    GICsatisfied = (betaMax < GICmaxBetas[educ_type]*GICfactor)

    DiscFacDstnActual = DiscFacDstnBase.atoms[0].copy()    
    for thedf in range(DiscFacCount):
        if DiscFacDstnActual[thedf] > GICmaxBetas[educ_type]*GICfactor: 
            DiscFacDstnActual[thedf] = GICmaxBetas[educ_type]*GICfactor
        elif DiscFacDstnActual[thedf] < minBeta:
            DiscFacDstnActual[thedf] = minBeta

    if print_mode:
        print('Base approximation to beta distribution:\n'+str(np.round(DiscFacDstnBase.atoms[0],4))+'\n')
        print('Actual approximation to beta distribution:\n'+str(np.round(DiscFacDstnActual,4))+'\n')
        print('GIC satisfied = '+str(GICsatisfied)+'\tGICmaxBeta = '+str(round(GICmaxBetas[educ_type],4))+'\n')
        print('Imposed GIC consistent maximum beta = ' + str(round(GICmaxBetas[educ_type]*GICfactor,5))+'\n\n')
        
    if print_file:
        with open(filename, 'a') as resFile: 
            resFile.write('\tBase approximation to beta distribution:\n\t'+str(np.round(DiscFacDstnBase.atoms[0],4))+'\n')
            resFile.write('\tActual approximation to beta distribution:\n\t'+str(np.round(DiscFacDstnActual,4))+'\n')
            resFile.write('\tGIC satisfied = '+str(GICsatisfied)+'\tGICmaxBeta = '+str(round(GICmaxBetas[educ_type],4))+'\n')
            resFile.write('\tImposed GIC-consistent maximum beta = ' + str(round(GICmaxBetas[educ_type]*GICfactor,5))+'\n\n')
    
    dfCheck = namedtuple("dfCheck", ["betaMin", "betaMax", "GICsatisfied"])
    return dfCheck(betaMin, betaMax, GICsatisfied)    

# =============================================================================
#%% Initialize economy
# Make education types
num_types = 3
# This is not the number of discount factors, but the number of household types

InfHorizonTypeAgg_d = AggFiscalType(**init_dropout)
InfHorizonTypeAgg_d.cycles = 0
InfHorizonTypeAgg_h = AggFiscalType(**init_highschool)
InfHorizonTypeAgg_h.cycles = 0
InfHorizonTypeAgg_c = AggFiscalType(**init_college)
InfHorizonTypeAgg_c.cycles = 0
AggDemandEconomy = AggregateDemandEconomy(**init_ADEconomy)
InfHorizonTypeAgg_d.get_economy_data(AggDemandEconomy)
InfHorizonTypeAgg_h.get_economy_data(AggDemandEconomy)
InfHorizonTypeAgg_c.get_economy_data(AggDemandEconomy)
BaseTypeList = [InfHorizonTypeAgg_d, InfHorizonTypeAgg_h, InfHorizonTypeAgg_c ]
      
# Fill in the Markov income distribution for each base type
# NOTE: THIS ASSUMES NO LIFECYCLE
IncomeDstn_unemp = DiscreteDistribution(np.array([1.0]), [np.array([1.0]), np.array([InfHorizonTypeAgg_d.IncUnemp])])
IncomeDstn_unemp_nobenefits = DiscreteDistribution(np.array([1.0]), [np.array([1.0]), np.array([InfHorizonTypeAgg_d.IncUnempNoBenefits])])
    
for ThisType in BaseTypeList:
    EmployedIncomeDstn = deepcopy(ThisType.IncShkDstn[0])
    ThisType.IncShkDstn = [[ThisType.IncShkDstn[0]] + [IncomeDstn_unemp]*UBspell_normal + [IncomeDstn_unemp_nobenefits]]
    ThisType.IncomeDstn_base = ThisType.IncShkDstn
    
# Make the overall list of types
TypeList = []
n = 0
for e in range(num_types):
    for b in range(DiscFacCount):
        DiscFac = DiscFacDstns[e].atoms[0][b]
        AgentCount = int(np.floor(AgentCountTotal*data_EducShares[e]*DiscFacDstns[e].pmv[b]))
        ThisType = deepcopy(BaseTypeList[e])
        ThisType.AgentCount = AgentCount
        ThisType.DiscFac = DiscFac
        ThisType.seed = n
        TypeList.append(ThisType)
        n += 1
base_dict['Agents'] = TypeList    

AggDemandEconomy.agents = TypeList
AggDemandEconomy.solve()

AggDemandEconomy.reset()
for agent in AggDemandEconomy.agents:
    agent.initialize_sim()
    agent.AggDemandFac = 1.0
    agent.RfreeNow = 1.0
    agent.CaggNow = 1.0

AggDemandEconomy.make_history()   
AggDemandEconomy.save_state()   
#AggDemandEconomy.switchToCounterfactualMode("base")
#AggDemandEconomy.makeIdiosyncraticShockHistories()

output_keys = ['NPV_AggIncome', 'NPV_AggCons', 'AggIncome', 'AggCons']


#%% Objective functions
# -----------------------------------------------------------------------------
def betasObjFunc(betas, spreads, GICfactors, target_option=1, print_mode=False, print_file=False, filename='DefaultResultsFile.txt'):
    '''
    Objective function for the estimation of discount factor distributions for the 
    three education groups. The groups can differ in the centering of their discount 
    factor distributions, and in the spread around the central value.
    
    Parameters
    ----------
    betas : [float]
        Central values of the discount factor distributions for each education
        level.
    spreads : [float]
        Half the width of each discount factor distribution. If we want the same spread
        for each education group we simply impose that the spreads are all the same.
        That is done outside this function.
    GICfactors : [float]
        How close to the GIC-imposed upper bound the highest betas are allowed to be. 
        If we want the same GICfactor for each education group we simply impose that 
        the GICfactors are all the same.
    target_option : integer
        = 1: Target medianLWPI and LorenzPtsAll 
        = 2: Target avgLWPI and LorenzPts_d, _h and _c
    print_mode : boolean, optional
        If true, statistics for each education level are printed. The default is False.
    print_file : boolean, optional
        If true, statistics are appended to the file filename. The default is False. 
    filename : str
        Filename for printing calculated statistics. The default is DefaultResultsFile.txt.
    
    Returns
    -------
    distance : float
        The distance of the estimation targets between those in the data and those
        produced by the model. 
    '''
    # # Set seed to ensure distance only changes due to different parameters 
    # random.seed(1234)

    beta_d, beta_h, beta_c = betas
    spread_d, spread_h, spread_c = spreads

    # # Overwrite the discount factor distribution for each education level with new values
    dfs_d = Uniform(beta_d-spread_d, beta_d+spread_d).discretize(DiscFacCount)
    dfs_h = Uniform(beta_h-spread_h, beta_h+spread_h).discretize(DiscFacCount)
    dfs_c = Uniform(beta_c-spread_c, beta_c+spread_c).discretize(DiscFacCount)
    dfs = [dfs_d, dfs_h, dfs_c]

    # Check GIC for each type:
    for e in range(num_types):
        for thedf in range(DiscFacCount):
            if dfs[e].atoms[0][thedf] > GICmaxBetas[e]*GICfactors[e]: 
                dfs[e].atoms[0][thedf] = GICmaxBetas[e]*GICfactors[e]
            elif dfs[e].atoms[0][thedf] < minBeta:
                dfs[e].atoms[0][thedf] = minBeta

    # Make a new list of types with updated discount factors 
    TypeListNew = []
    n = 0
    for e in range(num_types):
        for b in range(DiscFacCount):
            AgentCount = int(np.floor(AgentCountTotal*data_EducShares[e]*dfs[e].pmv[b]))
            ThisType = deepcopy(BaseTypeList[e])
            ThisType.AgentCount = AgentCount
            ThisType.DiscFac = dfs[e].atoms[0][b]
            ThisType.seed = n
            TypeListNew.append(ThisType)
            n += 1
    base_dict['Agents'] = TypeListNew

    AggDemandEconomy.agents = TypeListNew
    AggDemandEconomy.solve()

    AggDemandEconomy.reset()
    for agent in AggDemandEconomy.agents:
        agent.initialize_sim()
        agent.AggDemandFac = 1.0
        agent.RfreeNow = 1.0
        agent.CaggNow = 1.0

    AggDemandEconomy.make_history()   
    AggDemandEconomy.save_state()   

    # Simulate each type to get a new steady state solution 
    # solve: done in AggDemandEconomy.solve(), initializeSim: done in AggDemandEconomy.reset() 
    # baseline_commands = ['solve()', 'initializeSim()', 'simulate()', 'saveState()']
    baseline_commands = ['simulate()', 'save_state()']
    multi_thread_commands_fake(TypeListNew, baseline_commands)
    
    Stats = calcEstimStats(TypeListNew)
    
    if target_option == 1:
        sumSquares = 10*np.sum((Stats.medianLWPI-data_medianLWPI)**2)
        sumSquares += np.sum((np.array(Stats.LorenzPts) - data_LorenzPtsAll)**2)
    elif target_option == 2:
        lp_d = calcLorenzPts(TypeListNew[0:DiscFacCount])
        lp_h = calcLorenzPts(TypeListNew[DiscFacCount:2*DiscFacCount])
        lp_c = calcLorenzPts(TypeListNew[2*DiscFacCount:3*DiscFacCount])
        sumSquares = np.sum((np.array(Stats.avgLWPI)-data_avgLWPI)**2)
        sumSquares += np.sum((np.array(lp_d)-data_LorenzPts[0])**2)
        sumSquares += np.sum((np.array(lp_h)-data_LorenzPts[1])**2)
        sumSquares += np.sum((np.array(lp_c)-data_LorenzPts[2])**2)
    
    distance = np.sqrt(sumSquares)

    if print_mode or print_file:
        WealthShares = calcWealthShareByEd(TypeListNew)
        MPCsByEd = calcMPCbyEd(TypeListNew)
        MPCsByW  = calcMPCbyWealth(TypeListNew)

    # If not estimating, print stats by education level
    if print_mode:
        print('Dropouts: beta = ', mystr(beta_d), ' spread = ', mystr(spread_d))
        print('Highschool: beta = ', mystr(beta_h), ' spread = ', mystr(spread_h))
        print('College: beta = ', mystr(beta_c), ' spread = ', mystr(spread_c))
        print('Median LW/PI-ratios: D = ' + mystr(Stats.medianLWPI[0][0]) + ' H = ' + mystr(Stats.medianLWPI[1][0]) \
              + ' C = ' + mystr(Stats.medianLWPI[2][0])) 
        print('Lorenz shares - all:')
        print(Stats.LorenzPts)
        if target_option == 2:
            print('Lorenz shares - Dropouts:')
            print(lp_d)
            print('Lorenz shares - Highschool:')
            print(lp_h)
            print('Lorenz shares - College:')
            print(lp_c) 
        
        print('Distance = ' + mystr(distance))
        print('Average LW/PI-ratios: D = ' + mystr(Stats.avgLWPI[0]) + ' H = ' + mystr(Stats.avgLWPI[1]) \
              + ' C = ' + mystr(Stats.avgLWPI[2])) 
        print('Total LW/Total PI: D = ' + mystr(Stats.LWoPI[0]) + ' H = ' + mystr(Stats.LWoPI[1]) \
              + ' C = ' + mystr(Stats.LWoPI[2]))
        print('Wealth Shares: D = ' + mystr(WealthShares[0]) + \
              ' H = ' + mystr(WealthShares[1]) + ' C = ' + mystr(WealthShares[2]))
        print('Average MPCs by Ed. (incl. splurge) = ['+str(round(MPCsByEd.MPCsA[0],3))+', '
                      +str(round(MPCsByEd.MPCsA[1],3))+', '+str(round(MPCsByEd.MPCsA[2],3))+', '
                      +str(round(MPCsByEd.MPCsA[3],3))+']')
        print('Average MPCs by Wealth (incl. splurge) = ['+str(round(MPCsByW.MPCsA[0],3))+', '
                      +str(round(MPCsByW.MPCsA[1],3))+', '+str(round(MPCsByW.MPCsA[2],3))+', '
                      +str(round(MPCsByW.MPCsA[3],3))+', '+str(round(MPCsByW.MPCsA[4],3))+']\n')

    if print_file:
        with open(filename, 'a') as resFile: 
            resFile.write('Population calculations:\n')
            resFile.write('\tMedian LW/PI-ratios = ['+mystr(Stats.medianLWPI[0][0])+', '+ 
                          mystr(Stats.medianLWPI[1][0])+', '+mystr(Stats.medianLWPI[2][0])+']\n')
            resFile.write('\tLorenz Points = ['+str(round(Stats.LorenzPts[0],4))+', '
                          +str(round(Stats.LorenzPts[1],4))+', '+str(round(Stats.LorenzPts[2],4))+', '
                          +str(round(Stats.LorenzPts[3],4))+']\n')
            resFile.write('\tWealth shares = ['+str(round(WealthShares[0],3))+', '
                          +str(round(WealthShares[1],3))+', '+str(round(WealthShares[2],3))+']\n')
            resFile.write('\tAverage MPCs by Ed. (incl. splurge) = ['+str(round(MPCsByEd.MPCsA[0],3))+', '
                          +str(round(MPCsByEd.MPCsA[1],3))+', '+str(round(MPCsByEd.MPCsA[2],3))+', '
                          +str(round(MPCsByEd.MPCsA[3],3))+']\n')
            resFile.write('\tAverage MPCs by Wealth (incl. splurge) = ['+str(round(MPCsByW.MPCsA[0],3))+', '
                          +str(round(MPCsByW.MPCsA[1],3))+', '+str(round(MPCsByW.MPCsA[2],3))+', '
                          +str(round(MPCsByW.MPCsA[3],3))+', '+str(round(MPCsByW.MPCsA[4],3))+']\n')
        
    return distance 
# -----------------------------------------------------------------------------
def betasObjFuncEduc(beta, spread, GICx, educ_type=2, print_mode=False, print_file=False, filename='DefaultResultsFile.txt'):
    '''
    Objective function for the estimation of a discount factor distribution for
    a single education group.
    
    Parameters
    ----------
    beta : float
        Central value of the discount factor distribution.
    spread : float
        Half the width of the discount factor distribution.
    GICx : float
        Number that determines how close to the GIC-imposed upper bound the highest beta is allowed to be.
    educ_type : integer
        The education type to estimate a discount factor distribution for.     
        Targets are avgLWPI[educ_type] and LorenzPts[educ_type]
    print_mode : boolean, optional
        If true, statistics are printed. The default is False.
    print_file : boolean, optional
        If true, statistics are appended to the file filename. The default is False. 
    filename : str
        Filename for printing calculated statistics. The default is DefaultResultsFile.txt.
    
    Returns
    -------
    distance : float
        The distance of the estimation targets between those in the data and those
        produced by the model. 
    '''
    # # Set seed to ensure distance only changes due to different parameters 
    # random.seed(1234)

    dfs = Uniform(beta-spread, beta+spread).discretize(DiscFacCount)
    
    # Check GIC:
    for thedf in range(DiscFacCount):
        if dfs.atoms[0][thedf] > GICmaxBetas[educ_type]*np.exp(GICx)/(1+np.exp(GICx)):
            dfs.atoms[0][thedf] = GICmaxBetas[educ_type]*(np.exp(GICx)/(1+np.exp(GICx)))
        elif dfs.atoms[0][thedf] < minBeta:
            dfs.atoms[0][thedf] = minBeta

    # Make a new list of types with updated discount factors for the given educ type
    TypeListNewEduc = []
    n = 0
    for b in range(DiscFacCount):
        AgentCount = int(np.floor(AgentCountTotal*data_EducShares[educ_type]*dfs.pmv[b]))
        ThisType = deepcopy(BaseTypeList[educ_type])
        ThisType.AgentCount = AgentCount
        ThisType.DiscFac = dfs.atoms[0][b]
        ThisType.seed = n
        TypeListNewEduc.append(ThisType)
        n += 1
    TypeListAll = AggDemandEconomy.agents
    TypeListAll[educ_type*DiscFacCount:(educ_type+1)*DiscFacCount] = TypeListNewEduc
            
    base_dict['Agents'] = TypeListAll
    AggDemandEconomy.agents = TypeListAll
    AggDemandEconomy.solve()

    AggDemandEconomy.reset()
    for agent in AggDemandEconomy.agents:
        agent.initialize_sim()
        agent.AggDemandFac = 1.0
        agent.RfreeNow = 1.0
        agent.CaggNow = 1.0

    AggDemandEconomy.make_history()   
    AggDemandEconomy.save_state()   

    # Simulate each type to get a new steady state solution 
    # solve: done in AggDemandEconomy.solve(), initializeSim: done in AggDemandEconomy.reset() 
    # baseline_commands = ['solve()', 'initializeSim()', 'simulate()', 'saveState()']
    baseline_commands = ['simulate()', 'save_state()']
    multi_thread_commands_fake(TypeListAll, baseline_commands)
    
    Stats = calcEstimStats(TypeListAll)
    
    sumSquares = np.sum((Stats.medianLWPI[educ_type]-data_medianLWPI[educ_type])**2)
    lp = calcLorenzPts(TypeListNewEduc)
    sumSquares += np.sum((np.array(lp) - data_LorenzPts[educ_type])**2)
#    sumSquares = np.sum((Stats.avgLWPI[educ_type]-data_avgLWPI[educ_type])**2)
   
    distance = np.sqrt(sumSquares)

    # If not estimating, print stats by education level
    if print_mode:
        print('Median LW/PI-ratio for group e = ' + mystr(educ_type) + ' is: ' \
              + mystr(Stats.medianLWPI[educ_type][0]))
        if educ_type == 0:
            print('Lorenz shares - Dropouts:')
        elif educ_type == 1:
            print('Lorenz shares - Highschool:')
        elif educ_type == 2:
            print('Lorenz shares - College:')
        print(lp)
        print('Distance = ' + mystr(distance))
        print('Non-targeted moments:')
        print('Average LW/PI-ratios for group e = ' + mystr(educ_type) + ' is: ' \
              + mystr(Stats.avgLWPI[educ_type]))
    
    if print_file:
        with open(filename, 'a') as resFile: 
            resFile.write('Education group = '+mystr(educ_type)+': beta = '+mystr4(beta)+
                          ', nabla = '+mystr4(spread)+', GICfactor = '+mystr4(np.exp(GICx)/(1+np.exp(GICx)))+'\n')
            resFile.write('\tMedian LW/PI-ratio = '+mystr(Stats.medianLWPI[educ_type][0])+'\n')
            resFile.write('\tLorenz Points = ['+str(round(lp[0],4))+', '+str(round(lp[1],4))+', '
                          +str(round(lp[2],4))+', '+str(round(lp[3],4))+']\n')
        
    return distance 
# -----------------------------------------------------------------------------
#%% Estimate discount factor distributions separately for each education type

if IncUnemp == 0.7 and IncUnempNoBenefits == 0.5:
    # Baseline unemployment system: 
    print('Estimating for CRRA = '+str(round(CRRA,1))+' and R = ' + str(round(Rfree_base[0],3))+':\n')
    df_resFileStr = res_dir+'/DiscFacEstim_CRRA_'+str(CRRA)+'_R_'+str(Rfree_base[0])
else:
    print('Estimating for an alternativ unemployment system with IncUnemp = '+str(round(IncUnemp,2))+
          ' and IncUnempNoBenefits = ' + str(round(IncUnempNoBenefits,2))+':\n')
    df_resFileStr = res_dir+'/DiscFacEstim_CRRA_'+str(CRRA)+'_R_'+str(Rfree_base[0])+'_altBenefits'

if Splurge == 0:
    print('Estimating for special case of Splurge = 0\n')
    df_resFileStr = df_resFileStr + '_Splurge0'
df_resFileStr = df_resFileStr + '.txt'

print('Estimation results saved in ' + df_resFileStr)

for edType in [0,1,2]:
    f_temp = lambda x : betasObjFuncEduc(x[0],x[1],x[2], educ_type=edType)
    if edType == 0:
        initValues = [0.75, 0.3, 6]       # Dropouts
    elif edType == 1:
        initValues = [0.93, 0.12, 5]      # HighSchool
    elif edType == 2:
        initValues = [0.98, 0.015, 6]     # College
    else:
        initValues = [0.90,0.02,6]

    opt_params = minimize_nelder_mead(f_temp, initValues, verbose=True)
    print('Finished estimating for education type = '+str(edType)+'. Optimal beta, spread and GIC factor are:')
    print('Beta = ' + mystr4(opt_params[0]) +'  Nabla = ' + mystr4(opt_params[1]) + 
          ' GIC factor = ' + mystr4(np.exp(opt_params[2])/(1+np.exp(opt_params[2]))))

    if edType == 0:
        mode = 'a'      # Overwrite old file...
    else:
        mode = 'a'      # ...but append all results in same file 
    with open(df_resFileStr, mode) as f: 
        outStr = repr({'EducationGroup' : edType, 'beta' : opt_params[0], 'nabla' : opt_params[1], 'GICx' : opt_params[2]})
        f.write(outStr+'\n')
        f.close()
        
with open(df_resFileStr, 'a') as f: 
    f.write('\nParameters: R = '+str(round(Rfree_base[0],2))+', CRRA = '+str(round(CRRA,2))
          +', IncUnemp = '+str(round(IncUnemp,2))+', IncUnempNoBenefits = '+str(round(IncUnempNoBenefits,2))
          +', Splurge = '+str(Splurge) +'\n')

#%% Read in estimates and calculate all results:
if IncUnemp == 0.7 and IncUnempNoBenefits == 0.5:
    # Baseline unemployment system: 
    print('Calculating all results for CRRA = '+str(round(CRRA,1))+' and R = ' + str(round(Rfree_base[0],3))+':\n')
    df_resFileStr = res_dir+'/DiscFacEstim_CRRA_'+str(CRRA)+'_R_'+str(Rfree_base[0])
    ar_resFileStr = res_dir+'/AllResults_CRRA_'+str(CRRA)+'_R_'+str(Rfree_base[0])
else:
    print('Calculating all results for an alternativ unemployment system with IncUnemp = '+str(round(IncUnemp,2))+
          ' and IncUnempNoBenefits = ' + str(round(IncUnempNoBenefits,2))+':\n')
    df_resFileStr = res_dir+'/DiscFacEstim_CRRA_'+str(CRRA)+'_R_'+str(Rfree_base[0])+'_altBenefits'
    ar_resFileStr = res_dir+'/AllResults_CRRA_'+str(CRRA)+'_R_'+str(Rfree_base[0])+'_altBenefits'

if Splurge == 0:
    df_resFileStr = df_resFileStr + '_Splurge0'
    ar_resFileStr = ar_resFileStr + '_Splurge0'
df_resFileStr = df_resFileStr + '.txt'
ar_resFileStr = ar_resFileStr + '.txt'
print('Loading estimates from ' + df_resFileStr + ' and saving all model results in ' + ar_resFileStr)

with open(ar_resFileStr, 'w') as resFile: 
    resFile.write('Results for parameters:\n')
    resFile.write('R = '+str(round(Rfree_base[0],2))+', CRRA = '+str(round(CRRA,2))
          +', IncUnemp = '+str(round(IncUnemp,2))+', IncUnempNoBenefits = '+str(round(IncUnempNoBenefits,2))
          +', Splurge = '+str(Splurge) +'\n\n')
           
# Calculate results by education group    
myEstim = [[],[],[]]
betFile = open(df_resFileStr, 'r')
readStr = betFile.readline().strip()
while readStr != '' :
    dictload = eval(readStr)
    edType = dictload['EducationGroup']
    beta = dictload['beta']
    nabla = dictload['nabla']
    GICx = dictload['GICx']
    GICfactor = np.exp(GICx)/(1+np.exp(GICx))
    myEstim[edType] = [beta,nabla,GICx, GICfactor]
    betasObjFuncEduc(beta, nabla, GICx, educ_type = edType, print_mode=True, print_file=True, filename=ar_resFileStr)
    checkDiscFacDistribution(beta, nabla, GICfactor, edType, print_mode=True, print_file=True, filename=ar_resFileStr)
    readStr = betFile.readline().strip()
betFile.close()

# Also calculate results for the whole population 
betasObjFunc([myEstim[0][0], myEstim[1][0], myEstim[2][0]], \
             [myEstim[0][1], myEstim[1][1], myEstim[2][1]], \
             [myEstim[0][3], myEstim[1][3], myEstim[2][3]], \
             target_option = 1, print_mode=True, print_file=True, filename=ar_resFileStr)



#%% 
run_additional_analysis = False

#%%
if run_additional_analysis:
    #betasObjFuncEduc(0.9838941233454087, 0.009553568500479719, 6, educ_type = 2, print_mode=True)

    ar_resFileStr = res_dir + 'DEBUG_checkDiscFacDistribution.txt'
    GICx = 6.0832796965018225
    GICfactor = np.exp(GICx)/(1+np.exp(GICx))
    checkDiscFacDistribution(0.7354184459881328, 0.29783637632458415, GICfactor, edType, print_mode=True, print_file=True, filename=ar_resFileStr)

# d - (0.72, 0.5)        
# h - (0.94, 0.7)



#%%
if run_additional_analysis:
    #%% Read in estimates and save resulting discount factor distributions:
    myEstim = [[],[],[]]
    if IncUnemp == 0.7 and IncUnempNoBenefits == 0.5:
        # Baseline unemployment system: 
        betFile = open(res_dir+'/DiscFacEstim_CRRA_'+str(CRRA)+'_R_'+str(Rfree_base[0])+'.txt', 'r')
    else:
        betFile = open(res_dir+'/DiscFacEstim_CRRA_'+str(CRRA)+'_R_'+str(Rfree_base[0])+'_altBenefits.txt', 'r')
    readStr = betFile.readline().strip()
    while readStr != '' :
        dictload = eval(readStr)
        edType = dictload['EducationGroup']
        beta = dictload['beta']
        nabla = dictload['nabla']
        GICx = dictload['GICx']
        GICfactor = np.exp(GICx)/(1+np.exp(GICx))
        myEstim[edType] = [beta,nabla,GICx,GICfactor]
        readStr = betFile.readline().strip()
    betFile.close()

    if IncUnemp == 0.7 and IncUnempNoBenefits == 0.5:
        # Baseline unemployment system: 
        outFileStr = res_dir+'/DiscFacDistributions_CRRA_'+str(CRRA)+'_R_'+str(Rfree_base[0])+'.txt'
    else:
        outFileStr = res_dir+'/DiscFacDistributions_CRRA_'+str(CRRA)+'_R_'+str(Rfree_base[0])+'_altBenefits.txt'
    outFile = open(outFileStr, 'w')
    
    for e in [0,1,2]:
        dfs = Uniform(myEstim[e][0]-myEstim[e][1], myEstim[e][0]+myEstim[e][1]).discretize(DiscFacCount)
        
        # Check GIC:
        for thedf in range(DiscFacCount):
            if dfs.atoms[0][thedf] > GICmaxBetas[e]*myEstim[e][3]:
                dfs.atoms[0][thedf] = GICmaxBetas[e]*myEstim[e][3]
            elif dfs.atoms[0][thedf] < minBeta:
                dfs.atoms[0][thedf] = minBeta
        theDFs = np.round(dfs.atoms[0],4)
        outStr = repr({'EducationGroup' : e, 'betaDistr' : theDFs.tolist()})
        outFile.write(outStr+'\n')
    outFile.close()
    

#%% Plot of MPCs
if run_additional_analysis:
    mpcs = calcMPCbyEd(AggDemandEconomy.agents)
    
    plt.plot(range(len(mpcs[0])), np.sort(mpcs[0]))
    plt.xlabel('Agents')
    plt.ylabel('MPCs')
    plt.title('Dropout')
    plt.show()
    
    plt.plot(range(len(mpcs[1])), np.sort(mpcs[1]))
    plt.xlabel('Agents')
    plt.ylabel('MPCs')
    plt.title('Highschool')
    plt.show()
    
    plt.plot(range(len(mpcs[2])), np.sort(mpcs[2]))
    plt.xlabel('Agents')
    plt.ylabel('MPCs')
    plt.title('College')
    plt.show()

