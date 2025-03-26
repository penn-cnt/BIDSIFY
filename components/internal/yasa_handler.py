from mne.io import read_raw_edf

# Epipy imports
from components.workflows.public.channel_clean import *
from components.features.public.features import *

# Local Imports
from components.internal.observer_handler import *

class yasa_observer(Observer):

    def listen_postprocess(self):

        YASA_pointer = yasa_handler(self.data_path)
        YASA_pointer.workflow()

class yasa_handler:

    def __init__(self,data_path):

        self.infile      = data_path
        self.outfile     = data_path.strip('.edf')+'_yasa.csv'
        self.config_path = '/Users/bjprager/Documents/GitHub/CNT-codehub/scripts/codehub/configs/channel_types/scalp/hup_chop_chan_types.yaml'

    def workflow(self):

        try:
            # Read in the data
            self.read_data()

            # Clean the data as needed
            self.clean_data()

            # Run YASA
            self.YASA_wrapper()

            # Save the results
            self.YASA_DF.to_csv(self.outfile,index=False)
        except:
            pass

    def read_data(self):

        raw           = read_raw_edf(self.infile,verbose=False)
        self.data     = raw.get_data().T
        self.channels = raw.ch_names
        self.fs       = raw.info['sfreq']

    def clean_data(self):

        CC            = channel_clean()
        self.channels = CC.direct_inputs(self.channels)

    def YASA_wrapper(self):

        # get the predictions
        YP = YASA_processing(self.data,self.fs,self.channels)
        out = YP.yasa_sleep_stage(config_path=self.config_path)[0]
        
        # Unwrap the predictions and clean them up by time
        yasa_channels = out[1].split(',')
        yasa_preds    = [ival.split(',') for ival in out[0].split('|')]

        # Make the dataframe with predictions
        YASA_DF = PD.DataFrame(yasa_preds,columns=yasa_channels)

        # Add in the time columns
        YASA_DF['t_start'] = 30*(YASA_DF.index)
        YASA_DF['t_end']   = 30*(YASA_DF.index+1)

        # Final clean up of column order
        outcols = ['t_start','t_end']
        outcols.extend(yasa_channels)
        self.YASA_DF = YASA_DF[outcols]