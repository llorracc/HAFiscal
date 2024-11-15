import os
import sys
import numpy as np
import matplotlib.pyplot as plt  
from OtherFunctions import loadPickle
from HARK.utilities import make_figs


# for output
cwd             = os.getcwd()
folders         = cwd.split(os.path.sep)
top_most_folder = folders[-1]
if top_most_folder == 'FromPandemicCode':
    Abs_Path = cwd
else:
    Abs_Path = cwd + '/Code/HA-Models/FromPandemicCode'
    os.chdir(Abs_Path)

sys.path.append(Abs_Path)


base_results_full                            = loadPickle('base_results_full',Abs_Path+'/Figures/CRRA2/',locals())
base_results_full_splurge0                    = loadPickle('base_results_full',Abs_Path+'/Figures/Splurge0/',locals())




#%%

def calc_C_I_paths_for_Unemp(result_var):

    # Extract the relevant arrays from base_results_full  
    Mrkv_hist           = result_var['Mrkv_hist']  
    cLvl_all_splurge    = result_var['cLvl_all_splurge']  
    pLvl_all            = result_var['pLvl_all']  
    TranShk_all         = result_var['TranShk_all']  
    Wealth_all          = result_var['aNrm_all'] 
      
    # Calculate income level  
    income_all = pLvl_all * TranShk_all  
      
    # Initialize lists to store consumption and income levels for each period relative to state 3 entry  
    consumption_levels = [[] for _ in range(6)]  
    income_levels = [[] for _ in range(6)]  
    wealth_levels = [[] for _ in range(6)]  
      
    # Loop through each agent  
    for agent in range(Mrkv_hist.shape[1]):  
        # Find all times the agent enters state 3  
        instances_enter_state3 = np.where((Mrkv_hist[:, agent] == 3) &   
                                 (np.roll(Mrkv_hist[:, agent], 1) != 3))[0]  
          
        for instance_enter_state3 in instances_enter_state3:  
            # Check if the agent stays in state 3 for at least 3 quarters  
            if instance_enter_state3 + 2 < Mrkv_hist.shape[0] and np.all(Mrkv_hist[instance_enter_state3:instance_enter_state3 + 3, agent] == 3):  
                # Define the window from 3 periods before to 2 periods after entering state 3  
                start_time = max(0, instance_enter_state3 - 3)  
                end_time = min(Mrkv_hist.shape[0], instance_enter_state3 + 3)  
                  
                # Normalize consumption and income levels to 1 for the period 3 before entering state 3  
                normalization_period = instance_enter_state3 - 3  
                if normalization_period >= 0:  
                    normalization_factor_consumption = pLvl_all[normalization_period, agent]  
                    normalization_factor_income = pLvl_all[normalization_period, agent]  
                      
                    for i in range(start_time, end_time):  
                        period_index = i - instance_enter_state3 + 3  
                        normalized_consumption = cLvl_all_splurge[i, agent] / normalization_factor_consumption  
                        normalized_income = income_all[i, agent] / normalization_factor_income  
                        normalized_wealth = Wealth_all[i, agent] / normalization_factor_income <0.005  
                        consumption_levels[period_index].append(normalized_consumption)  
                        income_levels[period_index].append(normalized_income)  
                        wealth_levels[period_index].append(normalized_wealth)  
      
    # Calculate the average consumption and income levels for each period  
    avg_consumption_levels = [np.mean(period) if period else np.nan for period in consumption_levels]  
    avg_income_levels = [np.mean(period) if period else np.nan for period in income_levels]  
    avg_wealth_levels = [np.mean(period) if period else np.nan for period in wealth_levels]  
    
    return [avg_consumption_levels,avg_income_levels,avg_wealth_levels]
  
    
[avg_consumption_levels,avg_income_levels,avg_wealth_levels] = calc_C_I_paths_for_Unemp(base_results_full)  
[avg_consumption_levels_splurge0,avg_income_levels_splurge0,avg_wealth_levels_splurge0] = calc_C_I_paths_for_Unemp(base_results_full_splurge0) 


# Plot the results  
plt.figure(figsize=(7, 6))    
plt.plot(range(0, 6), avg_consumption_levels, label='Consumption', color='blue', linestyle='-')  
plt.plot(range(0, 6), avg_consumption_levels_splurge0, label='Consumption, splurge=0', color='blue', linestyle='--')     
plt.plot(range(0, 6), avg_income_levels, label='Income', color='green', linestyle='-')    
plt.plot(range(0, 6), avg_income_levels_splurge0, label='Income, splurge=0', color='green', linestyle='--')  
plt.plot(range(0, 6), avg_wealth_levels, label='Share at borrowing limit', color='red', linestyle='-')    
plt.plot(range(0, 6), avg_wealth_levels_splurge0, label='Share at borrowing limit, splurge=0', color='red', linestyle='--')   
plt.xlabel('quarters since last period of employment')    
plt.ylabel('1 = permanent income in last period of employment')    
plt.legend()    
plt.grid(True)  
make_figs('UIextension_CompSplurge0', True , False, target_dir=Abs_Path+'/Figures/Splurge0/')  
plt.show()  


# Plot the results  
plt.figure(figsize=(7, 6))    
plt.plot(range(0, 6), avg_consumption_levels, label='Consumption', color='blue', linestyle='-')      
plt.plot(range(0, 6), avg_income_levels, label='Income', color='green', linestyle='-')       
plt.xlabel('quarters since last period of employment')    
plt.ylabel('1 = permanent income in last period of employment')    
plt.legend()    
plt.grid(True)  
make_figs('UnempSpell_Dynamics', True , False, target_dir=Abs_Path+'/Figures/')  
plt.show()  



print('Mean reduction in consumption upon entering unemployment benefits state: ', 100*(1-avg_consumption_levels[1]/avg_consumption_levels[0]), '%.')
print('Mean reduction in consumption upon leaving unemployment benefits state: ', 100*(1-avg_consumption_levels[3]/avg_consumption_levels[2]), '%.')


print('For splurge = 0')
print('Mean reduction in consumption upon entering unemployment benefits state: ', 100*(1-avg_consumption_levels_splurge0[1]/avg_consumption_levels_splurge0[0]), '%.')
print('Mean reduction in consumption upon leaving unemployment benefits state: ', 100*(1-avg_consumption_levels_splurge0[3]/avg_consumption_levels_splurge0[2]), '%.')