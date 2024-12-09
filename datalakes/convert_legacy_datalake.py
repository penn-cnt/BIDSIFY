import pickle
import pandas as PD
from sys import argv,exit

class Value:
    def __init__(self,v=None):
        self.v=v
        
if __name__ == '__main__':
    
    # Read in the relevant columns from Joshua Asuncion's original datalake
    DF = PD.read_csv(argv[1],usecols=range(7))
    
    # Save output filename to variable
    ofile = argv[2].strip('.pickle')+'.pickle'

    # Initialize the dictionary, setting it for just HUP for now
    datalake        = {}
    datalake['HUP'] = {}
    
    # Loop over the unique keys
    for idx,ikey in enumerate(DF.protocol.values):
        
        # Grab the data slice
        iDF = DF.iloc[idx]
        
        # Make mutable variables so changes propagate
        legacy_scan_type = Value(iDF['scan type']).v
        legacy_data_type = Value(iDF['data type']).v
        legacy_modality  = Value(iDF['modality / suffix']).v
        legacy_task      = Value(iDF['task']).v
        legacy_acq       = Value(iDF['acq']).v
        legacy_ce        = Value(iDF['ce']).v
        
        datalake['HUP'][ikey] = {}
        datalake['HUP'][ikey]['scan_type'] = legacy_scan_type
        datalake['HUP'][ikey]['data_type'] = legacy_data_type
        datalake['HUP'][ikey]['modality']  = legacy_modality
        datalake['HUP'][ikey]['task']      = legacy_task
        datalake['HUP'][ikey]['acq']       = legacy_acq
        datalake['HUP'][ikey]['ce']        = legacy_ce
        
    # Save the resulting dictionary
    pickle.dump(datalake,open(ofile,'wb'))