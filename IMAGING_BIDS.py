import re
import os
import glob
import json
import shutil
import pickle
import argparse
import datetime
import numpy as np
from sys import exit
from pathlib import Path as Pathlib
from prettytable import PrettyTable,ALL

# Pybids imports
from bids import BIDSLayout
from bids.layout.writing import build_path

class prepare_imaging:

    def __init__(self,args):
        self.args             = args
        self.newflag          = False
        self.lakekeys         = ['data_type', 'scan_type', 'modality', 'task', 'acq', 'ce']
        self.protocol_counter = {}

    def workflow(self):
        """
        Workflow to turn a flat folder of imaging data to BIDS
        """

        # get json paths
        self.get_filepaths()
        
        # Load the datalake
        self.load_datalake()

        # Make the dataset description
        self.make_description()

        # Infer session labels as needed
        if self.args.session == None:
            self.infer_sessions()

        # Loop over the files
        for fcnt,ifile in enumerate(self.json_files):
            
            # Open the metadata
            self.metadata = json.load(open(ifile,'r'))
            
            # get the protocol name
            self.series = self.metadata["ProtocolName"].lower()

            # Ask the user if we should move this file
            while True:
                print(f"\nCurrent File ({fcnt+1} out of {len(self.json_files)}): {ifile}")
                print(f"Current protocol name: {self.series}")
                print(f"=============")

                # Ask if we should move this file
                continueflag = input(f"Create BIDS data for this file (Yy/Nn)? ")
                if continueflag.lower() in ['y','n']:
                    break

            # If requested, create the keywords and proceed
            if continueflag.lower() == 'y':
                while True:

                    # get the appropriate keywords
                    if self.series in self.keys:
                        self.proposed_keys = self.datalake[self.series]
                    else:
                        self.proposed_keys = {}

                    # Check if we should use this bids keywords
                    print(f"\nCurrent proposed keys: {self.proposed_keys}")
                    keyflag = input(f"Use current keyword set (Yy/Nn)? ")
                    if keyflag.lower() == 'y':
                        break
                    elif keyflag == 'n':
                        self.acquire_keys(self.series)
                
                # Keep count of how many times we've used this protocol
                if self.series not in self.protocol_counter.keys():
                    self.protocol_counter[self.series] = 1
                else:
                    self.protocol_counter[self.series] += 1

                # Save the results
                self.save_data(ifile,self.proposed_keys)

        # Update data lake as needed
        self.update_datalake()

    def infer_sessions(self):

        # Loop over the files and get the unique sessions
        pattern = r'_(\d{14})(_|\.?)'
        dates   = []
        dtimes  = []
        for ifile in self.json_files:
            # Get the relevant substring
            match  = re.search(pattern, ifile)
            substr = match.group(1)[:8]
            year   = int(substr[:4])
            month  = int(substr[4:6])
            day    = int(substr[6:])
            dates.append(int(substr))
            dtimes.append(datetime.date(year,month,day))
        
        # Initialize the session map
        self.session_map = {}

        # Case statements of how to handle date time generation
        if self.args.dateshift != None:
            for idx,ifile in enumerate(self.json_files):
                
                # For a simple mapping by 
                newtime = dtimes[idx]-datetime.timedelta(self.args.dateshift)
                self.session_map[ifile] = newtime.strftime('%Y%m%d')
        else:
            # Get the unique sorted options
            udates = np.sort(np.unique(dates))
            for idx,ifile in enumerate(self.json_files):
                
                # For a simple mapping by 
                session_index = np.where(udates==dates[idx])[0][0]
                self.session_map[ifile] = f"{session_index+1:02d}"

    def make_description(self):

        dataset_description = {
            'Name': 'Your Dataset Name',
            'BIDSVersion': '1.6.0',
            'Description': 'Description of your dataset',
            'License': 'License information'
            }

        # Define the output path
        description_path = f"{self.args.bidsroot}dataset_description.json"
        
        # Save the dataset description as JSON
        if not os.path.exists(description_path):
            with open(description_path, 'w') as f:
                json.dump(dataset_description, f, indent=4)

    def update_datalake(self):

        # Ask if the user wants to save the updated datalake
        if self.newflag:
            flag = input("Save the new datalake entires (Yy/Nn)? ")
            if flag.lower() == 'y':
                newpath = input("Provide a new filename: ")
                outlake = {'HUP':self.datalake}
                pickle.dump(outlake,open(newpath,'wb'))

    def get_filepaths(self):
        # Find all the json files in the flat data folder
        self.json_files = glob.glob(f"{self.args.dataset}*json")

    def load_datalake(self):

        if os.path.exists(self.args.datalake):
            # Open the datalake and store the protocol name keys to selkf
            self.datalake = pickle.load(open(self.args.datalake,'rb'))['HUP']
            self.keys     = np.array(list(self.datalake.keys()))
        else:
            self.datalake = {}
            self.keys     = np.array([])

    def acquire_keys(self,iprotocol):
        """
        Acquire keys from the user for the current protocol name
        """

        # Alert code that we updated the datalake
        self.newflag = True

        # Make the output object and query keys
        output = {}

        # Get new inputs
        print(f"Please provide information for '{iprotocol}'")
        for ikey in self.lakekeys:
            if ikey == 'data_type':
                while True:
                    newval = input("    Data Type (Required): ")
                    if newval != '':
                        break
            else:
                newval = input(f"    {ikey} (''=None): ")
            if newval == '':
                newval = None
            output[ikey] = newval
    
        # Update the datalake
        self.datalake[iprotocol] = output
        self.keys = np.array(list(self.datalake.keys()))

    def save_data(self,ifile,bidskeys):

        # Update keywords
        entities  = {}

        # Define the required keys
        entities['subject'] = self.args.subject
        entities['run']     = f"{self.protocol_counter[self.series]:02d}"
        
        # Check for undefined data type
        datatype = bidskeys['data_type']
        if type(datatype) != str:
            print(ifile)
            exit()
        entities['datatype'] = bidskeys['data_type']

        # Get the session label
        if self.args.session != None:
            entities['session'] = self.args.session
        else:
            try:
                prefix_dict = json.load(open(self.args.device_to_session,'r'))
                prefix      = prefix_dict[bidskeys['scan_type']]
            except:
                prefix = 'preprocessor'
            entities['session'] = f"{prefix}{self.session_map[ifile]}"

        # Begin building the match string
        match_str = 'sub-{subject}[/ses-{session}]/{datatype}/sub-{subject}[_ses-{session}]'

        # Optional keys
        if type(bidskeys['task']) == str or bidskeys['task'] != None:
            entities['task']        = bidskeys['task']
            match_str += '[_task-{task}]'
        if type(bidskeys['acq']) == str or not bidskeys['acq'] != None:
            entities['acquisition'] = bidskeys['acq']
            match_str += '[_acq-{acquisition}]'
        if type(bidskeys['ce']) == str or not bidskeys['ce'] != None:
            entities['ceagent'] = bidskeys['ce']
            match_str += '[_ce-{ceagent}]'

        # Add in the run number here
        match_str += '[_run-{run}]'

        # Remaining optional keys
        if type(bidskeys['modality']) == str or not bidskeys['modality'] != None:
            entities['modality'] = bidskeys['modality']
            match_str += '[_{modality}]'

        # Define the patterns for pathing    
        patterns = [match_str]

        # Set up the bids pathing
        bids_path = self.args.bidsroot+build_path(entities=entities, path_patterns=patterns)

        # Make the folder to save to
        rootpath = '/'.join(bids_path.split('/')[:-1])
        Pathlib(rootpath).mkdir(parents=True, exist_ok=True)
        
        # Copy the different data files over
        root_file     = '.'.join(ifile.split('.')[:-1])
        current_files = glob.glob(f"{root_file}*")
        for jfile in current_files:
            extension = jfile.split('.')[-1]  
            shutil.copyfile(jfile, f"{bids_path}.{extension}")

        # Create a new BIDSLayout object
        layout = BIDSLayout(args.bidsroot)

        # Save the bids layout
        output_path = os.path.join(args.bidsroot, 'dataset_description.json')
        with open(output_path, 'r') as f:
            existing_data = json.load(f)
        json_output = layout.to_df().to_dict()
        merged_data = {**existing_data, **json_output}
    
        # Save the updated data back to the JSON file
        with open(output_path, 'w') as f:
            json.dump(merged_data, f, indent=4)

if __name__ == '__main__':

    # Command line options needed to obtain data.
    parser   = argparse.ArgumentParser()
    parser.add_argument('--dataset', help='Input path to the folder containing niftii files.')
    parser.add_argument('--bidsroot', required=True, help='Output path to the BIDS root directory.')
    parser.add_argument('--datalake', help='Output path to the bids datalake for image naming.',default="./datalakes/HUP_BIDS_DATALAKE.pickle")
    parser.add_argument('--subject', required=True, help='Subject label.')
    parser.add_argument('--session', help='Session label. If blank, try to infer from filename.')
    parser.add_argument('--run', default=1, help='Run label.')
    parser.add_argument('--dateshift', type=int, help='Optional value to use to date shift files.')
    parser.add_argument('--device_to_session', type=str, help='Optional file. Maps device type to specific session label. (i.e. MR->preimplant)')
    args = parser.parse_args()

    # Minor cleanuo
    if args.dataset[-1] != '/':args.dataset += '/'
    if args.bidsroot[-1] != '/':args.bidsroot += '/'

    # Prepare data for BIDS work
    PI = prepare_imaging(args)
    PI.workflow()