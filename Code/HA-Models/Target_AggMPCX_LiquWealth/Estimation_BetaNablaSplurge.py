# Import python tools
import os
import numpy as np
import random
from copy import deepcopy
import pandas as pd

# Import needed tools from HARK
from HARK.distribution import Uniform
from HARK.utilities import get_percentiles, get_lorenz_shares, make_figs
from HARK.parallel import multi_thread_commands
from scipy.optimize import minimize
from HARK.ConsumptionSaving.ConsIndShockModel import KinkedRconsumerType
from SetupParamsCSTW import init_infinite


# for plotting
import matplotlib.pyplot as plt

# for output
cwd             = os.getcwd()
folders         = cwd.split(os.path.sep)
top_most_folder = folders[-1]
if top_most_folder == 'Target_AggMPCX_LiquWealth':
    Abs_Path = cwd
else:
    Abs_Path = cwd + '/Code/HA-Models/Target_AggMPCX_LiquWealth'

# Set key problem-specific parameters
TypeCount = 7       # Number of consumer types with heterogeneous discount factors
AdjFactor = 1.0     # Factor by which to scale all of MPCs in Table 9
T_kill    = 400     # Don't let agents live past this age (expressed in quarters)
drop_corner = True  # If True, ignore upper left corner when calculating distance

# Set standard HARK parameter values (from stickyE paper)
base_params = deepcopy(init_infinite)
base_params['LivPrb']       = [0.995]       #from stickyE paper
base_params['Rfree']        = 1.015         #from stickyE paper
base_params['Rsave']        = 1.015         #from stickyE paper
base_params['Rboro']        = 1.025         #from stickyE paper
base_params['PermShkStd']   = [0.001**0.5]  #from stickyE paper
base_params['TranShkStd']   = [0.132**0.5]  #from stickyE paper
base_params['T_age']        = 400           # Kill off agents if they manage to achieve T_kill working years
base_params['AgentCount']   = 5000          # Number of agents per instance of IndShockConsType
base_params['pLvlInitMean'] = np.log(23.72) 
base_params['T_sim']        = 800


Parametrization = 'NOR' 
if  Parametrization == 'NOR':    
    base_params['LivPrb']       = [1-1/160]     
    base_params['Rfree']        = 1.02**0.25
    base_params['Rsave']        = 1.02**0.25
    base_params['Rboro']        = 1.137**0.25
    base_params['pLvlInitMean'] = 0 
    base_params['UnempPrb']     = 0.044
    base_params['IncUnemp']     = 0.60
    base_params['PermShkStd']   = [0.001**0.5] #from Crawley,Moll,Tretvoll
    base_params['TranShkStd']   = [0.132**0.5]
    base_params['BoroCnstArt']  = 0 #-0.8
    base_params['PermGroFacAgg']= 1.01**0.25     
    base_params['CRRA']         = 2.0
    base_params['T_age']        = None
    
    
    

## TARGETS 
# Define the MPC targets from Fagereng et al Table 9; element i,j is lottery quartile i, deposit quartile j
MPC_target_base = np.array([[1.047, 0.745, 0.720, 0.490],
                            [0.762, 0.640, 0.559, 0.437],
                            [0.663, 0.546, 0.390, 0.386],
                            [0.354, 0.325, 0.242, 0.216]])
MPC_target = AdjFactor*MPC_target_base

# Define the agg MPCx targets from Fagereng et al. Figure 2; first element is same-year response, 2nd element, t+1 response etcc
Agg_MPCX_target = np.array([0.5056845, 0.1759051, 0.1035106, 0.0444222, 0.0336616])

# Define the four lottery sizes, in thousands of USD; these are eyeballed centers/averages
# 5th element is used as rep. lottery win to get at aggregate MPC / MPCX 
lottery_size_USD = np.array([1.625, 3.3741, 7.129, 40.0, 7.129])
lottery_size_NOK = lottery_size_USD * (10/1.1) #in Fagereng et al it is mention that 1000 NOK = 110 USD
lottery_size = lottery_size_NOK / (270/4); # divide by permanent income.
RandomLotteryWin = True #if True, then the 5th element will be replaced with a random lottery size win draw from the 1st to 4th element for each agent

# Liquid wealth target from US
lorenz_target = np.array([0.029, 0.354, 1.84, 7.42])/100
KY_target = 6.60




#%%  Objective function

