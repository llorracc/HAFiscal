# %%
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


# %%
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

    aLvlAll = np.concatenate([(1-ThisType.Splurge)*ThisType.state_now["aLvl"] for ThisType in Agents])
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
        # aNrmAll_byEd = np.concatenate([ThisType.state_now['aNrm'] for ThisType in \
        #                   Agents[e*DiscFacCount:(e+1)*DiscFacCount]])
        weights = np.ones(len(aNrmAll_byEd))/len(aNrmAll_byEd)
        avgLWPI[e] = np.dot(aNrmAll_byEd, weights) * 100
        
        aLvlAll_byEd = []
        aLvlAll_byEd = np.concatenate([(1-ThisType.Splurge)*ThisType.state_now["aLvl"] for ThisType in \
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
    aLvlAll = np.concatenate([(1-ThisType.Splurge)*ThisType.state_now["aLvl"] for ThisType in Agents])
    totLiqWealth = np.sum(aLvlAll)
    
    WealthShares = [0]*num_types
    for e in range(num_types):
        aLvlAll_byEd = []
        aLvlAll_byEd = np.concatenate([(1-ThisType.Splurge)*ThisType.state_now["aLvl"] for ThisType in \
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
    aLvlAll = np.concatenate([(1-ThisType.Splurge)*ThisType.state_now["aLvl"] for ThisType in Agents])
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
        MPC_byEd_Q = np.concatenate([ThisType.MPCNow for ThisType in \
                                       Agents[e*DiscFacCount:(e+1)*DiscFacCount]])

        MPC_byEd_A = Splurge + (1-Splurge)*MPC_byEd_Q
        for qq in range(3):
            MPC_byEd_A += (1-MPC_byEd_A)*MPC_byEd_Q
        
        MPCsQ[e] = np.mean(MPC_byEd_Q)
        MPCsA[e] = np.mean(MPC_byEd_A)
        
    MPC_all_Q = np.concatenate([ThisType.MPCNow for ThisType in Agents])
    MPC_all_A = Splurge + (1-Splurge)*MPC_all_Q
    for qq in range(3):
        MPC_all_A += (1-MPC_all_A)*MPC_all_Q
    
    MPCsQ[e+1] = np.mean(MPC_all_Q)
    MPCsA[e+1] = np.mean(MPC_all_A)

    MPCs = namedtuple("MPCs", ["MPCsQ", "MPCsA"])
 
    return MPCs(MPCsQ,MPCsA)
 
# -----------------------------------------------------------------------------
def calcMPCbyWealthQsimple(Agents):
    '''
    Calculate the average annual MPC for each wealth quartile. 
    Assumption: Agents is organized by EducType and there are DiscFacCount
    AgentTypes of each EducType. 
    
    Parameters
    ----------
    Agents : [AgentType]
        List of all AgentTypes in the economy. They are assumed to differ in 
        their EducType attribute.

    Returns
    -------
    MPCs : namedtuple("MPCsQ", "MPCsA", "MPCsFYL")    
    MPCsQ : [float]
        The average MPC for each wealth quartile - Quarterly, ignores splurge.
    MPCsA : [float]
        The average MPC for each wealth quartile - Annualized, taking splurge into account. 
        (Only splurge in the first quarter.)
    MPCsFYL : [float]
        The average MPC for each wealth quartile - MPC in the year of a lottery win, 
        taking the splurge into account. For different individuals the lottery win happens
        in different quarters.
    '''
    WealthNow = np.concatenate([(1-ThisType.Splurge)*ThisType.state_now["aLvl"] for ThisType in Agents])
    
    # Get wealth quartile cutoffs and distribute them to each consumer type
    quartile_cuts = get_percentiles(WealthNow,percentiles=[0.25,0.50,0.75])
    WealthQsAll = np.array([])
    for ThisType in Agents:
        WealthQ = np.zeros(ThisType.AgentCount,dtype=int)
        for n in range(3):
            WealthQ[(1-ThisType.Splurge)*ThisType.state_now["aLvl"] > quartile_cuts[n]] += 1
        ThisType.WealthQ = WealthQ
        WealthQsAll = np.concatenate([WealthQsAll, WealthQ])
    
    MPC_agents_Q = np.concatenate([ThisType.MPCNow for ThisType in Agents])
    # Annual MPC: first Q includes Splurge, other three Qs do not
    MPC_agents_A = Splurge+(1-Splurge)*MPC_agents_Q
    for qq in range(3):
        MPC_agents_A += (1-MPC_agents_A)*MPC_agents_Q

    # Vector of how many quarters of spending each agent has after a lottery win
    SpendAfterLW_all = np.array([])
    for ThisType in Agents: 
        SpendQs = np.random.randint(0,4,ThisType.AgentCount)
        ThisType.SpendQs = SpendQs
        SpendAfterLW_all = np.concatenate([SpendAfterLW_all, SpendQs])
    
    MPC_agents_FYL = Splurge + (1-Splurge)*MPC_agents_Q
    for qq in range(1,4):
        MPC_agents_FYL[SpendAfterLW_all >= qq] += (1-MPC_agents_FYL[SpendAfterLW_all >= qq])*MPC_agents_Q[SpendAfterLW_all >= qq]
    
    MPCsQ = [0]*(4+1)       # MPC for each quartile + for whole population
    MPCsA = [0]*(4+1)       # Annual MPCs with splurge (each quartile + population)
    MPCsFYL = [0]*(4+1)     # First-year MPC in the year of a lottery win that occurs in a random quarter
    # Mean MPCs for each of the 4 quartiles of wealth + all agents         
    for qq in range(4):
        MPCsQ[qq] = np.mean(MPC_agents_Q[WealthQsAll==qq])
        MPCsA[qq] = np.mean(MPC_agents_A[WealthQsAll==qq])
        MPCsFYL[qq] = np.mean(MPC_agents_FYL[WealthQsAll==qq])
    MPCsQ[4] = np.mean(MPC_agents_Q)
    MPCsA[4] = np.mean(MPC_agents_A)
    MPCsFYL[4] = np.mean(MPC_agents_FYL)
    
    MPCs = namedtuple("MPCs", ["MPCsQ", "MPCsA", "MPCsFYL"])
 
    return MPCs(MPCsQ,MPCsA,MPCsFYL)    
 
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

# -----------------------------------------------------------------------------
def calcMPCbyWealthQ(Agents,lotterySize):
    '''
    Modified objective function to calculate MPCs by wealth in a consistent way. 

    Parameters
    ----------
    Agents : [AgentType]
        List of all AgentTypes in the economy. They are assumed to differ in 
        their EducType attribute.
    lotterySize : int 
        Size of lottery win in thousands of USD.

    Returns
    -------
    MPCsByWealthQ : [float]
        Array with MPCs for each wealth quartile for these agents. 
    '''

    TypeCount = len(Agents)
    multi_thread_commands_fake(Agents, ['solve()', 'initialize_sim()', 'simulate()', 'unpack_cFunc()'])
    WealthNow = np.concatenate([(1-ThisType.Splurge)*ThisType.state_now["aLvl"] for ThisType in Agents])

    # Get wealth quartile cutoffs and distribute them to each consumer type
    quartile_cuts = get_percentiles(WealthNow,percentiles=[0.25,0.50,0.75])
    WealthQsAll = np.array([])
    wealth_list = np.array([])
    betasAll = np.array([])
    PIsAll = np.array([])
    UnempAll = np.array([])
    educAll = np.array([])
    for ThisType in Agents:
        WealthQ = np.zeros(ThisType.AgentCount,dtype=int)
        for n in range(3):
            WealthQ[(1-ThisType.Splurge)*ThisType.state_now["aLvl"] > quartile_cuts[n]] += 1
        ThisType.WealthQ = WealthQ
        WealthQsAll = np.concatenate([WealthQsAll, WealthQ])
        wealth_list = np.concatenate((wealth_list, (1-ThisType.Splurge)*ThisType.state_now["aLvl"] ))
        betasAll = np.concatenate((betasAll, ThisType.DiscFac*np.ones(ThisType.AgentCount)))
        PIsAll = np.concatenate((PIsAll, ThisType.state_now["pLvl"]))
        UnempAll = np.concatenate((UnempAll, ThisType.MicroMrkvNow))
        educAll = np.concatenate((educAll, ThisType.EducType*np.ones(ThisType.AgentCount)))
    
    N_Quarter_Sim = 20; # Needs to be dividable by four
    N_Year_Sim = int(N_Quarter_Sim/4)
    N_Lottery_Win_Sizes = 5 # 4 lottery size bin + 1 representative one for agg MPCX
    
    # Calculate average PI and store the AgentCount for each education type
    PI_list_d = np.array([])
    PI_list_h = np.array([])
    PI_list_c = np.array([])
    agCount = np.zeros(3,dtype=int)
    for ThisType in Agents :
        if ThisType.EducType == 0:
            PI_list_d = np.concatenate((PI_list_d, ThisType.state_now["pLvl"]))
            agCount[0] = ThisType.AgentCount
        elif ThisType.EducType == 1:
            PI_list_h = np.concatenate((PI_list_h, ThisType.state_now["pLvl"]))
            agCount[1] = ThisType.AgentCount
        elif ThisType.EducType == 2:
            PI_list_c = np.concatenate((PI_list_c, ThisType.state_now["pLvl"]))
            agCount[2] = ThisType.AgentCount
    avgPI = [np.mean(PI_list_d), np.mean(PI_list_h), np.mean(PI_list_c)]

    # Lottery size in thousands of USD. This code only uses one lottery size
    lottery_size_vec = np.array([0, 0, 0, 0, lotterySize])
    lottery_size = np.zeros(5)  # Fill this in when needed

    EmptyList = [[],[],[],[],[]]
    MPC_set_list = [deepcopy(EmptyList),deepcopy(EmptyList),deepcopy(EmptyList),deepcopy(EmptyList)]
    MPC_Lists    = [deepcopy(MPC_set_list),deepcopy(MPC_set_list),deepcopy(MPC_set_list),deepcopy(MPC_set_list),deepcopy(MPC_set_list)]    
    # additional list for 5th Lottery bin, just need for elements for four years
    MPC_List_Add_Lottery_Bin = EmptyList
    MPC_this_type_d = np.zeros((TypeCount, agCount[0],N_Lottery_Win_Sizes,N_Year_Sim)) #Empty array, MPC for each Lottery size and agent
    MPC_this_type_h = np.zeros((TypeCount, agCount[1],N_Lottery_Win_Sizes,N_Year_Sim)) #Empty array, MPC for each Lottery size and agent
    MPC_this_type_c = np.zeros((TypeCount, agCount[2],N_Lottery_Win_Sizes,N_Year_Sim)) #Empty array, MPC for each Lottery size and agent

    k = 4 # Only one lottery size considered

    for type_num, ThisType in zip(range(TypeCount), Agents):
            
        c_base = np.zeros((ThisType.AgentCount,N_Quarter_Sim))                        #c_base (in case of no lottery win) for each quarter
        c_base_Lvl = np.zeros((ThisType.AgentCount,N_Quarter_Sim))                    #same in levels
        c_actu = np.zeros((ThisType.AgentCount,N_Quarter_Sim,N_Lottery_Win_Sizes))    #c_actu (actual consumption in case of lottery win in one random quarter) for each quarter and lottery size
        c_actu_Lvl = np.zeros((ThisType.AgentCount,N_Quarter_Sim,N_Lottery_Win_Sizes))#same in levels
        a_actu = np.zeros((ThisType.AgentCount,N_Quarter_Sim,N_Lottery_Win_Sizes))    #a_actu captures the actual market resources after potential lottery win (last index) was added and c_actu deducted
        T_hist = np.zeros((ThisType.AgentCount,N_Quarter_Sim))
        P_hist = np.zeros((ThisType.AgentCount,N_Quarter_Sim)) 
                
        # LotteryWin is an array with AgentCount x 4 periods many entries; there is only one 1 in each row indicating the quarter of the Lottery win for the agent in each row
        # This can be coded more efficiently
        LotteryWin = np.zeros((ThisType.AgentCount,N_Quarter_Sim))   
        for i in range(ThisType.AgentCount):
            LotteryWin[i,random.randint(0,3)] = 1
            
        # Scale lottery win with the average PI for this education group
        # lottery_size = lottery_size_vec/avgPI[ThisType.EducType]     
        lottery_size = lottery_size_vec   

        for period in range(N_Quarter_Sim): #Simulate for 4 quarters as opposed to 1 year
            
            # Simulate forward for one quarter
            ThisType.simulate(1)           
            
            # capture base consumption which is consumption in absence of lottery win
            c_base[:,period] = ThisType.controls["cNrm"] 
            c_base_Lvl[:,period] = c_base[:,period] * ThisType.state_now["pLvl"]
            
            # #for k in range(N_Lottery_Win_Sizes): # Loop through different lottery sizes, only this will produce values in simulated_MPC_means
            # k = 4; # do not loop to save time 
            
            Llvl = lottery_size[k]*LotteryWin[:,period]  #Lottery win occurs only if LotteryWin = 1 for that agent
            Lnrm = Llvl/ThisType.state_now["pLvl"]
            SplurgeNrm = ThisType.Splurge*Lnrm  #Splurge occurs only if LotteryWin = 1 for that agent
    
            R_kink = np.zeros((ThisType.AgentCount))       
            for i in range(ThisType.AgentCount):
                if a_actu[i,period-1,k] < 0:
                    R_kink[i] = Rfree_base[0] #base_params['Rboro']
                else:
                    R_kink[i] = Rfree_base[0] #base_params['Rsave']  
            
            if period == 0:
                m_adj = ThisType.state_now["mNrm"]  + Lnrm - SplurgeNrm
                for aa in range(0,ThisType.AgentCount):
                    c_actu[aa,period,k] = ThisType.cFunc[0][ThisType.MicroMrkvNow[aa]](m_adj[aa],1) + SplurgeNrm[aa]
                # c_actu[:,period,k] = ThisType.cFunc[0](m_adj) + SplurgeNrm
                c_actu_Lvl[:,period,k] = c_actu[:,period,k] * ThisType.state_now["pLvl"]
                a_actu[:,period,k] = ThisType.state_now["mNrm"] + Lnrm - c_actu[:,period,k] #save for next periods
            else:
                T_hist[:,period] = ThisType.shocks["TranShk"] 
                P_hist[:,period] = ThisType.shocks["PermShk"]
                for i_agent in range(ThisType.AgentCount):
                    if ThisType.shocks["TranShk"][i_agent] == 1.0: # indicator of death
                        a_actu[i_agent,period-1,k] = np.exp(np.log(0.00001)) #base_params['aNrmInitMean']
                m_adj = a_actu[:,period-1,k]*R_kink/ThisType.shocks["PermShk"] + ThisType.shocks["TranShk"] + Lnrm - SplurgeNrm #continue with resources from last period
                for aa in range(0,ThisType.AgentCount):
                    c_actu[aa,period,k] = ThisType.cFunc[0][ThisType.MicroMrkvNow[aa]](m_adj[aa],1) + SplurgeNrm[aa]
                # c_actu[:,period,k] = ThisType.cFunc[0](m_adj) + SplurgeNrm
                c_actu_Lvl[:,period,k] = c_actu[:,period,k] * ThisType.state_now["pLvl"]
                a_actu[:,period,k] = a_actu[:,period-1,k]*R_kink/ThisType.shocks["PermShk"] + ThisType.shocks["TranShk"] + Lnrm - c_actu[:,period,k] 
                
            if period%4 + 1 == 4: #if we are in the 4th quarter of a year
                year = int((period+1)/4)
                c_actu_Lvl_year = c_actu_Lvl[:,(year-1)*4:year*4,k]
                c_base_Lvl_year = c_base_Lvl[:,(year-1)*4:year*4]
                if ThisType.EducType == 0:
                    MPC_this_type_d[type_num,:,k,year-1] = (np.sum(c_actu_Lvl_year,axis=1) - np.sum(c_base_Lvl_year,axis=1))/(lottery_size[k])
                elif ThisType.EducType == 1:
                    MPC_this_type_h[type_num,:,k,year-1] = (np.sum(c_actu_Lvl_year,axis=1) - np.sum(c_base_Lvl_year,axis=1))/(lottery_size[k])
                elif ThisType.EducType == 2:
                    MPC_this_type_c[type_num,:,k,year-1] = (np.sum(c_actu_Lvl_year,axis=1) - np.sum(c_base_Lvl_year,axis=1))/(lottery_size[k])
                    
            # Sort the MPCs into the proper MPC sets
            for q in range(4):
                these = ThisType.WealthQ == q
                
                # for k in range(N_Lottery_Win_Sizes):
                #     for y in range(N_Year_Sim):
                #         MPC_Lists[k][q][y].append(MPC_this_type[type_num,these,k,y])
                for y in range(N_Year_Sim):
                    if ThisType.EducType == 0:
                        MPC_Lists[k][q][y].append(MPC_this_type_d[type_num,these,k,y])
                    elif ThisType.EducType == 1:
                        MPC_Lists[k][q][y].append(MPC_this_type_h[type_num,these,k,y])
                    elif ThisType.EducType == 2:
                        MPC_Lists[k][q][y].append(MPC_this_type_c[type_num,these,k,y])
                        
            # sort MPCs for addtional Lottery bin
            for y in range(N_Year_Sim):
                if ThisType.EducType == 0:
                    MPC_List_Add_Lottery_Bin[y].append(MPC_this_type_d[type_num,:,k,y])
                elif ThisType.EducType == 1:
                    MPC_List_Add_Lottery_Bin[y].append(MPC_this_type_h[type_num,:,k,y])
                elif ThisType.EducType == 0:
                    MPC_List_Add_Lottery_Bin[y].append(MPC_this_type_c[type_num,:,k,y])

    #Create a list of wealth and MPCs
    MPC_list = np.array([])
    for type_num, ThisType in zip(range(TypeCount), Agents):
        if ThisType.EducType == 0:
            MPC_list = np.concatenate((MPC_list, MPC_this_type_d[type_num, :, 4, 0] ))
        elif ThisType.EducType == 1:
            MPC_list = np.concatenate((MPC_list, MPC_this_type_h[type_num, :, 4, 0] ))
        elif ThisType.EducType == 2:
            MPC_list = np.concatenate((MPC_list, MPC_this_type_c[type_num, :, 4, 0] ))

    MPCbyWQ = np.zeros(5)
    betaByWQ = np.zeros(5)
    PIbyWQ = np.zeros(5)
    wealthByWQ = np.zeros(5)
    UnempByWQ = np.zeros(5)
    UnempAll = UnempAll > 0
    educByWQ = np.zeros(5)
    numWQ = np.zeros(5)
    for qq in range(4):
        MPCbyWQ[qq] = np.mean(MPC_list[WealthQsAll==qq])
        betaByWQ[qq] = np.mean(betasAll[WealthQsAll==qq])
        PIbyWQ[qq] = np.mean(PIsAll[WealthQsAll==qq])
        wealthByWQ[qq] = np.mean(wealth_list[WealthQsAll==qq])
        UnempByWQ[qq] = np.sum(UnempAll[WealthQsAll==qq])/np.sum(WealthQsAll==qq)
        educByWQ[qq] = np.mean(educAll[WealthQsAll==qq])
        numWQ[qq] = np.sum(WealthQsAll==qq)
    MPCbyWQ[4] = np.mean(MPC_list)
    betaByWQ[4] = np.mean(betasAll)
    PIbyWQ[4] = np.mean(PIsAll)
    wealthByWQ[4] = np.mean(wealth_list)
    UnempByWQ[4] = np.sum(UnempAll)/len(UnempAll)
    educByWQ[4] = np.mean(educAll)
    numWQ[4] = len(WealthQsAll)
    
    sorted_wealth_MPC = np.stack((wealth_list, MPC_list))[:,wealth_list.argsort()]
    total_agents = len(MPC_list)
    quartile1_weights = np.zeros(total_agents)
    quartile1_weights[0:int(np.floor(total_agents*9/40))] = 1.0
    quartile1_slope_length = (int(np.floor(total_agents*11/40)-np.floor(total_agents*9/40)))
    quartile1_weights[int(np.floor(total_agents*9/40)):int(np.floor(total_agents*11/40))] = (quartile1_slope_length-np.arange(quartile1_slope_length))/quartile1_slope_length
    quartile2_weights = np.zeros(total_agents)
    quartile2_weights[0:int(np.floor(total_agents*19/40))] = 1- quartile1_weights[0:int(np.floor(total_agents*19/40))]
    quartile2_slope_length = (int(np.floor(total_agents*21/40)-np.floor(total_agents*19/40)))
    quartile2_weights[int(np.floor(total_agents*19/40)):int(np.floor(total_agents*21/40))] = (quartile2_slope_length-np.arange(quartile2_slope_length))/quartile2_slope_length
    quartile3_weights = np.flip(quartile2_weights)
    quartile4_weights = np.flip(quartile1_weights)
    simulated_MPC_means_smoothed = np.zeros(5)
    simulated_MPC_means_smoothed[0] = np.average(sorted_wealth_MPC[1],weights=quartile1_weights)
    simulated_MPC_means_smoothed[1] = np.average(sorted_wealth_MPC[1],weights=quartile2_weights)
    simulated_MPC_means_smoothed[2] = np.average(sorted_wealth_MPC[1],weights=quartile3_weights)
    simulated_MPC_means_smoothed[3] = np.average(sorted_wealth_MPC[1],weights=quartile4_weights)
    simulated_MPC_means_smoothed[4] = np.average(sorted_wealth_MPC[1])
    
    # #if estimation_mode==False or target == 'AGG_MPC_plus_Liqu_Wealth_plusKY_plusMPC':     
    # # Calculate average within each MPC set
    # simulated_MPC_means = np.zeros((N_Lottery_Win_Sizes,k,N_Year_Sim))
    
    # for q in range(4):
    #     for y in range(N_Year_Sim):
    #         MPC_array = np.concatenate(MPC_Lists[k][q][y])
    #         simulated_MPC_means[k,q,y] = np.mean(MPC_array)
            
    # # Calculate aggregate MPC and MPCx
    # simulated_MPC_mean_add_Lottery_Bin = np.zeros((N_Year_Sim))
    # for y in range(N_Year_Sim):
    #     MPC_array = np.concatenate(MPC_List_Add_Lottery_Bin[y])
    #     simulated_MPC_mean_add_Lottery_Bin[y] = np.mean(MPC_array)
            
    
    # MPCs = namedtuple("MPCs", ["simulated_MPC_means_smoothed", "sorted_wealth_MPC", 
    #                            "quartile_cuts", "q1w", "q2w", "q3w", "q4w"])
    # return MPCs(simulated_MPC_means_smoothed, sorted_wealth_MPC, quartile_cuts,
    #             quartile1_weights, quartile2_weights, quartile3_weights, quartile4_weights) 

    print('Average PIs: ['+str(np.round(avgPI[0],3))+', '+str(np.round(avgPI[1],3))+', '+str(np.round(avgPI[2],3))+']\n' )

    sMPCs = simulated_MPC_means_smoothed
    print('Wealth by WQ = ['+str(round(wealthByWQ[0],4))+', '+str(round(wealthByWQ[1],4))+', '+str(round(wealthByWQ[2],4))+', '
              +str(round(wealthByWQ[3],4))+', '+str(round(wealthByWQ[4],4))+']')
    print('sMPCs = ['+str(round(sMPCs[0],3))+', '+str(round(sMPCs[1],3))+', '+str(round(sMPCs[2],3))+', '
                  +str(round(sMPCs[3],3))+', '+str(round(sMPCs[4],3))+']')
    print('betas by WQ = ['+str(round(betaByWQ[0],4))+', '+str(round(betaByWQ[1],4))+', '+str(round(betaByWQ[2],4))+', '
                  +str(round(betaByWQ[3],4))+', '+str(round(betaByWQ[4],4))+']')
    print('PIs by WQ = ['+str(round(PIbyWQ[0],4))+', '+str(round(PIbyWQ[1],4))+', '+str(round(PIbyWQ[2],4))+', '
                  +str(round(PIbyWQ[3],4))+', '+str(round(PIbyWQ[4],4))+']')
    print('Unemp frac by WQ = ['+str(round(UnempByWQ[0],4))+', '+str(round(UnempByWQ[1],4))+', '+str(round(UnempByWQ[2],4))+', '
                  +str(round(UnempByWQ[3],4))+', '+str(round(UnempByWQ[4],4))+']')
    print('Education by WQ = ['+str(round(educByWQ[0],2))+', '+str(round(educByWQ[1],2))+', '+str(round(educByWQ[2],2))+', '
                  +str(round(educByWQ[3],2))+', '+str(round(educByWQ[4],2))+']')
    print('Num in each WQ = ['+str(numWQ[0])+', '+str(numWQ[1])+', '+str(numWQ[2])+', '
                  +str(numWQ[3])+', '+str(numWQ[4])+']\n')
    
    return MPCbyWQ


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

baseline_commands = ['solve()', 'initialize_sim()', 'simulate()', 'save_state()', 'unpack_cFunc()']
multi_thread_commands_fake(TypeList, baseline_commands)


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
            ThisType.seed = n + 100
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
    # baseline_commands = ['simulate()', 'save_state()']
    baseline_commands = ['solve()', 'initialize_sim()', 'simulate()', 'save_state()', 'unpack_cFunc()']
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
        MPCsByWQsimple = calcMPCbyWealthQsimple(TypeListNew)
        MPCsByWQ = calcMPCbyWealthQ(TypeListNew, 5)

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
        print('Average annual MPCs by Wealth (incl. splurge) = ['+str(round(MPCsByWQsimple.MPCsA[0],3))+', '
                      +str(round(MPCsByWQsimple.MPCsA[1],3))+', '+str(round(MPCsByWQsimple.MPCsA[2],3))+', '
                      +str(round(MPCsByWQsimple.MPCsA[3],3))+', '+str(round(MPCsByWQsimple.MPCsA[4],3))+']\n')
        print('Average lottery-win-year MPCs by Wealth (simple, incl. splurge) = ['+str(round(MPCsByWQsimple.MPCsFYL[0],3))+', '
                      +str(round(MPCsByWQsimple.MPCsFYL[1],3))+', '+str(round(MPCsByWQsimple.MPCsFYL[2],3))+', '
                      +str(round(MPCsByWQsimple.MPCsFYL[3],3))+', '+str(round(MPCsByWQsimple.MPCsFYL[4],3))+']\n')
        print('Average lottery-win-year MPCs by Wealth (incl. splurge) = ['+str(round(MPCsByWQ[0],3))+', '
                      +str(round(MPCsByWQ[1],3))+', '+str(round(MPCsByWQ[2],3))+', '
                      +str(round(MPCsByWQ[3],3))+', '+str(round(MPCsByWQ[4],3))+']\n')

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
            
            resFile.write('\tAverage LW/PI-ratios: D = ' + mystr(Stats.avgLWPI[0]) + ' H = ' + mystr(Stats.avgLWPI[1]) \
                  + ' C = ' + mystr(Stats.avgLWPI[2])+'\n') 
            resFile.write('\tTotal LW/Total PI: D = ' + mystr(Stats.LWoPI[0]) + ' H = ' + mystr(Stats.LWoPI[1]) \
                  + ' C = ' + mystr(Stats.LWoPI[2])+'\n')
            
            resFile.write('\tAverage MPCs by Ed. (incl. splurge) = ['+str(round(MPCsByEd.MPCsA[0],3))+', '
                          +str(round(MPCsByEd.MPCsA[1],3))+', '+str(round(MPCsByEd.MPCsA[2],3))+', '
                          +str(round(MPCsByEd.MPCsA[3],3))+']\n')
            resFile.write('\tAverage annual MPCs by Wealth (incl. splurge) = ['+str(round(MPCsByWQsimple.MPCsA[0],3))+', '
                          +str(round(MPCsByWQsimple.MPCsA[1],3))+', '+str(round(MPCsByWQsimple.MPCsA[2],3))+', '
                          +str(round(MPCsByWQsimple.MPCsA[3],3))+', '+str(round(MPCsByWQsimple.MPCsA[4],3))+']\n')
            resFile.write('\tAverage lottery-win-year MPCs by Wealth (simple, incl. splurge) = ['+str(round(MPCsByWQsimple.MPCsFYL[0],3))+', '
                          +str(round(MPCsByWQsimple.MPCsFYL[1],3))+', '+str(round(MPCsByWQsimple.MPCsFYL[2],3))+', '
                          +str(round(MPCsByWQsimple.MPCsFYL[3],3))+', '+str(round(MPCsByWQsimple.MPCsFYL[4],3))+']\n')
            resFile.write('\tAverage lottery-win-year MPCs by Wealth (incl. splurge) = ['+str(round(MPCsByWQ[0],3))+', '
                          +str(round(MPCsByWQ[1],3))+', '+str(round(MPCsByWQ[2],3))+', '
                          +str(round(MPCsByWQ[3],3))+', '+str(round(MPCsByWQ[4],3))+']\n')
        
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
    # baseline_commands = ['simulate()', 'save_state()']
    baseline_commands = ['solve()', 'initialize_sim()', 'simulate()', 'save_state()']
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
estimateDiscFacs = True 
if estimateDiscFacs:
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
    
    for edType in [1]:
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
            mode = 'w'      # Overwrite old file...
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
calcAllResults = False
if calcAllResults:
    printResToFile  = True
    
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
    print('Loading estimates from ' + df_resFileStr + '\n')
    
    if printResToFile:
        with open(ar_resFileStr, 'w') as resFile: 
            print('Saving all model results in ' + ar_resFileStr + '\n')
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
        betasObjFuncEduc(beta, nabla, GICx, educ_type = edType, print_mode=True, print_file=printResToFile, filename=ar_resFileStr)
        checkDiscFacDistribution(beta, nabla, GICfactor, edType, print_mode=True, print_file=printResToFile, filename=ar_resFileStr)
        readStr = betFile.readline().strip()
    betFile.close()
    
    # Also calculate results for the whole population 
    betasObjFunc([myEstim[0][0], myEstim[1][0], myEstim[2][0]], \
                 [myEstim[0][1], myEstim[1][1], myEstim[2][1]], \
                 [myEstim[0][3], myEstim[1][3], myEstim[2][3]], \
                 target_option = 1, print_mode=True, print_file=printResToFile, filename=ar_resFileStr)
    


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
    if IncUnemp == 0.7 and IncUnempNoBenefits == 0.5 and Splurge != 0:
        # Baseline unemployment system: 
        betFile = open(res_dir+'/DiscFacEstim_CRRA_'+str(CRRA)+'_R_'+str(Rfree_base[0])+'.txt', 'r')
    elif IncUnemp == 0.7 and IncUnempNoBenefits == 0.5 and Splurge == 0:
        # Baseline unemployment system: 
        betFile = open(res_dir+'/DiscFacEstim_CRRA_'+str(CRRA)+'_R_'+str(Rfree_base[0])+'_Splurge0.txt', 'r')
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

    if IncUnemp == 0.7 and IncUnempNoBenefits == 0.5 and Splurge != 0:
        # Baseline unemployment system: 
        outFileStr = res_dir+'/DiscFacDistributions_CRRA_'+str(CRRA)+'_R_'+str(Rfree_base[0])+'.txt'
    elif IncUnemp == 0.7 and IncUnempNoBenefits == 0.5 and Splurge == 0:
        # Baseline unemployment system: 
        outFileStr = res_dir+'/DiscFacDistributions_CRRA_'+str(CRRA)+'_R_'+str(Rfree_base[0])+'_Splurge0.txt'
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

