# filename: do_all.py

# Import the exec function
from builtins import exec
import sys 
import os


#%% This script is a reduced version of do_all.py
# It only executes Step 4 of do_all.py 
# It thus skips the estimation of the splurge and discount factors (and robustness estimations)
# For step 4, we consider a simpler setup and reduce the number of discount factors per education group to 1
# Furthermore, we only run N=100 rather than 10000 agents.
# Finally, the Aggregate Demand solution is run calculated with fewer iterations (reducing accuracy)
# The code creates IRF for the simulations in FromPandemicCode\Figures\Reduced_Run
# and a table of the Multipliers in  FromPandemicCode\Tables\Reduced_Run
# The whole code should take roughly one hour to execute (using a laptop computer)


print('Step 4: Comparing policies\n')
script_path = "AggFiscalMAIN_reduced.py"
os.chdir('./Code/HA-Models/FromPandemicCode')
exec(open(script_path).read())
os.chdir('../')
print('Concluded Step 4. \n')