def FagerengObjFunc(SplurgeEstimate,center,spread,verbose=False,estimation_mode=True,target='AGG_MPC',investigate=False):
    '''
    Objective function for the quick and dirty structural estimation to fit
    Fagereng, Holm, and Natvik's Table 9 results with a basic infinite horizon
    consumption-saving model (with permanent and transitory income shocks).

    Parameters
    ----------
    center : float
        Center of the uniform distribution of discount factors.
    spread : float
        Width of the uniform distribution of discount factors.
    verbose : bool
        When True, print to screen MPC table for these parameters.  When False,
        print (center, spread, distance).

    Returns
    -------
    distance : float
        Euclidean distance between simulated MPCs and (adjusted) Table 9 MPCs.
    '''
    
    # Give our consumer types the requested discount factor distribution
    for j in range(TypeCount):
        EstTypeList[j].reset_rng()
    random.seed(55)
    beta_set = Uniform(bot=center-spread, top=center+spread).discretize(TypeCount).atoms[0]
    
    # Taper off toward the growth impatience condition 
    GICmaxBeta = (1-base_params['LivPrb'][0]) + (base_params['PermGroFacAgg']**base_params['CRRA'])/base_params['Rfree']
    minBeta = 0.01
    for thedf in range(TypeCount):
        taper_threshold = 0.01
        if beta_set[thedf] > GICmaxBeta-taper_threshold:
            beta_set[thedf] = GICmaxBeta-taper_threshold + (np.arctan((beta_set[thedf] - GICmaxBeta + taper_threshold)/taper_threshold))*taper_threshold/np.pi*2
        elif beta_set[thedf] < minBeta:
            beta_set[thedf] = minBeta
    
      
    
    for j in range(TypeCount):
        EstTypeList[j].DiscFac = beta_set[j]

    # Solve and simulate all consumer types, then gather their wealth levels
    multi_thread_commands(EstTypeList,['solve()','initialize_sim()','simulate()', 'unpack_cFunc()'])
    WealthNow = np.concatenate([ThisType.state_now["aLvl"] for ThisType in EstTypeList])
    

    # Get wealth quartile cutoffs and distribute them to each consumer type
    quartile_cuts = get_percentiles(WealthNow,percentiles=[0.25,0.50,0.75])
    wealth_list = np.array([])
    for ThisType in EstTypeList:
        WealthQ = np.zeros(ThisType.AgentCount,dtype=int)
        for n in range(3):
            WealthQ[ThisType.state_now["aLvl"] > quartile_cuts[n]] += 1
        ThisType.WealthQ = WealthQ
        wealth_list = np.concatenate((wealth_list, ThisType.state_now["aLvl"] ))
            

         
    # Get lorenz curve
    order = np.argsort(WealthNow)
    WealthNow_sorted = WealthNow[order]
    Lorenz_Data = get_lorenz_shares(WealthNow_sorted,percentiles=np.arange(0.01,1.00,0.01),presorted=True) 
    Lorenz_Data = np.hstack((np.array(0.0),Lorenz_Data,np.array(1.0))) 
    Wealth_adj = WealthNow_sorted - WealthNow_sorted[0] # add lowest possible value to everyone
    Lorenz_Data_Adj = get_lorenz_shares(Wealth_adj,percentiles=np.arange(0.01,1.00,0.01),presorted=True) 
    Lorenz_Data_Adj = np.hstack((np.array(0.0),Lorenz_Data_Adj,np.array(1.0))) 
    lorenz_Model = np.array([Lorenz_Data_Adj[20], Lorenz_Data_Adj[40], Lorenz_Data_Adj[60], Lorenz_Data_Adj[80]])
    
    # Get K to Y
    CapAgg      = np.sum(WealthNow)
    TransNow    = np.concatenate([ThisType.shocks["TranShk"] for ThisType in EstTypeList])
    permNow     = np.concatenate([ThisType.state_now["pLvl"] for ThisType in EstTypeList]) 
    IncAgg      = np.sum(permNow*TransNow)
    KY_Model    = CapAgg/IncAgg
    
