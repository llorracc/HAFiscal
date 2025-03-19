# filename: do_all.py

# Import the exec function
from builtins import exec
import sys 
import os


#%% This script is a reduced version of do_all.py
# It only executes Step 4 and half of Step 5 of do_all.py 
# It thus skips the estimation of the splurge and discount factors (and robustness estimations)
# For step 4, we consider a simpler setup and reduce the number of discount factors per education group to 1
# Furthermore, we only run N=100 rather than 10000 agents.
# Finally, the Aggregate Demand solution is run calculated with fewer iterations (reducing accuracy)
# The code creates IRF for the simulations in FromPandemicCode\Figures\Reduced_Run
# and a table of the Multipliers in  FromPandemicCode\Tables\Reduced_Run
# For step 5, we take the Jacobians computed by HA-Fiscal-HANK-SAM.py as given
# and only conduct the policy experiements. Execution only takes seconds.
# The whole code should take roughly one hour to execute (using a laptop computer)


print('Step 4: Comparing policies\n')
script_path = "AggFiscalMAIN_reduced.py"
os.chdir('./FromPandemicCode')
exec(open(script_path).read())
print('Concluded Step 4. \n')


print('Step 5: HANK Robustness Check\n')
script_path = 'HA-Fiscal-HANK-SAM-to-python.py'
os.system("python " + script_path)  
os.chdir('../')
print('Concluded Step 5. \n')
