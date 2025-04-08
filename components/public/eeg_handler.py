import os 
from tqdm import tqdm

# Local import

from components.internal.BIDS_handler import *
from components.internal.data_backends import *
from components.internal.PHI_handler import *
from components.internal.observer_handler import *
from components.internal.exception_handler import *
from components.internal.nlp_token_handler import *
from components.internal.yasa_handler import *

class eeg_handler(Subject):
    """
    This class manages the methods that enable timeseries conversion to BIDS structure.
    The method 'workflow' manages the basic steps required.
    It is the subject object that maintains a list of observers. 
    These observers enable a variety of automated functionality.

    As of 03/24/25, the observers fall into the following categories:
    data observers:
        - Methods that perform any data preprocessing that need to occur before being saved.
            - By default, no preprocessing is done. But this can be modified easily by changing the behavior of components.internal.data_backends for the relevant back-end. (MNE_handler by default)
    meta observers:
        - Methods that create the required metadata for BIDS generation.
    postprocessor observers:
        - Methods that act on the complete BIDS file or BIDS dataset.
            - At present, the post processor acts on each file after generation. This can be modified by changing when notify_postprocess_observers is called in save_data method.
            - Currently we include file token creation and yasa sleep staging. But this can be changed in the attach_objects methods. 
            - Currently only used on eeg datasets. But attaching new methods to the attach_objects method in another handler will enable the same behavior.
                - Argparse can be given new keywords to modify logic for postprocessor usage.
            
    Args:
        Subject (class): Subject class that allows for linking observers to this class
    """

    def __init__(self,args):
        """
        Initialize the EEG conversion to BIDS. 
        Clean up input arguments for this use case, then create the observation objects.

        Args:
            args (Namespace): Argument parser.
        """

        # Manage input argument exceptions and then save the data
        IE        = InputExceptions()
        self.args = IE.eeg_input_exceptions(args)

        # Create the object pointers to the backend, phi, and bids library of choice
        self.BH      = BIDS_handler_MNE(args)
        self.PHI     = phi_handler()
        self.backend = return_backend(self.args.backend)

        # Get the data record of existing files within this BIDS dataset.
        self.get_data_record()

        # Create objects that interact with observers
        self.BIDS_keywords = {'root':self.args.bids_root,'datatype':None,'session':None,'subject':None,'run':None,'task':None}

    def workflow(self):
        """
        Run a workflow that downloads data from iEEG.org, creates the correct objects in memory, and saves it to BIDS format.
        """
        
        # Attach observers
        self.attach_objects()

        # Determine how to save the data
        self.get_inputs()

        # Loop over the files individually for eeg files. This option has to handle large files.
        self.event_list = []
        for fidx in range(len(self.eeg_files)):

            # Make a data validation flag. Originally we used a phi flag, but this is more general, in case some new use-case comes up to stop data getting loaded into memory.
            self.valid_data = True

            # Create objects to store info.
            # Note. This is inside the file loop since iEEG.org files can be downloaded by clip layer, making a single origin file go to many bids files.
            # If a single eeg is to be broken up, this same logic can apply here. But it could be moved outside the loop if that is an unlikely use-case.
            self.data_list  = []
            self.type_list  = []

            # Begin loading the data
            self.load_data_manager(fidx)

            # Assign events
            self.event_manager(fidx)

            # Save the data
            self.save_data(fidx)

            # Update the data records
            self.get_data_record()
            self.new_data_record = PD.concat((self.data_record,self.new_data_record))
            self.new_data_record = self.new_data_record.drop_duplicates()
            self.new_data_record = self.new_data_record.sort_values(by=['subject_number','session_number','run_number'])
            self.new_data_record.to_csv(self.data_record_path,index=False)

            # Update the bids ignore
            try:
                self.BH.update_ignore()
            except AttributeError:
                pass

    def attach_objects(self):
        """
        Attach observers here.
        Doing so within the workflow allows potential multiprocessors to see the pointers correctly.
        """

        # Create the observer objects
        self._data_observers        = []
        self._meta_observers        = []
        self._postprocess_observers = []

        ##########################
        ##### Data Observers #####
        ##########################

        # Manages how to read in and prepare data for saving to disk for the currently selected backend
        if self.args.anonymize:
            self.add_data_observer(phi_observer)
        self.add_data_observer(backend_observer)

        ##############################
        ##### Metadata Observers #####
        ##############################

        # Add a metadata observer. In this context, if data can be read in and prepared for saving to BIDS, create the proposed BIDS pathing.
        self.add_meta_observer(BIDS_observer)

        ####################################
        ##### Postprocessing Observers #####
        ####################################

        # Add any post processing scripts
        self.add_postprocessor_observer(nlp_token_observer)
        self.add_postprocessor_observer(yasa_observer)

    def get_inputs(self, multiflag=False, multiinds=None):
        """
        Create the input objects that track what files and times to download, and any relevant keywords for the BIDS process.
        For single core pulls, has more flexibility to set parameters. For multicore, we restrict it to a pre-built input_args.
        """

        # Check for an input csv to manually set entries
        if self.args.input_csv != None:
            
            # Read in the input data
            input_args = PD.read_csv(self.args.input_csv)

            # Pull out the relevant data pointers for required columns.
            self.eeg_files = list(input_args['orig_filename'].values)

            # Get the unique identifier if provided
            if 'start' in input_args.columns:
                self.start_times=list(input_args['start'].values)
            else:
                self.start_times=[self.args.start for idx in range(input_args.shape[0])]

            # Get the unique identifier if provided
            if 'duration' in input_args.columns:
                self.durations=list(input_args['duration'].values)
            else:
                self.durations=[self.args.duration for idx in range(input_args.shape[0])]

            # Get the unique identifier if provided
            if 'uid' in input_args.columns:
                self.uid_list=list(input_args['uid'].values)
            else:
                self.uid_list=[self.args.uid for idx in range(input_args.shape[0])]

            # Get the subejct number if provided
            if 'subject_number' in input_args.columns:
                self.subject_list=list(input_args['subject_number'].values)
            else:
                self.subject_list=[self.args.subject_number for idx in range(input_args.shape[0])]

            # Get the session number if provided
            if 'session_number' in input_args.columns:
                self.session_list=list(input_args['session_number'].values)
            else:
                self.session_list=[self.args.session for idx in range(input_args.shape[0])]

            # Get the run number if provided
            if 'run_number' in input_args.columns:
                self.run_list=list(input_args['run_number'].values)
            else:
                self.run_list=[self.args.run for idx in range(input_args.shape[0])]

            # Get the task if provided
            if 'task' in input_args.columns:
                self.task_list=list(input_args['task'].values)

            # Get the target if provided
            if 'target' in input_args.columns:
                self.target_list = list(input_args['target'].values)

            # Get the events if provided
            if 'event_file' in  input_args.columns:
                self.event_files = list(input_args['event_file'].values)
            else:
                self.event_files = [self.args.event_file for idx in range(input_args.shape[0])]
        else:
            # Get the required information if we don't have an input csv
            self.eeg_files    = [self.args.dataset]
            self.start_times  = [self.args.start]
            self.durations    = [self.args.duration]
            self.uid_list     = [self.args.uid_number]
            self.subject_list = [self.args.subject_number]
            self.session_list = [self.args.session]
            self.run_list     = [self.args.run]
            self.task_list    = [self.args.task]

            if self.args.target != None:
                self.target_list = [self.args.target]

            if self.args.event_file != None:
                self.event_files = [self.args.event_file]
            else:
                self.event_files = [None]

    def get_data_record(self):
        """
        Get the existing data record. This is typically 'subject_map.csv' and is used to locate data and prevent duplicate downloads.
        """
        
        # Get the proposed data record
        self.data_record_path = self.args.bids_root+self.args.data_record

        # Check if the file exists
        if os.path.exists(self.data_record_path):
            self.data_record = PD.read_csv(self.data_record_path)
        else:
            self.data_record = PD.DataFrame(columns=['orig_filename','source','creator','gendate','uid','subject_number','session_number','run_number','start_sec','duration_sec'])   

    def load_data_manager(self,file_cntr):
        """
        Loop over the eeg file list and load data. If unable to load data, or the data observers find issues, append a None to the output manifest.
        """

        # Store the filename to class instance
        self.file_name = self.eeg_files[file_cntr]

        # Load the data exists exception handler so we can avoid already downloaded data.
        DE = DataExists(self.data_record)

        # Check if we have a specific set of times for this file
        try:
            istart    = self.start_times[file_cntr]
            iduration = self.durations[file_cntr]
        except TypeError:
            istart    = None
            iduration = None

        if DE.check_default_records(self.eeg_files[file_cntr],istart,iduration,overwrite=self.args.overwrite):
            
            # Load data using the appropriate backend
            self.load_data(self.file_name)
                    
            # If successful, notify data observer. Else, add a skip
            if self.success_flag:

                # Data object is a way to package data relevant to whatever workflow you want to send to a backend. Named and packaged like this 
                # so the listener can send an expected object to different backends.
                self.data_object = (self.data,self.channels,self.fs,self.annotations)
                self.notify_data_observers()
            else:
                print(f"Skipping {self.file_name}.")
                self.data_list.append(None)
                self.type_list.append(None)
        else:
            print(f"Skipping {self.file_name}.")
            self.data_list.append(None)
            self.type_list.append(None)

    def load_data(self,infile):
        """
        Load the eeg data into memory and some associated objects. This is so we can make sure it is readable, and any preprocessing
        of the data can take place. (i.e. Cleaning channel names, removing artifacts, etc.) Currently we do not do any preprocessing,
        but leave this method in so it is easier to perform. Suggested approach would be to add a listener to the data observer.

        Args:
            infile (str): Filepath to eeg data
        """

        self.data, self.channels, self.fs, self.annotations, self.success_flag,error_info = self.backend.read_data(infile)
        if self.success_flag == False and self.args.debug:
            print(f"Load error {error_info}")

    def event_manager(self,fidx):
        """
        Either read in events tsv, events dictionary, or grab from the back-end. Not yet implemented until consensus on code usage in the lab

        Args:
            fidx (int): File index
        """

        # Manage different event read in scenarios
        if self.event_files[fidx] != None:
            if self.event_files[fidx].endswith('.csv'):
                events = PD.read_csv(self.event_files[fidx])
            elif self.event_files[fidx].endswith('.tsv'):
                events = PD.read_csv(self.event_files[fidx],delimiter='\t')
        elif self.args.event_from_backend:
            # Read in events using the backends built-in method. Like MNE event finder. Not yet implemented
            events = None
        else:
            events = None

        # Store to event list
        self.event_list.append(events)

    def save_data(self,fidx):
        """
        Notify the BIDS code about data updates and save the results when possible.
        """
        
        # Loop over the data, assign keys, and save
        self.new_data_record = self.data_record.copy()
        for idx,iraw in enumerate(self.data_list):
            if iraw != None:

                # Define start time and duration. Can differ for different filetypes
                # May not exist for a raw eeg transfer, so add a None outcome.
                try:
                    istart    = self.start_times[fidx]
                    iduration = self.durations[fidx]
                except TypeError:
                    istart    = None
                    iduration = None

                # Update keywords
                self.keywords = {'filename':self.eeg_files[fidx],'root':self.args.bids_root,'datatype':self.type_list[idx],
                                 'session':self.session_list[fidx],'subject':self.subject_list[fidx],'run':self.run_list[fidx],
                                 'task':'rest','fs':iraw.info["sfreq"],'start':istart,'duration':iduration,'uid':self.uid_list[fidx]}
                self.notify_metadata_observers(self.args.backend)

                # Save the data
                print(f"Converting {self.eeg_files[fidx]} to BIDS...")
                if self.event_list[fidx] == None:
                    success_flag = self.BH.save_data_wo_events(iraw, debug=self.args.debug)
                else:
                    self.events = self.event_list[fidx]
                    success_flag = self.BH.save_data_w_events(iraw, debug=self.args.debug)

                if not success_flag and self.args.copy_eeg:
                    print(f"Copying {self.eeg_files[fidx]} to BIDS...")
                    success_flag = self.BH.copy_data(self.eeg_files[fidx],'eeg',self.type_list[idx],debug=self.args.debug)

                # Copy the data path to this instance
                self.data_path = self.BH.data_path

                # If the data wrote out correctly, update the data record
                if success_flag:
                    # Save the target info
                    try:
                        self.BH.annotation_manager(iraw)
                        self.target_path = self.BH.save_targets(self.target_list[fidx])
                    except Exception as e:
                        if self.args.debug:
                            print(f"Target Writout error: {e}")
                    
                    # Add the datarow to the records
                    self.current_record  = self.BH.make_records('eeg_file')
                    self.new_data_record = PD.concat((self.new_data_record,self.current_record))

                    # Run post processing
                    self.notify_postprocess_observers()
                else:
                    if self.args.error_code:
                        sys.exit(1)
            else:
                if self.args.error_code:
                    sys.exit(1)