################## Can return K/Y here
    if target != "Liqu_Wealth_plusKY":

        N_Quarter_Sim = 20; # Needs to be dividable by four
        N_Year_Sim = int(N_Quarter_Sim/4)
        N_Lottery_Win_Sizes = 5 # 4 lottery size bin + 1 representative one for agg MPCX
    
        
        EmptyList = [[],[],[],[],[]]
        MPC_set_list = [deepcopy(EmptyList),deepcopy(EmptyList),deepcopy(EmptyList),deepcopy(EmptyList)]
        MPC_Lists    = [deepcopy(MPC_set_list),deepcopy(MPC_set_list),deepcopy(MPC_set_list),deepcopy(MPC_set_list),deepcopy(MPC_set_list)]    
        # additional list for 5th Lottery bin, just need for elements for four years
        MPC_List_Add_Lottery_Bin = EmptyList
        
        MPC_this_type = np.zeros((TypeCount, ThisType.AgentCount,N_Lottery_Win_Sizes,N_Year_Sim)) #Empty array, MPC for each Lottery size and agent
            
        for type_num, ThisType in zip(range(TypeCount), EstTypeList):
            
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
                

            for period in range(N_Quarter_Sim): #Simulate for 4 quarters as opposed to 1 year
                
                # Simulate forward for one quarter
                ThisType.simulate(1)           
                
                # capture base consumption which is consumption in absence of lottery win
                c_base[:,period] = ThisType.controls["cNrm"] 
                c_base_Lvl[:,period] = c_base[:,period] * ThisType.state_now["pLvl"]
                
            
                #for k in range(N_Lottery_Win_Sizes): # Loop through different lottery sizes, only this will produce values in simulated_MPC_means
                k = 4; # do not loop to save time 
                
                Llvl = lottery_size[k]*LotteryWin[:,period]  #Lottery win occurs only if LotteryWin = 1 for that agent
                
                if RandomLotteryWin and k == 5:
                    for i in range(ThisType.AgentCount):
                        Llvl[i] = lottery_size[random.randint(0,3)]*LotteryWin[i,period]
                        if LotteryWin[i,period]==1 and i==0:
                            print(Llvl[i])
                
                Lnrm = Llvl/ThisType.state_now["pLvl"]
                SplurgeNrm = SplurgeEstimate*Lnrm  #Splurge occurs only if LotteryWin = 1 for that agent
        
            
                R_kink = np.zeros((ThisType.AgentCount))       
                for i in range(ThisType.AgentCount):
                    if a_actu[i,period-1,k] < 0:
                        R_kink[i] = base_params['Rboro']
                    else:
                        R_kink[i] = base_params['Rsave']  
                
                
                if period == 0:
                    m_adj = ThisType.state_now["mNrm"]  + Lnrm - SplurgeNrm
                    c_actu[:,period,k] = ThisType.cFunc[0](m_adj) + SplurgeNrm
                    c_actu_Lvl[:,period,k] = c_actu[:,period,k] * ThisType.state_now["pLvl"]
                    a_actu[:,period,k] = ThisType.state_now["mNrm"] + Lnrm - c_actu[:,period,k] #save for next periods
                else:  
                    T_hist[:,period] = ThisType.shocks["TranShk"] 
                    P_hist[:,period] = ThisType.shocks["PermShk"]
                    for i_agent in range(ThisType.AgentCount):
                        if ThisType.shocks["TranShk"][i_agent] == 1.0: # indicator of death
                            a_actu[i_agent,period-1,k] = np.exp(base_params['aNrmInitMean'])
                    m_adj = a_actu[:,period-1,k]*R_kink/ThisType.shocks["PermShk"] + ThisType.shocks["TranShk"] + Lnrm - SplurgeNrm #continue with resources from last period
                    c_actu[:,period,k] = ThisType.cFunc[0](m_adj) + SplurgeNrm
                    c_actu_Lvl[:,period,k] = c_actu[:,period,k] * ThisType.state_now["pLvl"]
                    a_actu[:,period,k] = a_actu[:,period-1,k]*R_kink/ThisType.shocks["PermShk"] + ThisType.shocks["TranShk"] + Lnrm - c_actu[:,period,k] 
                    
                if period%4 + 1 == 4: #if we are in the 4th quarter of a year
                    year = int((period+1)/4)
                    c_actu_Lvl_year = c_actu_Lvl[:,(year-1)*4:year*4,k]
                    c_base_Lvl_year = c_base_Lvl[:,(year-1)*4:year*4]
                    MPC_this_type[type_num,:,k,year-1] = (np.sum(c_actu_Lvl_year,axis=1) - np.sum(c_base_Lvl_year,axis=1))/(lottery_size[k])
                        
            
            # Sort the MPCs into the proper MPC sets
            for q in range(4):
                these = ThisType.WealthQ == q
                for k in range(N_Lottery_Win_Sizes):
                    for y in range(N_Year_Sim):
                        MPC_Lists[k][q][y].append(MPC_this_type[type_num,these,k,y])
                        
            # sort MPCs for addtional Lottery bin
            for y in range(N_Year_Sim):
                MPC_List_Add_Lottery_Bin[y].append(MPC_this_type[type_num,:,4,y])

                
        #Create a list of wealth and MPCs
        MPC_list = np.array([])
        for type_num, ThisType in zip(range(TypeCount), EstTypeList):
            MPC_list = np.concatenate((MPC_list, MPC_this_type[type_num, :, 4, 0] ))
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
        simulated_MPC_means_smoothed = np.zeros(4)
        simulated_MPC_means_smoothed[0] = np.average(sorted_wealth_MPC[1],weights=quartile1_weights)
        simulated_MPC_means_smoothed[1] = np.average(sorted_wealth_MPC[1],weights=quartile2_weights)
        simulated_MPC_means_smoothed[2] = np.average(sorted_wealth_MPC[1],weights=quartile3_weights)
        simulated_MPC_means_smoothed[3] = np.average(sorted_wealth_MPC[1],weights=quartile4_weights)
        
        #if estimation_mode==False or target == 'AGG_MPC_plus_Liqu_Wealth_plusKY_plusMPC':     
        # Calculate average within each MPC set
        simulated_MPC_means = np.zeros((N_Lottery_Win_Sizes,4,N_Year_Sim))
        for k in range(N_Lottery_Win_Sizes):
            for q in range(4):
                for y in range(N_Year_Sim):
                    MPC_array = np.concatenate(MPC_Lists[k][q][y])
                    simulated_MPC_means[k,q,y] = np.mean(MPC_array)
                    
        # Calculate aggregate MPC and MPCx
        simulated_MPC_mean_add_Lottery_Bin = np.zeros((N_Year_Sim))
        for y in range(N_Year_Sim):
            MPC_array = np.concatenate(MPC_List_Add_Lottery_Bin[y])
            simulated_MPC_mean_add_Lottery_Bin[y] = np.mean(MPC_array)
                
        # Calculate Euclidean distance between simulated MPC averages and Table 9 targets
        
       
        # MPC for representative lottery win (k=4), which corresponds to third row in MPC_target
        diff_MPC = simulated_MPC_means_smoothed - MPC_target[2,:] 
        distance_MPC = 0.1*np.sum((diff_MPC)**2) 
          
        diff_Agg_MPC = simulated_MPC_mean_add_Lottery_Bin - Agg_MPCX_target
        distance_Agg_MPC = np.sum((diff_Agg_MPC)**2)     
        distance_Agg_MPC_24 = np.sum((diff_Agg_MPC[2:4])**2)
        distance_Agg_MPC_01 = np.sum((diff_Agg_MPC[0:1])**2)
    else:
        distance_MPC = 0
        diff_Agg_MPC = 0
        distance_Agg_MPC = 0
        distance_Agg_MPC_24 = 0
        distance_Agg_MPC_01 = 0
        simulated_MPC_means = 0
        simulated_MPC_mean_add_Lottery_Bin = 0
        c_actu_Lvl = 0
        c_base_Lvl = 0
        LotteryWin = 0
        
        
        
    diff_lorenz = lorenz_Model - lorenz_target
    distance_lorenz = np.sum((diff_lorenz)**2)
    
    distance_KY = 1.0*((KY_target - KY_Model)/KY_target)**2 
    

    if target == 'MPC':
        distance = distance_MPC + distance_Agg_MPC
    elif target == 'AGG_MPC':
        distance = distance_Agg_MPC
    elif target == 'AGG_MPC_234':
        distance = distance_Agg_MPC_24
    elif target == 'MPC_plus_AGG_MPC_1':
        distance = distance_MPC + distance_Agg_MPC_01
    elif target == 'AGG_MPC_plus_Liqu_Wealth':
        distance = distance_Agg_MPC + distance_lorenz
    elif target == 'AGG_MPC_plus_Liqu_Wealth_plusKY':
        distance = distance_Agg_MPC + distance_lorenz + distance_KY
    elif target == 'AGG_MPC_plus_Liqu_Wealth_plusKY_plusMPC':
        distance = distance_MPC + distance_Agg_MPC + distance_lorenz + distance_KY
    elif target == "Liqu_Wealth_plusKY":
        distance = distance_lorenz + distance_KY
    elif target == "test":
        distance = distance_MPC
        
    if estimation_mode==False:   
        print(distance_Agg_MPC,distance_lorenz,distance_KY)
        
    if verbose:
        print(simulated_MPC_means)
        print(simulated_MPC_means_smoothed)
    else:
        print (SplurgeEstimate, center, spread, distance)
        
    if investigate:
        print("distance_MPC", distance_MPC) 
        print("distance_Agg_MPC", distance_Agg_MPC)
        print("distance_lorenz", distance_lorenz)
        print("distance_KY", distance_KY)
        print (beta_set)
        
    if investigate:
        for j in range(TypeCount):
            CapAggj = np.sum(EstTypeList[j].state_now["aLvl"])
            permNowj = EstTypeList[j].state_now["pLvl"] 
            TransNowj = EstTypeList[j].shocks["TranShk"]
            KY_Modelj = CapAggj/np.sum(permNowj*TransNowj)
            print("K/Y for DF group ", str(j), ": ",  KY_Modelj)
        print("K/Y for whole pop : ",  KY_Model)
        print("")
        
    if estimation_mode:
        return distance
    else:
        Output = dict()
        Output['distance'] = distance
        Output['distance_MPC'] = distance_MPC
        Output['distance_Agg_MPC'] = distance_Agg_MPC
        Output['distance_lorenz'] = distance_lorenz
        Output['distance_KY'] = distance_KY
        Output['simulated_MPC_means_smoothed'] = simulated_MPC_means_smoothed
        Output['simulated_MPC_mean_add_Lottery_Bin'] = simulated_MPC_mean_add_Lottery_Bin
        Output['c_actu_Lvl'] = c_actu_Lvl
        Output['c_base_Lvl'] = c_base_Lvl
        Output['LotteryWin'] = LotteryWin
        Output['Lorenz_Data'] = Lorenz_Data
        Output['Lorenz_Data_Adj'] = Lorenz_Data_Adj
        Output['KY_Model'] = KY_Model
        return Output


