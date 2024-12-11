import os
import time
import getpass
import pickle
import numpy as np
import pandas as PD
from mne import Annotations
from mne.export import export_raw
from mne_bids import BIDSPath,write_raw_bids

# Local Imports
from components.internal.observer_handler import *

class BIDS_observer(Observer):

    def listen_metadata(self):

        def clean_value(key,value):
            
            # Track the typing
            dtype = 'str'

            # Try a float conversion first
            try:
                newval = float(value)
                dtype  = 'float'
            except:
                newval = value

            # Try an integer conversion
            if dtype == 'float':
                if newval % 1 == 0:
                    newval = int(newval)
                    dtype  = 'int'
            
            # Clean up the value as much as possible
            if dtype == 'float':
                newval = f"{newval:06.1f}"
            elif dtype == 'int':
                newval = f"{newval:04d}"
            else:
                if key in ['start','duration']:
                    if value == None:
                        newval = "None"
                elif key in ['run']:
                    newval = int(value)
            return newval

        # Define the required BIDS keywords
        BIDS_keys = ['root','datatype','session','subject','run','task','filename','start','duration','uid']

        # Populate the bids dictionary with the new values
        for ikey,ivalue in self.keywords.items():
            if ikey in BIDS_keys:
                self.BIDS_keywords[ikey]=clean_value(ikey,ivalue)

        # If all keywords are set, send information to the BIDS handler.
        if all(self.BIDS_keywords.values()):

            # Update the bids path
            self.BH.update_path(self.BIDS_keywords)

            # See if there are annotation argument flags
            try:
                if self.args.include_annotation or self.args.annotations:
                    # Update the events
                    self.BH.create_events(self.keywords['filename'],int(self.keywords['run']),
                                        self.keywords['fs'],self.annotations)
            except AttributeError:
                pass
        else:
            print(f"Unable to create BIDS keywords for file: {self.keywords['filename']}.")
            print(f"{self.BIDS_keywords}")
        

class BIDS_handler:

    def __init__(self):
        pass

    def update_path(self,keywords):
        """
        Update the bidspath.
        """

        self.current_keywords = keywords
        self.bids_path = BIDSPath(root=keywords['root'], 
                                  datatype=keywords['datatype'], 
                                  session=keywords['session'], 
                                  subject=keywords['subject'],
                                  run=keywords['run'], 
                                  task=keywords['task'])
        
        self.target_path = f"{self.bids_path.copy()}_{keywords['datatype']}_targets.pickle"

    def create_events(self,ifile,run,fs,annotations):

        # Make the events file and save the results
        events             = []
        self.alldesc       = []
        self.event_mapping = {}
        for ii,iannot in enumerate(annotations[ifile][run].keys()):
            
            # Get the raw annotation and the index
            desc  = str(annotations[ifile][run][iannot])
            index = (1e-6*iannot)*fs

            # Make the required mne event mapper
            self.event_mapping[desc] = ii

            # Store the results
            events.append([index,0,ii])
            self.alldesc.append(desc)
        self.events  = np.array(events)

    def save_targets(self,target):

        # Store the targets
        target_dict = {'target':target,'annotation':'||'.join(self.alldesc)}
        pickle.dump(target_dict,open(self.target_path,"wb"))

    def save_data_w_events(self, raw, debug=False):
        """
        Save EDF data into a BIDS structure. With events.

        Args:
            raw (_type_): MNE Raw objext.
            debug (bool, optional): Debug flag. Acts for verbosity.

        Returns:
            _type_: _description_
        """

        # Save the bids data
        try:
            write_raw_bids(bids_path=self.bids_path, raw=raw, events=self.events,event_id=self.event_mapping, allow_preload=True, format='EDF', overwrite=True, verbose=False)
            return True
        except Exception as e:
            if debug:
                print(f"Write error: {e}")
            return False
        
    def save_data_wo_events(self, raw, debug=False):
        """
        Save EDF data into a BIDS structure.

        Args:
            raw (_type_): MNE Raw objext.
            debug (bool, optional): Debug flag. Acts for verbosity.

        Returns:
            _type_: _description_
        """

        # Save the bids data
        try:
            write_raw_bids(bids_path=self.bids_path, raw=raw, allow_preload=True, format='EDF',verbose=False,overwrite=True)
            return True
        except Exception as e:
            if debug:
                print(f"Bids write error: {e}")
            return False

    def save_raw_edf(self,raw,itype,pmin=0,pmax=1,debug=False):
        """
        If data is all zero, try to just write out the all zero timeseries data.

        Args:
            raw (_type_): _description_
            debug (bool, optional): _description_. Defaults to False.
        """

        try:
            export_raw(str(self.bids_path)+f"_{itype}.edf",raw=raw,fmt='edf',physical_range=(pmin,pmax),overwrite=True,verbose=False)
            return True
        except Exception as e:
            if debug:
                print("Raw write error: {e}")
            return False
        
    def copy_raw_edf(self,original_path,itype,debug=False):

        try:
            os.system(f"cp {original_path} {str(self.bids_path)}_{itype}.edf")
            return True
        except Exception as e:
            if debug:
                print("Raw copy error: {e}")
            return False


    def make_records(self,source):

        self.current_record = PD.DataFrame([self.current_keywords['filename']],columns=['orig_filename'])
        self.current_record['source']         = source
        self.current_record['creator']        = getpass.getuser()
        self.current_record['gendate']        = time.strftime('%d-%m-%y', time.localtime())
        self.current_record['uid']            = self.current_keywords['uid']
        self.current_record['subject_number'] = self.current_keywords['subject']
        self.current_record['session_number'] = self.current_keywords['session']
        self.current_record['run_number']     = self.current_keywords['run']
        self.current_record['start_sec']      = self.current_keywords['start']
        self.current_record['duration_sec']   = self.current_keywords['duration']
        return self.current_record