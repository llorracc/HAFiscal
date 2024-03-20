'''
This is the main script for the paper
'''
#from Parameters import returnParameters

import os
import sys
from time import time
mystr = lambda x : '{:.2f}'.format(x)

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
from Simulate import Simulate
from Output_Results import Output_Results

#%%



Run_Dict = dict()
Run_Dict['Run_Baseline']            = True
Run_Dict['Run_Recession ']          = True
Run_Dict['Run_Check_Recession']     = True
Run_Dict['Run_UB_Ext_Recession']    = True
Run_Dict['Run_TaxCut_Recession']    = True
Run_Dict['Run_Check']               = True
Run_Dict['Run_UB_Ext']              = True
Run_Dict['Run_TaxCut']              = True
Run_Dict['Run_AD ']                 = True
Run_Dict['Run_1stRoundAD']          = False
Run_Dict['Run_NonAD']               = True


t0 = time()
    
figs_dir = Abs_Path+'/Figures/Reduced_Run/'    
Simulate(Run_Dict,figs_dir,Parametrization='Reduced_Run')    
Output_Results(Abs_Path+'/Figures/Reduced_Run/',Abs_Path+'/Figures/Reduced_Run/',Abs_Path+'/Tables/Reduced_Run/',Parametrization='Reduced_Run')

t1 = time()
print('Whole script took ' + mystr((t1-t0)/60) + ' min.')