def save_betanabla_res_txt(filename,res):
    with open(Abs_Path+filename, 'w') as f:
        str1 = repr(res)
        f.write(str1)
        f.close
        
def load_betanabla_res_txt(filename):
    f = open(Abs_Path+filename, 'r')
    if f.mode=='r':
        contents= f.read()
    dictload= eval(contents)
    splurge = dictload['splurge']
    beta    = dictload['beta']
    nabla   = dictload['nabla']
    return [splurge,beta,nabla]


def find_Opt(target='', startpoint = [0.27,0.96,0.03], check_maximum = False):
    
    bounds = [(0.0,0.9),(0.7,1.1),(0.0,0.4)]
        
    f_temp = lambda x : FagerengObjFunc(x[0],x[1],x[2],target=target)
    #opt = minimizeNelderMead(f_temp, startpoint2, verbose=1, xtol=0.001, ftol=0.001)
    opt_output = minimize(f_temp, startpoint,method="Powell", bounds =bounds)
    opt = opt_output.x
    obs = opt_output.fun
    beta = opt[1]
    nabla = opt[2]
    print('Finished estimating')
    print('Optimal splurge is ' + str(opt[0]) )
    print('Optimal (beta,nabla) is ' + str(beta) + ',' + str(nabla))
    
    if check_maximum:
        check_start = [opt[0],opt[2]]
        check_obs = [0.0, 0.0]
        for i,deviation in zip(range(2), [-0.0001, 0.0001]):
            f_temp = lambda y : FagerengObjFunc(y[0],opt[1]+deviation,y[1],target=target)
            check_opt = minimize(f_temp, check_start,method="Powell", bounds = [(0.0,0.9),(0.0,0.4)])
            check_obs[i] = check_opt.fun
        print("Objective around minimum:")
        print([check_obs[0], obs, check_obs[1]])
        if check_obs[0]<obs or check_obs[1] < obs :
            print("Didn't find minimum - check what is going on")
            return {'splurge' : opt[0], 'beta' : beta, 'nabla': nabla, 'Error': 'Not a maximum'}
        else:
            print("Local minimum check passed")
    
    return {'splurge' : opt[0], 'beta' : beta, 'nabla': nabla}

