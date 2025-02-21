import os
from Welfare import Welfare_Results
from HARK.utilities import make_figs

def Output_Results(saved_results_dir,fig_dir,table_dir,Parametrization='Baseline'):

    # Make folders for output   
    try:
        os.mkdir(fig_dir)
    except OSError:
        print ("Creation of the directory %s failed" % fig_dir)
    else:
        print ("Successfully created the directory %s " % fig_dir)

    try:
        os.mkdir(table_dir)
    except OSError:
        print ("Creation of the directory %s failed" % table_dir)
    else:
        print ("Successfully created the directory %s " % table_dir)


    
    
    from Parameters import returnParameters
    import numpy as np
    import matplotlib.pyplot as plt
    from OtherFunctions import getSimulationDiff, getSimulationPercentDiff, getNPVMultiplier, loadPickle, saveAsPickleUnderVarName
    mystr = lambda x : '{:.2f}'.format(x)
    
    
    [max_recession_duration, Rspell, Rfree_base, figs_dir_FullRun, CRRA]  = returnParameters(Parametrization=Parametrization,OutputFor='_Output_Results.py')
    
    
    Plot_1stRoundAd         = False
            
    max_T = 12
    x_axis = np.arange(1,max_T+1)
    
    folder_AD           = saved_results_dir
    if Parametrization.find('PVSame')>0:
        folder_nonPVSame         = figs_dir_FullRun
    else:
        folder_nonPVSame         = saved_results_dir
        

    base_results                            = loadPickle('base_results',folder_nonPVSame,locals())
    
    recession_results                       = loadPickle('recession_results',folder_nonPVSame,locals())
    recession_results_AD                    = loadPickle('recession_results_AD',folder_nonPVSame,locals())
    recession_results_firstRoundAD          = loadPickle('recession_results_firstRoundAD',folder_nonPVSame,locals())
    
    recession_UI_results                    = loadPickle('recessionUI_results',folder_nonPVSame,locals())       
    recession_UI_results_AD                 = loadPickle('recessionUI_results_AD',folder_nonPVSame,locals())
    recession_UI_results_firstRoundAD       = loadPickle('recessionUI_results_firstRoundAD',folder_nonPVSame,locals())
    
    recession_Check_results                 = loadPickle('recessionCheck_results',saved_results_dir,locals())       
    recession_Check_results_AD              = loadPickle('recessionCheck_results_AD',saved_results_dir,locals())
    recession_Check_results_firstRoundAD    = loadPickle('recessionCheck_results_firstRoundAD',saved_results_dir,locals())
    
    recession_TaxCut_results                = loadPickle('recessionTaxCut_results',saved_results_dir,locals())
    recession_TaxCut_results_AD             = loadPickle('recessionTaxCut_results_AD',saved_results_dir,locals())
    recession_TaxCut_results_firstRoundAD   = loadPickle('recessionTaxCut_results_firstRoundAD',saved_results_dir,locals())
    
    if type(recession_TaxCut_results_firstRoundAD) == int:
        Mltp_1stRoundAd         = False
    else:
        Mltp_1stRoundAd         = True
          
    
    #%% IRFs for income and consumption for three policies
    # Tax cut        
    
    
    AddCons_Rec_TaxCut_RelRec               = getSimulationPercentDiff(recession_results,               recession_TaxCut_results,'AggCons')
    AddCons_Rec_TaxCut_AD_RelRec            = getSimulationPercentDiff(recession_results_AD,            recession_TaxCut_results_AD,'AggCons')
    
    AddInc_Rec_TaxCut_RelRec                = getSimulationPercentDiff(recession_results,               recession_TaxCut_results,'AggIncome')
    AddInc_Rec_TaxCut_AD_RelRec             = getSimulationPercentDiff(recession_results_AD,            recession_TaxCut_results_AD,'AggIncome')
    
    if Plot_1stRoundAd:
        AddCons_Rec_TaxCut_firstRoundAD_RelRec  = getSimulationPercentDiff(recession_results_firstRoundAD,  recession_TaxCut_results_firstRoundAD,'AggCons')
        AddInc_Rec_TaxCut_firstRoundAD_RelRec  = getSimulationPercentDiff(recession_results_firstRoundAD,   recession_TaxCut_results_firstRoundAD,'AggIncome')
       
    
    plt.figure(figsize=(4, 4))
    #plt.title('Recession + tax cut', size=30)
    plt.plot(x_axis,AddInc_Rec_TaxCut_RelRec[0:max_T],              color='#377eb8',linestyle='-')
    plt.plot(x_axis,AddInc_Rec_TaxCut_AD_RelRec[0:max_T],           color='#377eb8',linestyle='--')
    if Plot_1stRoundAd:
        plt.plot(x_axis,AddInc_Rec_TaxCut_firstRoundAD_RelRec[0:max_T], color='#377eb8',linestyle=':')
    plt.plot(x_axis,AddCons_Rec_TaxCut_RelRec[0:max_T],             color='#ff7f00',linestyle='-')
    plt.plot(x_axis,AddCons_Rec_TaxCut_AD_RelRec[0:max_T],          color='#ff7f00',linestyle='--') 
    
    #plt.legend(['Income','Income (AD effects)', \
    #            'Consumption','Consumption (AD effects)'],loc='best')
    
    if Plot_1stRoundAd:
        plt.plot(x_axis,AddCons_Rec_TaxCut_firstRoundAD_RelRec[0:max_T],color='#ff7f00',linestyle=':')
        plt.legend(['Income','Income (AD effects)','Inc, 1st round AD effects', \
                    'Consumption','Consumption (AD effects)','Cons, 1st round AD effects'])
            
    plt.xticks(np.arange(min(x_axis), max(x_axis)+1, 1.0))
    plt.xlabel('quarter')
    #plt.ylabel('% difference relative to recession')
    #plt.savefig(fig_dir +'recession_taxcut_relrecession.pdf')
    plt.ylim(-0.2, 6.5)
    make_figs('recession_taxcut_relrecession', True , False, target_dir=fig_dir)
    plt.show()   
    
    
    
    #UI extension
    AddCons_UI_Ext_Rec_RelRec               = getSimulationPercentDiff(recession_results,    recession_UI_results,'AggCons')
    AddInc_UI_Ext_Rec_RelRec                = getSimulationPercentDiff(recession_results,    recession_UI_results,'AggIncome')
    
    AddCons_UI_Ext_Rec_RelRec_AD            = getSimulationPercentDiff(recession_results_AD,    recession_UI_results_AD,'AggCons')
    AddInc_UI_Ext_Rec_RelRec_AD             = getSimulationPercentDiff(recession_results_AD,    recession_UI_results_AD,'AggIncome')
     
    if Plot_1stRoundAd:
        AddCons_UI_Ext_Rec_RelRec_firstRoundAD  = getSimulationPercentDiff(recession_results_firstRoundAD,    recession_UI_results_firstRoundAD,'AggCons')
        AddInc_UI_Ext_Rec_RelRec_firstRoundAD   = getSimulationPercentDiff(recession_results_firstRoundAD,    recession_UI_results_firstRoundAD,'AggIncome')       
    
    plt.figure(figsize=(4, 4))
    #plt.title('Recession + UI extension', size=30)
    plt.plot(x_axis,AddInc_UI_Ext_Rec_RelRec[0:max_T],              color='#377eb8',linestyle='-')
    plt.plot(x_axis,AddInc_UI_Ext_Rec_RelRec_AD[0:max_T],           color='#377eb8',linestyle='--')
    if Plot_1stRoundAd:
        plt.plot(x_axis,AddInc_UI_Ext_Rec_RelRec_firstRoundAD[0:max_T], color='#377eb8',linestyle=':')
    plt.plot(x_axis,AddCons_UI_Ext_Rec_RelRec[0:max_T],             color='#ff7f00',linestyle='-')
    plt.plot(x_axis,AddCons_UI_Ext_Rec_RelRec_AD[0:max_T],          color='#ff7f00',linestyle='--') 
    
    #plt.legend(['Income','Income (AD effects)', \
    #            'Consumption','Consumption (AD effects)'],loc='best')
    
    if Plot_1stRoundAd:
        plt.plot(x_axis,AddCons_Rec_TaxCut_firstRoundAD_RelRec[0:max_T],color='#ff7f00',linestyle=':')
        plt.legend(['Income','Income (AD effects)','Inc, 1st round AD effects', \
                    'Consumption','Consumption (AD effects)','Cons, 1st round AD effects'])
            
    plt.xticks(np.arange(min(x_axis), max(x_axis)+1, 1.0))
    plt.xlabel('quarter')
    #plt.ylabel('% difference relative to recession')
    #plt.savefig(fig_dir +'recession_UI_relrecession.pdf')
    plt.ylim(-0.2, 6.5)
    make_figs('recession_UI_relrecession', True , False, target_dir=fig_dir)
    plt.show() 
    
    
    #Check stimulus    
    AddCons_Rec_Check_RelRec               = getSimulationPercentDiff(recession_results,               recession_Check_results,'AggCons')
    AddInc_Rec_Check_RelRec                = getSimulationPercentDiff(recession_results,               recession_Check_results,'AggIncome')
    
    AddCons_Rec_Check_AD_RelRec            = getSimulationPercentDiff(recession_results_AD,            recession_Check_results_AD,'AggCons')
    AddInc_Rec_Check_AD_RelRec             = getSimulationPercentDiff(recession_results_AD,            recession_Check_results_AD,'AggIncome')
    
    if Plot_1stRoundAd:
        AddCons_Rec_Check_firstRoundAD_RelRec  = getSimulationPercentDiff(recession_results_firstRoundAD,  recession_Check_results_firstRoundAD,'AggCons')
        AddInc_Rec_Check_firstRoundAD_RelRec   = getSimulationPercentDiff(recession_results_firstRoundAD,  recession_Check_results_firstRoundAD,'AggIncome')
    
    
    plt.figure(figsize=(4, 4))
    #plt.title('Recession + Check', size=30)
    plt.plot(x_axis,AddInc_Rec_Check_RelRec[0:max_T],              color='#377eb8',linestyle='-')
    plt.plot(x_axis,AddInc_Rec_Check_AD_RelRec[0:max_T],           color='#377eb8',linestyle='--')
    if Plot_1stRoundAd:
        plt.plot(x_axis,AddInc_Rec_Check_firstRoundAD_RelRec[0:max_T], color='#377eb8',linestyle=':')
    plt.plot(x_axis,AddCons_Rec_Check_RelRec[0:max_T],             color='#ff7f00',linestyle='-')
    plt.plot(x_axis,AddCons_Rec_Check_AD_RelRec[0:max_T],          color='#ff7f00',linestyle='--') 
    
    plt.legend(['Income','Income (AD effects)', \
                'Consumption','Consumption (AD effects)'],loc='best')
    
    if Plot_1stRoundAd:
        plt.plot(x_axis,AddCons_Rec_TaxCut_firstRoundAD_RelRec[0:max_T],color='#ff7f00',linestyle=':')
        plt.legend(['Income','Income (AD effects)','Inc, 1st round AD effects', \
                    'Consumption','Consumption (AD effects)','Cons, 1st round AD effects'])
            
    plt.xticks(np.arange(min(x_axis), max(x_axis)+1, 1.0))
    plt.xlabel('quarter')
    plt.ylabel('% difference relative to recession')
    plt.ylim(-0.2, 6.5)
    #plt.savefig(fig_dir +'recession_Check_relrecession.pdf')
    make_figs('recession_Check_relrecession', True , False, target_dir=fig_dir)
    plt.show()        
    
    
    #########################################################################
    #########################################################################
    #########################################################################
       
    
    
    
    
    
    
    
    #%% Multipliers
    
    
    
    NPV_AddInc_UI_Rec                       = getSimulationDiff(recession_results,recession_UI_results,'NPV_AggIncome') # Policy expenditure
    NPV_Multiplier_UI_Rec                   = getNPVMultiplier(recession_results,               recession_UI_results,               NPV_AddInc_UI_Rec)
    NPV_Multiplier_UI_Rec_AD                = getNPVMultiplier(recession_results_AD,            recession_UI_results_AD,            NPV_AddInc_UI_Rec)
    if Mltp_1stRoundAd:
        NPV_Multiplier_UI_Rec_firstRoundAD  = getNPVMultiplier(recession_results_firstRoundAD,  recession_UI_results_firstRoundAD,  NPV_AddInc_UI_Rec)
    else:
        NPV_Multiplier_UI_Rec_firstRoundAD = np.zeros_like(NPV_Multiplier_UI_Rec)
    
    
    NPV_AddInc_Rec_TaxCut                   = getSimulationDiff(recession_results,recession_TaxCut_results,'NPV_AggIncome')
    NPV_Multiplier_Rec_TaxCut               = getNPVMultiplier(recession_results,               recession_TaxCut_results,               NPV_AddInc_Rec_TaxCut)
    NPV_Multiplier_Rec_TaxCut_AD            = getNPVMultiplier(recession_results_AD,            recession_TaxCut_results_AD,            NPV_AddInc_Rec_TaxCut)
    if Mltp_1stRoundAd:
        NPV_Multiplier_Rec_TaxCut_firstRoundAD  = getNPVMultiplier(recession_results_firstRoundAD,  recession_TaxCut_results_firstRoundAD,  NPV_AddInc_Rec_TaxCut)
    else:
        NPV_Multiplier_Rec_TaxCut_firstRoundAD = np.zeros_like(NPV_Multiplier_Rec_TaxCut)
        
    NPV_AddInc_Rec_Check                    = getSimulationDiff(recession_results,recession_Check_results,'NPV_AggIncome') 
    NPV_Multiplier_Rec_Check                = getNPVMultiplier(recession_results,               recession_Check_results,               NPV_AddInc_Rec_Check)
    NPV_Multiplier_Rec_Check_AD             = getNPVMultiplier(recession_results_AD,            recession_Check_results_AD,            NPV_AddInc_Rec_Check)
    if Mltp_1stRoundAd:
        NPV_Multiplier_Rec_Check_firstRoundAD   = getNPVMultiplier(recession_results_firstRoundAD,  recession_Check_results_firstRoundAD,  NPV_AddInc_Rec_Check)
    else:
        NPV_Multiplier_Rec_Check_firstRoundAD = np.zeros_like(NPV_Multiplier_Rec_Check)
 
    #print('NPV Multiplier check recession no AD: \t\t',mystr(NPV_Multiplier_Rec_Check[-1]))
    print('NPV Multiplier check recession with AD: \t',mystr(NPV_Multiplier_Rec_Check_AD[-1]))
    print('NPV Multiplier check recession 1st round AD: \t',mystr(NPV_Multiplier_Rec_Check_firstRoundAD[-1]))
    print('')
    # Multipliers in non-AD are less than 1 -> this is because of deaths!
            
    #print('NPV Multiplier UI recession no AD: \t\t',mystr(NPV_Multiplier_UI_Rec[-1]))
    print('NPV Multiplier UI recession with AD: \t\t',mystr(NPV_Multiplier_UI_Rec_AD[-1]))
    print('NPV Multiplier UI recession 1st round AD: \t',mystr(NPV_Multiplier_UI_Rec_firstRoundAD[-1]))
    print('')
    
    #print('NPV Multiplier tax cut recession no AD: \t',mystr(NPV_Multiplier_Rec_TaxCut[-1]))
    print('NPV Multiplier tax cut recession with AD: \t',mystr(NPV_Multiplier_Rec_TaxCut_AD[-1]))
    print('NPV Multiplier tax cut recession 1st round AD:  ',mystr(NPV_Multiplier_Rec_TaxCut_firstRoundAD[-1]))
    print('')
    

    
    # Multiplier plots for AD case
    max_T2 = 12
    
    
    
    
    
    
    #Cumulative, common plot
    C_Multiplier_UI_Rec_AD                = getNPVMultiplier(recession_results_AD,            recession_UI_results_AD,            NPV_AddInc_UI_Rec[-1])
    C_Multiplier_Rec_TaxCut_AD            = getNPVMultiplier(recession_results_AD,            recession_TaxCut_results_AD,        NPV_AddInc_Rec_TaxCut[-1])
    C_Multiplier_Rec_Check_AD             = getNPVMultiplier(recession_results_AD,            recession_Check_results_AD,         NPV_AddInc_Rec_Check[-1])
    x_axis = np.arange(1,max_T2+1)
    plt.plot(x_axis,C_Multiplier_Rec_Check_AD[0:max_T2],               color='#4daf4a',linestyle='-')
    plt.plot(x_axis,C_Multiplier_UI_Rec_AD[0:max_T2],                  color='#377eb8',linestyle='-')
    plt.plot(x_axis,C_Multiplier_Rec_TaxCut_AD[0:max_T2],              color='#ff7f00',linestyle='-')
    plt.legend(['Stimulus check','UI extension','Tax cut',])
    plt.xticks(np.arange(min(x_axis), max(x_axis)+1, 1))
    plt.xlabel('quarter')
    #plt.savefig(fig_dir +'Cummulative_multipliers.pdf')
    make_figs('Cummulative_multipliers', True , False, target_dir=fig_dir)
    plt.show()
    
    # Save multiplier values for comparison
    if Parametrization=='Baseline':
        C_Multiplier_Baseline_Results = {  
        'C_Multiplier_Rec_Check_AD': C_Multiplier_Rec_Check_AD,  
        'C_Multiplier_UI_Rec_AD': C_Multiplier_UI_Rec_AD,  
        'C_Multiplier_Rec_TaxCut_AD': C_Multiplier_Rec_TaxCut_AD  
        }
        
        saveAsPickleUnderVarName(C_Multiplier_Baseline_Results,fig_dir,locals())
        
    #Cumulative, single plots
    if Parametrization=='Baseline':
        x_axis = np.arange(1,max_T2+1)
        plt.plot(x_axis,C_Multiplier_Rec_Check_AD[0:max_T2],                  color='#377eb8')
        plt.xticks(np.arange(min(x_axis), max(x_axis)+1, 1))
        plt.xlabel('quarter')
        plt.ylim(0, 1.25)
        make_figs('Cummulative_multiplier_Check', True , False, target_dir=fig_dir)
        plt.show()
        
        plt.plot(x_axis,C_Multiplier_UI_Rec_AD[0:max_T2],                  color='#377eb8')
        plt.xticks(np.arange(min(x_axis), max(x_axis)+1, 1))
        plt.xlabel('quarter')
        plt.ylim(0, 1.25)
        make_figs('Cummulative_multiplier_UI', True , False, target_dir=fig_dir)
        plt.show()
        
        plt.plot(x_axis,C_Multiplier_Rec_TaxCut_AD[0:max_T2],                  color='#377eb8')
        plt.xticks(np.arange(min(x_axis), max(x_axis)+1, 1))
        plt.xlabel('quarter')
        plt.ylim(0, 1.25)
        make_figs('Cummulative_multiplier_TaxCut', True , False, target_dir=fig_dir)
        plt.show()
        
        

    
    # Comparison chart with HANK for baseline
    if Parametrization=='Baseline':
        
        cwd              = os.getcwd()
        folders          = cwd.split(os.path.sep)
        Abs_Path_Results = "".join([x + "//" for x in folders[0:-1]],)
        HANK_results_dir = Abs_Path_Results+'Results_HANK/multipliers_across_horizon_w_splurge.obj' 
        
        import pickle
        with open(HANK_results_dir, 'rb') as f:
            HANK_results = pickle.load(f)
    
    
        fig, ax = plt.subplots()  
        
        ax.plot(x_axis,C_Multiplier_Rec_Check_AD[0:max_T2],               color='#4daf4a',linestyle='-')
        ax.plot(x_axis,HANK_results['transfers'][0:max_T2],        color='#4daf4a',linestyle=':')  
        
        ax.plot(x_axis,C_Multiplier_UI_Rec_AD[0:max_T2],                  color='#377eb8',linestyle='-')
        ax.plot(x_axis,HANK_results['UI_extensions'][0:max_T2],    color='#377eb8',linestyle=':') 
        
        ax.plot(x_axis,C_Multiplier_Rec_TaxCut_AD[0:max_T2],              color='#ff7f00',linestyle='-')
        ax.plot(x_axis,HANK_results['tax_cut'][0:max_T2],          color='#ff7f00',linestyle=':')  
          
        ax.legend(['Check','Check, HANK model','UI extension','UI extension, HANK model','Tax cut','Tax cut, HANK model'])
        plt.xticks(np.arange(min(x_axis), max(x_axis)+1, 1))
        ax.set_xlabel('quarter')
        make_figs('Cummulative_multipliers_withHank', True , False, target_dir=fig_dir)
          
        # Show the plot  
        plt.show()
        
        
        HANK_results_dir = Abs_Path_Results+'Results_HANK/multipliers_across_horizon.obj' 
        
        import pickle
        with open(HANK_results_dir, 'rb') as f:
            HANK_results = pickle.load(f)
    
    
        fig, ax = plt.subplots()  
        
        ax.plot(x_axis,C_Multiplier_Rec_Check_AD[0:max_T2],               color='#4daf4a',linestyle='-')
        ax.plot(x_axis,HANK_results['transfers'][0:max_T2],        color='#4daf4a',linestyle=':')  
        
        ax.plot(x_axis,C_Multiplier_UI_Rec_AD[0:max_T2],                  color='#377eb8',linestyle='-')
        ax.plot(x_axis,HANK_results['UI_extensions'][0:max_T2],    color='#377eb8',linestyle=':') 
        
        ax.plot(x_axis,C_Multiplier_Rec_TaxCut_AD[0:max_T2],              color='#ff7f00',linestyle='-')
        ax.plot(x_axis,HANK_results['tax_cut'][0:max_T2],          color='#ff7f00',linestyle=':')  
          
        ax.legend(['Check','Check, HANK model','UI extension','UI extension, HANK model','Tax cut','Tax cut, HANK model'])
        plt.xticks(np.arange(min(x_axis), max(x_axis)+1, 1))
        ax.set_xlabel('quarter')
        make_figs('Cummulative_multipliers_withHanknoSpluge', True , False, target_dir=fig_dir)
          
        # Show the plot  
        plt.show()
    
    # Comparison chart with baseline for Splurge = 0
    if Parametrization == 'Splurge0':
        
        
        Abs_Path              = os.getcwd()   
        C_Multiplier_Baseline_Results = loadPickle('C_Multiplier_Baseline_Results',Abs_Path+'/Figures/',locals())
        
        fig, ax = plt.subplots()  
        
        ax.plot(x_axis,C_Multiplier_Baseline_Results['C_Multiplier_Rec_Check_AD'][0:max_T2],        color='#4daf4a',linestyle='-')
        ax.plot(x_axis,C_Multiplier_Rec_Check_AD[0:max_T2],                                         color='#4daf4a',linestyle=':')  
        
        ax.plot(x_axis,C_Multiplier_Baseline_Results['C_Multiplier_UI_Rec_AD'][0:max_T2],           color='#377eb8',linestyle='-')
        ax.plot(x_axis,C_Multiplier_UI_Rec_AD[0:max_T2],                                            color='#377eb8',linestyle=':') 
        
        ax.plot(x_axis,C_Multiplier_Baseline_Results['C_Multiplier_Rec_TaxCut_AD'][0:max_T2],       color='#ff7f00',linestyle='-')
        ax.plot(x_axis,C_Multiplier_Rec_TaxCut_AD[0:max_T2],                                        color='#ff7f00',linestyle=':')  
          
        ax.legend(['Check, splurge > 0','Check, splurge = 0','UI extension, splurge > 0','UI extension, splurge = 0','Tax cut, splurge > 0','Tax cut, splurge = 0'])
        plt.xticks(np.arange(min(x_axis), max(x_axis)+1, 1))
        ax.set_xlabel('quarter')
        make_figs('Cummulative_multipliers_SplurgeComp', True , False, target_dir=fig_dir)
          
        # Show the plot  
        plt.show()
        
    

    
    
    # Share of policy expenditure during recession
    R_persist = 1.-1./Rspell        
    recession_prob_array = np.array([R_persist**t*(1-R_persist) for t in range(max_recession_duration)])
    recession_prob_array[-1] = 1.0 - np.sum(recession_prob_array[:-1])
         
    def ShareOfPolicyDuringRec(rec,TaxCut,UI,Check,recession_prob_array,max_T):  
        # considers runs different recession lengths and calculates expenditure share within those runs
        # then sums it up weighing by probability of that recession length
        ShareduringRecession = dict()
        ShareduringRecession['Tax_Inc']     = 0
        ShareduringRecession['Tax_Cons']    = 0
        ShareduringRecession['UI_Inc']      = 0
        ShareduringRecession['UI_Cons']     = 0
        ShareduringRecession['Check_Inc']   = 0
        ShareduringRecession['Check_Cons']  = 0
             
        for i in range(max_recession_duration):      
            NPV_TaxCut                      = getSimulationDiff(rec[i],TaxCut[i],'NPV_AggIncome') 
            ShareduringRecession['Tax_Inc'] += NPV_TaxCut[i]/NPV_TaxCut[-1]*recession_prob_array[i]
            
            NPV_Cons_TaxCut                 = getSimulationDiff(rec[i],TaxCut[i],'NPV_AggCons') 
            ShareduringRecession['Tax_Cons']+= NPV_Cons_TaxCut[i]/NPV_Cons_TaxCut[-1]*recession_prob_array[i]
            
            
            NPV_UI                          = getSimulationDiff(rec[i],UI[i],'NPV_AggIncome') 
            ShareduringRecession['UI_Inc']  += NPV_UI[i]/NPV_UI[-1]*recession_prob_array[i]
            
            NPV_Cons_UI                     = getSimulationDiff(rec[i],UI[i],'NPV_AggCons') 
            ShareduringRecession['UI_Cons'] += NPV_Cons_UI[i]/NPV_Cons_UI[-1]*recession_prob_array[i]
            
            
            NPV_Check                           = getSimulationDiff(rec[i],Check[i],'NPV_AggIncome') 
            ShareduringRecession['Check_Inc']   += NPV_Check[i]/NPV_Check[-1]*recession_prob_array[i]
            
            NPV_Cons_Check                      = getSimulationDiff(rec[i],Check[i],'NPV_AggCons') 
            ShareduringRecession['Check_Cons']  += NPV_Cons_Check[i]/NPV_Cons_Check[-1]*recession_prob_array[i]
             
        # times 100
        ShareduringRecession = {key: value * 100 for key, value in ShareduringRecession.items()} 
        
        # output
        for key, value in ShareduringRecession.items():  
            print(f"Key: {key}, Value: {value}")  
            
        return ShareduringRecession
        
             
    recession_all_results        = loadPickle('recession_all_results',folder_nonPVSame,locals())   
    recession_all_results_UI     = loadPickle('recessionUI_all_results',folder_nonPVSame,locals())
    recession_all_results_TaxCut = loadPickle('recessionTaxCut_all_results',saved_results_dir,locals())
    recession_all_results_Check  = loadPickle('recessionCheck_all_results',saved_results_dir,locals())
        
    ShareduringRecession=ShareOfPolicyDuringRec(recession_all_results,recession_all_results_TaxCut,\
                           recession_all_results_UI,recession_all_results_Check,\
                           recession_prob_array,max_recession_duration)
            
    
    def mystr3(number):
        if not np.isnan(number):
            out = "{:.3f}".format(number)
        else:
            out = ''
        return out
    
    def mystr1(number):
        if not np.isnan(number):
            out = "{:.1f}".format(number)
        else:
            out = ''
        return out
        
    output  ="\\begin{tabular}{@{}lccc@{}} \n"
    output +="\\toprule \n"
    output +="& Stimulus check    & UI extension    & Tax cut     \\\\  \\midrule \n"
    output +="10y-horizon Multiplier (no AD effect) &"   + mystr3(NPV_Multiplier_Rec_Check[-1])             + "  & "+ mystr3(NPV_Multiplier_UI_Rec[-1])               +  "  & "+  mystr3(NPV_Multiplier_Rec_TaxCut[-1])  + "     \\\\ \n"
    output +="10y-horizon Multiplier (AD effect) &"      + mystr3(NPV_Multiplier_Rec_Check_AD[-1])             + "  & "+ mystr3(NPV_Multiplier_UI_Rec_AD[-1])               +  "  & "+  mystr3(NPV_Multiplier_Rec_TaxCut_AD[-1])  + "     \\\\ \n"
    output +="10y-horizon (1st round AD effect only) &"  + mystr3(NPV_Multiplier_Rec_Check_firstRoundAD[-1])   + "  & "+ mystr3(NPV_Multiplier_UI_Rec_firstRoundAD[-1])     +  "  & "+  mystr3(NPV_Multiplier_Rec_TaxCut_firstRoundAD[-1])  + "     \\\\ \n"
    output +="Share of policy expenditure during recession &" + mystr1(ShareduringRecession['Check_Inc'])   + "\%  & "+ mystr1(ShareduringRecession['UI_Inc'])  +  "\%  & "+  mystr1(ShareduringRecession['Tax_Inc'])  + " \%    \\\\ \n"
    output +="Share of policy cons. stimulus during recession &" + mystr1(ShareduringRecession['Check_Cons'])   + "\%  & "+ mystr1(ShareduringRecession['UI_Cons'])  +  "\%  & "+  mystr1(ShareduringRecession['Tax_Cons'])  + " \%    \\\\ \\bottomrule \n"
    output +="\\end{tabular}  \n"

    
    with open(table_dir + 'Multiplier.tex','w') as f:
        f.write(output)
        f.close()
        
        
    # Save multiplier values for comparison
    if Parametrization=='Baseline':
        NPV_Multiplier_Baseline_Results = {  
        'NPV_Multiplier_Rec_Check':     NPV_Multiplier_Rec_Check,  
        'NPV_Multiplier_UI_Rec':        NPV_Multiplier_UI_Rec,  
        'NPV_Multiplier_Rec_TaxCut':    NPV_Multiplier_Rec_TaxCut,
        'NPV_Multiplier_Rec_Check_AD':  NPV_Multiplier_Rec_Check_AD,  
        'NPV_Multiplier_UI_Rec_AD':     NPV_Multiplier_UI_Rec_AD,  
        'NPV_Multiplier_Rec_TaxCut_AD': NPV_Multiplier_Rec_TaxCut_AD,
        }
        saveAsPickleUnderVarName(NPV_Multiplier_Baseline_Results,fig_dir,locals())

    
    # Comparison chart with baseline for Splurge = 0
    if Parametrization == 'Splurge0':
        Abs_Path              = os.getcwd()   
        NPV_Multiplier_Baseline_Results = loadPickle('NPV_Multiplier_Baseline_Results',Abs_Path+'/Figures/',locals())

        
        output  ="\\begin{tabular}{@{}lccc@{}} \n"
        output +="\\toprule \n"
        output +="& Stimulus check    & UI extension    & Tax cut     \\\\  \\midrule \n"
        output +="10y-horizon Multiplier (no AD effect)  &"    + mystr3(NPV_Multiplier_Rec_Check[-1])  +"(" + mystr3(NPV_Multiplier_Baseline_Results['NPV_Multiplier_Rec_Check'][-1]) +")"         + "  & "+ mystr3(NPV_Multiplier_UI_Rec[-1])    +"(" +  mystr3(NPV_Multiplier_Baseline_Results['NPV_Multiplier_UI_Rec'][-1]) +")" +              "  & "+  mystr3(NPV_Multiplier_Rec_TaxCut[-1]) +"(" + mystr3(NPV_Multiplier_Baseline_Results['NPV_Multiplier_Rec_TaxCut'][-1])   +")" +    "     \\\\ \n"
        output +="10y-horizon Multiplier (AD effect) &"       + mystr3(NPV_Multiplier_Rec_Check_AD[-1])  +"(" + mystr3(NPV_Multiplier_Baseline_Results['NPV_Multiplier_Rec_Check_AD'][-1]) +")"            + "  & "+ mystr3(NPV_Multiplier_UI_Rec_AD[-1])   +"(" + mystr3(NPV_Multiplier_Baseline_Results['NPV_Multiplier_UI_Rec_AD'][-1]) +")" +              "  & "+  mystr3(NPV_Multiplier_Rec_TaxCut_AD[-1])  +"(" + mystr3( NPV_Multiplier_Baseline_Results['NPV_Multiplier_Rec_TaxCut_AD'][-1]) +")" +   "     \\\\ \n"
        output +="\\end{tabular}  \n"
    
        
        with open(table_dir + 'Multiplier_SplurgeComp.tex','w') as f:
            f.write(output)
            f.close()    
    
    
    
    
    
    
    
    
    
    
    #%% Function that returns information on a policy with specific RecLength and PolicyLength
    RunRecLengthAnalysis = False
    if RunRecLengthAnalysis:
    
        def PlotsforSpecificRecLength(RecLength,Policy): 
        
            # Policy options 'recession_UI' / 'recession_TaxCut' / 'recession_Check'
            
            recession_all_results               = loadPickle('recession_all_results',folder_nonPVSame,locals())
            recession_all_results_AD            = loadPickle('recession_all_results_AD',folder_nonPVSame,locals())
            if Mltp_1stRoundAd:
                recession_all_results_firstRoundAD  = loadPickle('recession_all_results_firstRoundAD',folder_nonPVSame,locals())
            
            if Policy == 'recessionUI':
                folder_policy = folder_nonPVSame
            else:
                folder_policy = saved_results_dir
                    
            
            recession_all_policy_results        = loadPickle( Policy + '_all_results',folder_policy,locals())       
            recession_all_policy_results_AD     = loadPickle(Policy + '_all_results_AD',folder_policy,locals())
            if Mltp_1stRoundAd:
                recession_all_policy_results_firstRoundAD= loadPickle(Policy + '_all_results_firstRoundAD',folder_policy,locals())
            
            
            NPV_AddInc                  = getSimulationDiff(recession_all_results[RecLength-1],recession_all_policy_results[RecLength-1],'NPV_AggIncome') # Policy expenditure
            NPV_Multiplier              = getNPVMultiplier(recession_all_results[RecLength-1],               recession_all_policy_results[RecLength-1],               NPV_AddInc)
            NPV_Multiplier_AD           = getNPVMultiplier(recession_all_results_AD[RecLength-1],            recession_all_policy_results_AD[RecLength-1],            NPV_AddInc)
            if Mltp_1stRoundAd:
                NPV_Multiplier_firstRoundAD = getNPVMultiplier(recession_all_results_firstRoundAD[RecLength-1],  recession_all_policy_results_firstRoundAD[RecLength-1],  NPV_AddInc)
            else:
                NPV_Multiplier_firstRoundAD = np.zeros_like(NPV_Multiplier_AD)
             
            Multipliers = [NPV_Multiplier,NPV_Multiplier_AD,NPV_Multiplier_firstRoundAD]
            
            PlotEach = False
            
            if PlotEach:
            
                AddCons_RelRec               = getSimulationPercentDiff(recession_all_results[RecLength-1],    recession_all_policy_results[RecLength-1],'AggCons')
                AddInc_RelRec                = getSimulationPercentDiff(recession_all_results[RecLength-1],    recession_all_policy_results[RecLength-1],'AggIncome')
                
                AddCons_RelRec_AD            = getSimulationPercentDiff(recession_all_results_AD[RecLength-1],    recession_all_policy_results_AD[RecLength-1],'AggCons')
                AddInc_RelRec_AD             = getSimulationPercentDiff(recession_all_results_AD[RecLength-1],    recession_all_policy_results_AD[RecLength-1],'AggIncome')
                
               
                plt.figure(figsize=(15,10))
                plt.title('Recession lasts ' + str(RecLength) + 'q', size=30)
                plt.plot(x_axis,AddInc_RelRec[0:max_T],              color='#377eb8',linestyle='-')
                plt.plot(x_axis,AddInc_RelRec_AD[0:max_T],           color='#377eb8',linestyle='--')
                plt.plot(x_axis,AddCons_RelRec[0:max_T],             color='#ff7f00',linestyle='-')
                plt.plot(x_axis,AddCons_RelRec_AD[0:max_T],          color='#ff7f00',linestyle='--') 
                plt.legend(['Inc, no AD effects','Inc, AD effects',\
                            'Cons, no AD effects','Cons, AD effects'], fontsize=14)
                plt.xticks(np.arange(min(x_axis), max(x_axis)+1, 1.0))
                plt.xlabel('quarter', fontsize=18)
                plt.ylabel('% diff. rel. to recession', fontsize=16)
                plt.show() 
                
            
            return Multipliers
            
        
        RecLengthInspect = 8
        Multiplier21qRecession_TaxCut = PlotsforSpecificRecLength(RecLengthInspect,'recessionTaxCut')
        print('NPV_Multiplier_Rec_TaxCut_AD for ' + str(RecLengthInspect) + ' q recession: ',mystr(Multiplier21qRecession_TaxCut[1][-1]))
        Multiplier21qRecession_UI = PlotsforSpecificRecLength(RecLengthInspect,'recessionUI')
        print('NPV_Multiplier_UI_Rec_AD for ' + str(RecLengthInspect) + ' q recession: ',mystr(Multiplier21qRecession_UI[1][-1]))
        Multiplier21qRecession_Check = PlotsforSpecificRecLength(RecLengthInspect,'recessionCheck')
        print('NPV_Multiplier_Rec_Check_AD for ' + str(RecLengthInspect) + ' q recession: ',mystr(Multiplier21qRecession_Check[1][-1]))
        
        
               
            
         
        
        output  ="\\begin{tabular}{@{}lccc@{}} \n"
        output +="\\toprule \n"
        output +="& Tax Cut    & UI extension    & Stimulus check    \\\\  \\midrule \n"
        output +="Recession lasts 2q &" + mystr3(PlotsforSpecificRecLength(2,'recessionTaxCut')[1][-1]) + "  & " + mystr3(PlotsforSpecificRecLength(2,'recessionUI')[1][-1]) + "  & " +  mystr3(PlotsforSpecificRecLength(2,'recessionCheck')[1][-1])  + "     \\\\ \n"
        output +="Recession lasts 4q &" + mystr3(PlotsforSpecificRecLength(4,'recessionTaxCut')[1][-1]) + "  & " + mystr3(PlotsforSpecificRecLength(4,'recessionUI')[1][-1]) + "  & " +  mystr3(PlotsforSpecificRecLength(4,'recessionCheck')[1][-1])  + "     \\\\ \n"
        output +="Recession lasts 8q &" + mystr3(PlotsforSpecificRecLength(8,'recessionTaxCut')[1][-1]) + "  & " + mystr3(PlotsforSpecificRecLength(8,'recessionUI')[1][-1]) + "  & " +  mystr3(PlotsforSpecificRecLength(8,'recessionCheck')[1][-1])  + "     \\\\ \\bottomrule \n"
        output +="\\end{tabular}  \n"
        
        with open(table_dir + 'Multiplier_RecLengths.tex','w') as f:
            f.write(output)
            f.close()  
        
        
    #%% Output welfare tables
        
    # Welfare_Results(saved_results_dir,table_dir,Parametrization=Parametrization)