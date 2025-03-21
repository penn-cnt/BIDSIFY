import os
import time
import getpass
import pickle
import numpy as np
import pandas as PD

# MNE imports
from mne import Annotations
from mne.export import export_raw
from mne_bids import BIDSPath,write_raw_bids

# Pybids imports
from bids import BIDSLayout
from bids.layout.writing import build_path

# Local Imports
from components.internal.observer_handler import *

class BIDS_observer(Observer):

    def listen_metadata_eeg(self):
        """
        Checks for the needed keywords to ensure bids data is created correctly. Timeseries version.
        """

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
        
    def listen_metadata_img(self):
        """
        Checks for the needed keywords to ensure bids data is created correctly. Imaging version.
        """

        # Function to update keys to user inputted values.
        def acquire_keys(image_keys,series):
            """
            Acquire keys from the user for the current protocol name
            """

            # Make the output object and query keys
            output = {}

            # Get new inputs
            print(f"Please provide information for '{series}'")
            for ikey in image_keys:
                newval = input(f"    {ikey} (''=None): ")
                if newval == '':
                    newval = None
                output[ikey] = newval
        
            return output

        # if we have been given all the keys via cli, or given a user_input csv with all keys, we can skip asking the user for input
        if not self.skipcheck:
            # Ask the user if current keys are acceptable. If not, get new entries.,
            while True:
                # Check for required key values
                print(f"Current Protocol Name: {self.series}.")
                for ikey in self.imaging_keys:
                    if self.keywords[ikey] == None:
                        try:
                            ival = self.datalake[self.series][ikey]
                        except Exception as e:
                            print(e)
                            ival = None
                        print(f"Proposed key for {ikey:10}: {ival}")

                # Check for good keys and exit as needed
                continueflag = input(f"Create BIDS data using these keywords (Yy to proceed. Nn to update keys. Ss to skip this file.)? ")
                if continueflag.lower() == 'y':
                    for ikey in self.datalake[self.series].keys():
                        self.keywords[ikey] = self.datalake[self.series][ikey]
                    break

                # Obtain new keys
                self.datalake[self.series] = acquire_keys(self.imaging_keys,self.series)

        # Update the pathing in the bids handler
        try:
            self.BH.update_path(self.keywords)
        except:
            pass

        

class BIDS_handler_MNE:

    def __init__(self,args):
        self.args = args

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
        self.target_path = f"{self.bids_path.directory}/{self.bids_path.basename}_{keywords['datatype']}_targets.pickle"
        self.data_path   = f"{self.bids_path.directory}/{self.bids_path.basename}_{keywords['datatype']}.edf"

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

    def annotation_manager(self,raw):

        def get_annot(iannot):
            return iannot['description']

        self.alldesc = '||'.join(list(map(get_annot,raw.annotations)))

    def save_targets(self,target):

        # Logic for handling file input targets
        if os.path.exists(target):
            if target.endswith('.pickle'):
                fp          = open(target,'rb')
                target_dict = pickle.load(fp)
                fp.close()
            else:
                target_dict = {'target':target}
        else:
            target_dict = {'target':target}

        # Check for the merged descriptions. Only important for iEEG.org calls.
        if hasattr(self,'alldesc'):
            target_dict['description'] ='||'.join(self.alldesc)

        # Store the targets
        fp = open(self.target_path,"wb")
        pickle.dump(target_dict,fp)
        fp.close()

        return self.data_path,self.target_path

    def save_data_w_events(self, raw, debug=False):
        """
        Save EDF data into a BIDS structure. With events.

        Args:
            raw (_type_): MNE Raw objext.
            debug (bool, optional): Debug flag. Acts for verbosity.

        Returns:
            _type_: _description_
        """

        if self.args.backend == 'MNE':
            # Save the bids data
            try:
                write_raw_bids(bids_path=self.bids_path, raw=raw, events=self.events, event_id=self.event_mapping, allow_preload=True, format='EDF', overwrite=True, verbose=False)
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

        if self.args.backend == 'MNE':
            # Save the bids data
            try:
                write_raw_bids(bids_path=self.bids_path, raw=raw, allow_preload=True, format='EDF', verbose=False, overwrite=True)
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

        if self.args.backend == 'MNE':
            try:
                export_raw(str(self.bids_path)+f"_{itype}.edf",raw=raw,fmt='edf',physical_range=(pmin,pmax),overwrite=True,verbose=False)
                return True
            except Exception as e:
                if debug:
                    print("Raw write error: {e}")
                return False
        
    def copy_data(self,original_path,extension,itype,debug=False):

        try:
            os.system(f"cp {original_path} {str(self.bids_path)}_{itype}.{extension}")
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
    
    def update_ignore(self):
        """
        Update the ignore file to avoid CNT specific side cars.
        """

        # Define the ignore list
        ignore_list = ["**/*yasa.csv","**/*targets.pickle","**/*filetokens.dict"]

        # Uncover the bids ignore path
        ignore_path = f"{self.bids_path._root}/.bidsignore"
        
        # Check for the bids ignore file
        if not os.path.exists(ignore_path):
            
            # Add to the ignore file
            fp = open(ignore_path,'w')
            for istr in ignore_list:
                fp.write(f"{istr}\n")
            fp.close()
        else:
            
            # Get the existing list
            fp               = open(ignore_path,'r')
            previous_ignores = fp.readlines()
            previous_ignores = [istr.strip('\n') for istr in previous_ignores]
            fp.close()

            # Add to the ignore file if needed
            fp = open(ignore_path,'w')
            for istr in previous_ignores:fp.write(istr)
            for istr in ignore_list:
                if istr not in previous_ignores:
                    fp.write(f"{istr}\n")
            fp.close()

class BIDS_handler_pybids:

    def __init__(self,args):
        self.args = args

    def update_path(self,keywords):

        # Create the entities object
        entities  = {}

        # Define the required keys
        entities['subject']     = keywords['subject']
        entities['session']     = f"{keywords['session']:02d}"
        entities['run']         = f"{keywords['run']:02d}"
        entities['data_type']   = keywords['data_type']

        # Begin building the match string
        match_str = 'sub-{subject}[/ses-{session}]/{data_type}/sub-{subject}[_ses-{session}]'

        # Optional keys
        if keywords['task'] != None:
            entities['task']= keywords['task']
            match_str += '[_task-{task}]'
        if keywords['acq'] != None:
            entities['acquisition'] = keywords['acq']
            match_str += '[_acq-{acquisition}]'
        if keywords['ce'] != None:
            entities['ceagent'] = keywords['ce']
            match_str += '[_ce-{ceagent}]'

        # Add in the run number here
        match_str += '[_run-{run}]'

        # Remaining optional keys
        if keywords['modality'] != None:
            entities['modality'] = keywords['modality']
            match_str += '[_{modality}]'

        # Define the patterns for pathing    
        patterns = [match_str]

        # Set up the bids pathing
        self.bids_path = keywords['root']+build_path(entities=entities, path_patterns=patterns)

        return True