def find_Opt_splurge0(target='', startpoint = [0.96,0.03], check_maximum = False):
        

    f_temp = lambda x : FagerengObjFunc(0,x[0],x[1], target=target)
    opt_output = minimize(f_temp, startpoint,method="Powell", bounds = [(0.7,1.01),(0.0,0.4)])
    opt = opt_output.x
    obs = opt_output.fun
    beta = opt[0]
    nabla = opt[1]
    print('Optimal (beta,nabla) is ' + str(beta) + ',' + str(nabla)) 
    
    if check_maximum:
        check_start = [opt[1]]
        check_obs = [0.0, 0.0]
        for i,deviation in zip(range(2), [-0.0001, 0.0001]):
            f_temp = lambda y : FagerengObjFunc(0,opt[0]+deviation,y[0],target=target)
            check_opt = minimize(f_temp, check_start,method="L-BFGS-B", bounds = [(0.0,0.4)])
            check_obs[i] = check_opt.fun
            print([opt[0]+deviation,check_opt.x,check_opt.fun])
        print("Objective around minimum:")
        print([check_obs[0], obs, check_obs[1]])
        if check_obs[0]<obs or check_obs[1] < obs :
            print("Didn't find minimum - check what is going on")
            return {'splurge' : 0, 'beta' : beta, 'nabla': nabla, 'Error': 'Not a maximum'}
        else:
            print("Local minimum check passed")
    
    return {'splurge' : 0, 'beta' : beta, 'nabla': nabla}


# Make several consumer types to be used during estimation
BaseType = KinkedRconsumerType(**base_params)
EstTypeList = []
for j in range(TypeCount):
    EstTypeList.append(deepcopy(BaseType))
    EstTypeList[-1].seed = j




#%% Estimation
Run_estimation      = True
Run_SplurgeZero     = True

RunLoopofStarpoints = True 
# Running the Loop of startpoints shows that that the algorithm converges to the same
# solution independent of startpoint and thus strongly suggests that the global minimum was found

    
if Run_estimation:
    print("RUNNING RUN KY AND INIT MPC ESTIMATION")
    target = 'AGG_MPC_plus_Liqu_Wealth_plusKY_plusMPC'
    
    if RunLoopofStarpoints:
        # Loop over starting points with splurge in (0.10,0.3,0.5), beta in (0.85, 0.925, 1) and nabla in (0.05, 0.10)
        startpoints = [ [0.10, 0.85, 0.05],#
                        [0.10, 0.85, 0.10],
                        [0.10, 0.925, 0.05],#
                        [0.10, 0.925, 0.10],
                        [0.10, 1, 0.05],
                        [0.10, 1, 0.10],
                        [0.30, 0.85, 0.05],#
                        [0.30, 0.85, 0.10],
                        [0.30, 0.925, 0.05],#
                        [0.30, 0.925, 0.10],
                        [0.30, 1, 0.05],
                        [0.30, 1, 0.10],
                        [0.50, 0.85, 0.05],#
                        [0.50, 0.85, 0.10],
                        [0.50, 0.925, 0.05],
                        [0.50, 0.925, 0.10],
                        [0.50, 1, 0.05],
                        [0.50, 1, 0.10]]
    else:
        startpoints = [ [0.24906992981618237, 0.9675474591463475, 0.05782806961924406] ]
    
    for i,startpoint in enumerate(startpoints):
        print("Startpoint run no. ",i+1)
        print("Startpoint used: ", startpoint)

        
        if RunLoopofStarpoints:
            filename = '\Result_AllTarget_startpoint'+str(i+1)+'.txt'
        else:
            filename = '\Result_AllTarget.txt'  
        res = find_Opt(target=target, startpoint=startpoint)   
        save_betanabla_res_txt(filename,res)
        

if Run_SplurgeZero:
    print("RUNNING RUN KY AND INIT MPC ESTIMATION, SPLURGE = 0")
    target = 'AGG_MPC_plus_Liqu_Wealth_plusKY_plusMPC'
    
    if RunLoopofStarpoints:
        # Loop over starting points with beta in (0.85, 0.925, 1) and nabla in (0.05, 0.10, 0.20)
        startpoints = [ [0.00, 0.85, 0.05],
                        [0.00, 0.85, 0.10],
                        [0.00, 0.85, 0.20],
                        [0.00, 0.925, 0.05],
                        [0.00, 0.925, 0.10],
                        [0.00, 0.925, 0.20],
                        [0.00, 1, 0.05],
                        [0.00, 1, 0.10],
                        [0.00, 1, 0.20]]
    else:
        startpoints = [ [0, 0.9215203827041509, 0.11625829523973752] ]
        
    for i,startpoint in enumerate(startpoints):
        print("Startpoint run no. ",i+1)
        print("Startpoint used: ", startpoint)
    
        
        if RunLoopofStarpoints:
            filename = '\Result_AllTarget_Splurge0_startpoint'+str(i+1)+'.txt'  
        else:
            filename = '\Result_AllTarget_Splurge0.txt'  
        res = find_Opt_splurge0(target=target, startpoint=startpoint[1:3])  
        save_betanabla_res_txt(filename,res)

