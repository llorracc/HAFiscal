import os
import sys

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
from Output_Results import Output_Results


# Baseline
Output_Results(Abs_Path+'/Figures/CRRA2/',Abs_Path+'/Figures/',Abs_Path+'/Tables/CRRA2/',Parametrization='Baseline')
 
   
# Splurge = 0
Output_Results(Abs_Path+'/Figures/Splurge0/',Abs_Path+'/Figures/Splurge0/',Abs_Path+'/Tables/Splurge0/',Parametrization='Splurge0')
