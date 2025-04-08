import re
import mne
import numpy as np
import pandas as PD
import nibabel as nib
from mne.io import read_raw_edf
from mne.io.constants import FIFF

# Local Imports
from components.internal.observer_handler import *

def return_backend(user_request='mne'):
    if user_request.lower() == 'mne':
        return MNE_handler()
    elif user_request == 'nibabel':
        return nibabel_handler()

class backend_observer(Observer):
    """
    Data observer listening for new data that is successfully loaded into memory.
    Kicks off workflows in a backend to perform any needed steps to get the data ready for saving.

    Args:
        Observer (_type_): _description_
    """

    def listen_data(self):

        if self.valid_data:
            # Send the data through the backend handler
            idata,itype = self.backend.workflow(self.args,self.data_object)

            # Add objects to the shared list
            self.data_list.append(idata)
            self.type_list.append(itype)
        else:
            self.data_list.append(None)
            self.type_list.append(None)

class MNE_handler:
    """
    Back-end handler using MNE as its core component. It is meant to read data into memory and on a succesful
    data load, perform any required steps for saving the data into BIDS. For example, MNE requires an info object
    to be attached to a raw data object before it can be exported to BIDS.

    Required methods:
        - read_data (extension point): Method for reading data into memory using MNE. Checks file extension to figure out
        the right MNE method to use for the input timeseries format.
        - workflow: Method that controls the flow of how data is prepared for export.
    """

    def __init__(self):
        pass

    def read_data(self,inpath):
        """
        Read data into memory. Checks for file extension of the path to determine the correct methodology.
        Extension point for the mne_handler.

        Args:
            inpath (str, filepath): Filepath to data to read in.

        Returns:
            tuple: data, channels, sampling frequency, annotations, Success flag, Any potential error messages
        """
        
        if inpath.endswith('.edf'):
            try:
                raw = read_raw_edf(inpath,verbose=False)
                data         = raw.get_data().T
                channels     = raw.ch_names
                fs           = raw.info.get('sfreq')
                annotations  = raw.annotations
                success_flag = True
                return data, channels, fs, annotations, success_flag, None
            except Exception as e:
                return None,None,None,None,False,e

    def workflow(self,args,data_object):
        """
        Workflow for MNE data preparation.

        Args:
            args (Namespace): Entry point arguments.
            data_object (tuple): Tuple with the raw data, channels, sampling frequency, and annotations.

        Returns:
            tuple: Tuple of the MNE raw object and the best guess for the data type (i.e ieeg,seeg, etc.)
        """

        # Save the inputs to class instance
        self.args     = args
        self.indata   = data_object[0]
        self.channels = data_object[1]
        self.fs       = data_object[2]
        self.annots   = data_object[3]

        # Prepare the data according to the backend
        try:
            passflag = self.get_channel_type()
            if passflag:
                self.make_info()
                self.make_raw()
                self.attach_annotations()
            else:
                self.irow = None
                self.bids_datatype = None
        except Exception as e:
            if self.args.debug:
                print(f"Load error {e}")

        # Anonymize if requested
        if self.args.anonymize:
            self.iraw = self.iraw.anonymize()

        # Return raw to the list of raws being tracked by the Subject class
        return self.iraw,self.bids_datatype

    def make_raw(self):
        """
        Create the MNE raw object.
        """

        idata     = np.nan_to_num(self.indata.T, )
        self.iraw = mne.io.RawArray(idata, self.data_info, verbose=False)
        self.iraw.set_channel_types(self.channel_types.type)
    
    def make_info(self):
        """
        Create the info object for MNE that defines the channels and their relevant units.
        """

        self.data_info = mne.create_info(ch_names=list(self.channels), sfreq=self.fs, verbose=False)
        for idx,ichannel in enumerate(self.channels):
            if self.channel_types.loc[ichannel]['type'] in ['seeg','eeg']:
                self.data_info['chs'][idx]['unit'] = FIFF.FIFF_UNIT_V

    def attach_annotations(self):

        try:
            # Make a new annotation object to ensure no measurement date issue mismatches
            new_annot = mne.Annotations(onset=self.annots.onset,duration=self.annots.duration,description=self.annots.description)

            # Set annotation to raw object
            self.iraw.set_annotations(new_annot)
        except:
            pass

    def get_channel_type(self, threshold=15):
        """
        Attempt to figure out the recording type for a given channel based on its input naming.

        Args:
            threshold (int, optional): Maximum number of leads to define between typical scalp and ECOG electrodes. Defaults to 15.

        Returns:
            bool flag: Boolean flag for whether a reasonable match was made or not. If failure, use a default electrode type set by arguments.
        """

        # Define the expression that gets lead info
        regex = re.compile(r"(\D+)(\d+)")

        # Get the outputs of each channel
        try:
            channel_expressions = [regex.match(ichannel) for ichannel in self.channels]

            # Make the channel types
            self.channel_types = []
            for (i, iexpression), channel in zip(enumerate(channel_expressions), self.channels):
                if iexpression == None:
                    if channel.lower() in ['fz','cz']:
                        self.channel_types.append('eeg')
                    else:
                        self.channel_types.append('misc')
                else:
                    lead = iexpression.group(1)
                    contact = int(iexpression.group(2))
                    if lead.lower() in ["ecg", "ekg"]:
                        self.channel_types.append('ecg')
                    elif lead.lower() in ['c', 'cz', 'cz', 'f', 'fp', 'fp', 'fz', 'fz', 'o', 'p', 'pz', 'pz', 't']:
                        self.channel_types.append('eeg')
                    elif "NVC" in iexpression.group(0):  # NeuroVista data 
                        self.channel_types.append('eeg')
                        self.channels[i] = f"{channel[-2:]}"
                    elif lead.lower() in ['a']:
                        self.channel_types.append('misc')
                    else:
                        self.channel_types.append(1)

            # Do some final clean ups based on number of leads
            lead_sum = 0
            for ival in self.channel_types:
                if isinstance(ival,int):lead_sum+=1
            if self.args.ch_type == None:
                if lead_sum > threshold:
                    remaining_leads = 'ecog'
                else:
                    remaining_leads = 'seeg'
            else:
                remaining_leads = self.args.ch_type
            for idx,ival in enumerate(self.channel_types):
                if isinstance(ival,int):self.channel_types[idx] = remaining_leads
            self.channel_types = np.array(self.channel_types)
        except:
            if self.args.ch_type != None:
                self.channel_types = np.array([self.args.ch_type for ichannel in self.channels])
            else:
                return False

        # Make the dictionary for mne
        self.channel_types = PD.DataFrame(self.channel_types.reshape((-1,1)),index=self.channels,columns=["type"])
        
        # Get the best guess datatype to send to bids writer
        raw_datatype = self.channel_types['type'].mode().values[0]
        
        # perform some common mappings to the bids keywords
        if raw_datatype == 'ecog':
            datatype = 'ieeg'
        elif raw_datatype == 'seeg':
            datatype = 'ieeg'
        else:
            datatype = raw_datatype

        # Store the data type to use for write out
        self.bids_datatype = datatype
        return True

class nibabel_handler:
    """
    Back-end handler using Nibabel as its core component. It is meant to read data into memory and on a succesful
    data load, perform any required steps for saving the data into BIDS. For example, MNE requires an info object
    to be attached to a raw data object before it can be exported to BIDS.

    Required methods:
        - read_data (extension point): Method for reading data into memory using Nibabel.
        - workflow: Method that controls the flow of how data is prepared for export.
    """

    def __init__(self):
        pass

    def read_data(self,inpath):
        """
        Read data into memory. Checks for file extension of the path to determine the correct methodology.
        Extension point for the nibabel_handler.

        Args:
            inpath (str, filepath): Filepath to data to read in.

        Returns:
            tuple: data, Success flag, Any potential error messages
        """

        if inpath.endswith('.nii'):
            try:
                data = nib.load(inpath)
                return data,True,None
            except Exception as e:
                return None,False,e
        
    def workflow(self,args,data_object):

        # Save the inputs to class instance
        self.args = args
        self.data = data_object[0]
        
        return self.data,None