#%% Output results for paper

Plot_Output = False
if Plot_Output:
    target = 'AGG_MPC_plus_Liqu_Wealth_plusKY_plusMPC'
    # Splurge=0 solution 
    [splurge,beta,nabla] = load_betanabla_res_txt('\Result_AllTarget_Splurge0.txt')
    Splurge0_Sol=FagerengObjFunc(splurge,beta,nabla,estimation_mode=False,target=target)
    
    # Splurge>0 solution
    [splurge,beta,nabla] = load_betanabla_res_txt('\Result_AllTarget.txt')
    SplurgeNot0_Sol=FagerengObjFunc(splurge,beta,nabla,estimation_mode=False,target=target)
    
    # Plot Lorentz curve
    plt.figure()
    LorenzAxis = np.arange(101,dtype=float)
    plt.plot(LorenzAxis,SplurgeNot0_Sol['Lorenz_Data_Adj'] ,'b-',linewidth=2)
    plt.plot(LorenzAxis,Splurge0_Sol['Lorenz_Data_Adj']    ,'r:',linewidth=2)
    plt.scatter(np.array([20,40,60,80,100]),np.hstack([lorenz_target,1]),c='black', marker='o')
    plt.xlabel('Liquid wealth percentile',fontsize=12)
    plt.ylabel('Cumulative liquid wealth share',fontsize=12)
    plt.legend(['Model, splurge $\geq$ 0','Model, splurge = 0','Data'])
    make_figs('LiquWealth_Distribution_comparison', True , False, target_dir=Abs_Path+'/Figures/')
    plt.show()  
    
    # Plot Agg MPCx
    plt.figure()
    xAxis = np.arange(0,5)
    plt.plot(xAxis,SplurgeNot0_Sol['simulated_MPC_mean_add_Lottery_Bin'] ,'b-',linewidth=2)
    plt.plot(xAxis,Splurge0_Sol['simulated_MPC_mean_add_Lottery_Bin']    ,'r:',linewidth=2)
    plt.scatter(xAxis,Agg_MPCX_target,c='black', marker='o')
    plt.legend(['Model, splurge $\geq$ 0','Model, splurge = 0','Fagereng, Holm and Natvik (2021)'])
    plt.xticks(np.arange(min(xAxis), max(xAxis)+1, 1.0))
    plt.xlabel('year')
    plt.ylabel('% of lottery win spent')
    make_figs('AggMPC_LotteryWin_comparison', True , False, target_dir=Abs_Path+'/Figures/')
    plt.show()  
    
    # Table initial MPCs along wealth q
    
    def mystr2(number):
        if not np.isnan(number):
            out = "{:.2f}".format(number)
        else:
            out = ''
        return out
    
        
    output  ="\\begin{tabular}{@{}lcccccc@{}} \n"
    output +="\\toprule \n"
    output +="                  & \multicolumn{5}{c}{MPC} &   \\\\   \n"
    output +="                  &  1st WQ  & 2nd WQ  & 3rd WQ & 4th WQ  & Agg  &  K/Y  \\\\  \\midrule \n"
    output +="Splurge $\geq$ 0 &"+mystr2(SplurgeNot0_Sol['simulated_MPC_means_smoothed'][3])      + " & "+ mystr2(SplurgeNot0_Sol['simulated_MPC_means_smoothed'][2])+ " & "+  \
                                mystr2(SplurgeNot0_Sol['simulated_MPC_means_smoothed'][1])      + " & "+ mystr2(SplurgeNot0_Sol['simulated_MPC_means_smoothed'][0]) + " & "+  \
                                mystr2(SplurgeNot0_Sol['simulated_MPC_mean_add_Lottery_Bin'][0])+ " & "+ mystr2(SplurgeNot0_Sol['KY_Model'])  + " \\\\ \n"
    output +="Splurge = 0 &"+   mystr2(Splurge0_Sol['simulated_MPC_means_smoothed'][3])         + " & "+ mystr2(Splurge0_Sol['simulated_MPC_means_smoothed'][2])+ " & "+  \
                                mystr2(Splurge0_Sol['simulated_MPC_means_smoothed'][1])         + " & "+ mystr2(Splurge0_Sol['simulated_MPC_means_smoothed'][0]) + " & "+  \
                                mystr2(Splurge0_Sol['simulated_MPC_mean_add_Lottery_Bin'][0])   + " & "+ mystr2(Splurge0_Sol['KY_Model'])  + " \\\\ \n"
    output +="Data &"+          mystr2(MPC_target[2,3])                                         + " & "+ mystr2(MPC_target[2,2])+ " & "+  \
                                mystr2(MPC_target[2,1])                                         + " & "+ mystr2(MPC_target[2,0]) + " & "+  \
                                mystr2(Agg_MPCX_target[0])                                      + " & "+ mystr2(KY_target)  + " \\\\ \n"
    output +="\\end{tabular}  \n"
    
    
    with open(Abs_Path+'/Figures/Comparison_Splurge_Table.tex','w') as f:
        f.write(output)
        f.close()   
    
    
    
    Output_to_Excel = True
    if Output_to_Excel:
        x = np.vstack(( xAxis, SplurgeNot0_Sol['simulated_MPC_mean_add_Lottery_Bin'], Splurge0_Sol['simulated_MPC_mean_add_Lottery_Bin'] , Agg_MPCX_target) )
        df = pd.DataFrame(x.T,columns=['Year','Model, splurge > 0','Model, splurge = 0','Fagereng, Holm and Natvik (2021)'])
        df.to_excel(Abs_Path+'/Data_AggMPC_LotteryWin.xlsx')
        
        x = np.vstack(( LorenzAxis, SplurgeNot0_Sol['Lorenz_Data_Adj'], Splurge0_Sol['Lorenz_Data_Adj'] ) )
        df = pd.DataFrame(x.T,columns=['Percentile','Model, splurge > 0','Model, splurge = 0'])
        df.to_excel(Abs_Path+'/LiquWealth_Distribution_a.xlsx')
        
        x = np.vstack(( np.array([20,40,60,80,100]), np.hstack([lorenz_target,1]) ) )
        df = pd.DataFrame(x.T,columns=['Percentile','Data'])
        df.to_excel(Abs_Path+'/LiquWealth_Distribution_b.xlsx')
    
    

#%%
Run_other_CRRA_values = True
if Run_other_CRRA_values:
    CRRA_values = [1,3]
    
    RunLoopofStarpoints = True 
    startpoints = [ [0.10, 0.85, 0.10],
                    [0.10, 0.95, 0.15],
                    [0.30, 0.85, 0.10],
                    [0.30, 0.95, 0.15] ]
    
    for el in range(0,len(CRRA_values)):
        print('Running CRRA = ', CRRA_values[el])
        base_params['CRRA'] = CRRA_values[el]
    
        # Make several consumer types to be used during estimation
        del EstTypeList
        BaseTypeCRRA = KinkedRconsumerType(**base_params)
        EstTypeList = []
        for j in range(TypeCount):
            EstTypeList.append(deepcopy(BaseTypeCRRA))
            EstTypeList[-1].seed = j
    
    
    
        if RunLoopofStarpoints:
            for i,startpoint in enumerate(startpoints):
                print("Startpoint run no. ",i+1)
                print("Startpoint used: ", startpoint)
         
                target = 'AGG_MPC_plus_Liqu_Wealth_plusKY_plusMPC'
                filename = '\Result_AllTarget_CRRA_'+str(CRRA_values[el])+'_startpoint'+str(i)+'.txt'  
                res = find_Opt(target=target, startpoint=startpoint)
                save_betanabla_res_txt(filename,res)
        else:
            if CRRA_values[el] == 1:
                startpoint  = [0.14936532325901916, 0.9768205536148804, 0.09086039551142643]
            else:
                startpoint  = [0.2660514984112632, 0.9549940464615455, 0.06597517675173052]    
            
            target = 'AGG_MPC_plus_Liqu_Wealth_plusKY_plusMPC'
            filename = '\Result_AllTarget_CRRA_'+str(CRRA_values[el])+'.txt'  
            res = find_Opt(target=target, startpoint=startpoint)
            save_betanabla_res_txt(filename,res)


Plot_other_CRRA_values = False
if Plot_other_CRRA_values:
    target = 'AGG_MPC_plus_Liqu_Wealth_plusKY_plusMPC'
    # CRRA=1 
    del EstTypeList
    base_params['CRRA'] = 1
    BaseType = KinkedRconsumerType(**base_params)
    EstTypeList = []
    for j in range(TypeCount):
        EstTypeList.append(deepcopy(BaseType))
        EstTypeList[-1].seed = j
    [splurge,beta,nabla] = load_betanabla_res_txt('\Result_AllTarget_CRRA_1.txt')
    CRRA1=FagerengObjFunc(splurge,beta,nabla,estimation_mode=False,target=target)
    
    # CRRA=2
    del EstTypeList
    base_params['CRRA'] = 3
    BaseType = KinkedRconsumerType(**base_params)
    EstTypeList = []
    for j in range(TypeCount):
        EstTypeList.append(deepcopy(BaseType))
        EstTypeList[-1].seed = j
    [splurge,beta,nabla] = load_betanabla_res_txt('\Result_AllTarget_CRRA_3.txt')
    CRRA3=FagerengObjFunc(splurge,beta,nabla,estimation_mode=False,target=target)
    
    # Plot Lorentz curve
    plt.figure()
    LorenzAxis = np.arange(101,dtype=float)
    plt.plot(LorenzAxis,CRRA1['Lorenz_Data_Adj'] ,'b-',linewidth=2)
    plt.plot(LorenzAxis,CRRA3['Lorenz_Data_Adj']    ,'r:',linewidth=2)
    plt.scatter(np.array([20,40,60,80,100]),np.hstack([lorenz_target,1]),c='black', marker='o')
    plt.xlabel('Liquid wealth percentile',fontsize=12)
    plt.ylabel('Cumulative liquid wealth share',fontsize=12)
    plt.legend(['CRRA=1','CRRA = 3','Data'])
    make_figs('LiquWealth_Distribution_comparison_CRRA', True , False, target_dir=Abs_Path+'/Figures/')
    plt.show()  
    
    # Plot Agg MPCx
    plt.figure()
    xAxis = np.arange(0,5)
    plt.plot(xAxis,CRRA1['simulated_MPC_mean_add_Lottery_Bin'] ,'b-',linewidth=2)
    plt.plot(xAxis,CRRA3['simulated_MPC_mean_add_Lottery_Bin']    ,'r:',linewidth=2)
    plt.scatter(xAxis,Agg_MPCX_target,c='black', marker='o')
    plt.legend(['CRRA=1','CRRA = 3','Fagereng, Holm and Natvik (2021)'])
    plt.xticks(np.arange(min(xAxis), max(xAxis)+1, 1.0))
    plt.xlabel('year')
    plt.ylabel('% of lottery win spent')
    make_figs('AggMPC_LotteryWin_comparison_CRRA', True , False, target_dir=Abs_Path+'/Figures/')
    plt.show()  
    
    # Table initial MPCs along wealth q
    
    def mystr2(number):
        if not np.isnan(number):
            out = "{:.2f}".format(number)
        else:
            out = ''
        return out
    
        
    output  ="\\begin{tabular}{@{}lcccccc@{}} \n"
    output +="\\toprule \n"
    output +="                  & \multicolumn{5}{c}{MPC} &   \\\\   \n"
    output +="                  &  1st WQ  & 2nd WQ  & 3rd WQ & 4th WQ  & Agg  &  K/Y  \\\\  \\midrule \n"
    output +="CRRA=1 &"+mystr2(CRRA1['simulated_MPC_means_smoothed'][3])      + " & "+ mystr2(CRRA1['simulated_MPC_means_smoothed'][2])+ " & "+  \
                                mystr2(CRRA1['simulated_MPC_means_smoothed'][1])      + " & "+ mystr2(CRRA1['simulated_MPC_means_smoothed'][0]) + " & "+  \
                                mystr2(CRRA1['simulated_MPC_mean_add_Lottery_Bin'][0])+ " & "+ mystr2(CRRA1['KY_Model'])  + " \\\\ \n"
    output +="CRRA=3 &"+   mystr2(CRRA3['simulated_MPC_means_smoothed'][3])         + " & "+ mystr2(CRRA3['simulated_MPC_means_smoothed'][2])+ " & "+  \
                                mystr2(CRRA3['simulated_MPC_means_smoothed'][1])         + " & "+ mystr2(CRRA3['simulated_MPC_means_smoothed'][0]) + " & "+  \
                                mystr2(CRRA3['simulated_MPC_mean_add_Lottery_Bin'][0])   + " & "+ mystr2(CRRA3['KY_Model'])  + " \\\\ \n"
    output +="Data &"+          mystr2(MPC_target[2,3])                                         + " & "+ mystr2(MPC_target[2,2])+ " & "+  \
                                mystr2(MPC_target[2,1])                                         + " & "+ mystr2(MPC_target[2,0]) + " & "+  \
                                mystr2(Agg_MPCX_target[0])                                      + " & "+ mystr2(KY_target)  + " \\\\ \n"
    output +="\\end{tabular}  \n"
    
    
    with open(Abs_Path+'/Figures/Comparison_CRRA_Table.tex','w') as f:
        f.write(output)
        f.close()   
    


    
 
    
    



    #%% For testing purposes

Run_3D_Plot         = False
Run_Investigation   = False


if Run_Investigation:
    for this_beta in np.linspace(0.925,0.932,10):
        FagerengObjFunc(0,this_beta ,0.086, target='AGG_MPC_plus_Liqu_Wealth_plusKY_plusMPC',investigate=True)
        

if Run_3D_Plot:
    # Define the function to be evaluated
    def my_function(x,y):
        return FagerengObjFunc(0,x,y, target='AGG_MPC_plus_Liqu_Wealth_plusKY_plusMPC')
      
          
    x_range = np.linspace(0.925, 0.95, 10)
    y_range = np.linspace(0.006, 0.01, 10)
     
    # Create empty arrays to store the results
    z_values = np.zeros((len(x_range), len(y_range)))
     
    # Evaluate the function using loops
    for i, x in enumerate(x_range):
        for j, y in enumerate(y_range):
            if (x + y > 1.05) or  (x + y < 0.98):
                z_values[i, j] = None
            else:
                z_values[i, j] = my_function(x, y)
                
          
                
    # Create a 3D plot
    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')
     
    # Create meshgrid for plotting
    x_grid, y_grid = np.meshgrid(x_range, y_range)
     
    # Plot the surface
    surf = ax.plot_surface(x_grid, y_grid, z_values.T, cmap='viridis')
     
    # Add labels and title
    ax.set_xlabel('X-axis')
    ax.set_ylabel('Y-axis')
    ax.set_zlabel('Z-axis')
    ax.set_title('Function Evaluation over 2D Grid (using loops)')
     
    # Add color bar
    fig.colorbar(surf, ax=ax, shrink=0.5, aspect=10)
     
    # Show the plot
    plt.show()




    




    