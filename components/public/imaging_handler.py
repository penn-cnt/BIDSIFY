import os 
from tqdm import tqdm

# Local import

from components.internal.BIDS_handler import *
from components.internal.data_backends import *
from components.internal.observer_handler import *
from components.internal.exception_handler import *
from components.internal.nlp_token_handler import *
from components.internal.yasa_handler import *
from components.internal.PHI_handler import *

class imaging_handler(Subject):
    """
    This class manages the methods that enable imaging conversion to BIDS structure.
    The method 'workflow' manages the basic steps required.
    It is the subject object that maintains a list of observers. 
    These observers enable a variety of automated functionality.

    As of 03/24/25, the observers fall into the following categories:
    data observers:
        - Methods that perform any data preprocessing that need to occur before being saved.
            - By default, no preprocessing is done. But this can be modified easily by changing the behavior of components.internal.data_backends for the relevant back-end. (MNE_handler by default)
            - For images, this would be the place to add de-facing or similar methods.
    meta observers:
        - Methods that create the required metadata for BIDS generation.
    postprocessor observers:
        - Methods that act on the complete BIDS file or BIDS dataset.
            - At present, the post processor acts on each file after generation. This can be modified by changing when notify_postprocess_observers is called in save_data method.
            - Currently we include file token creation and yasa sleep staging. But this can be changed in the attach_objects methods. 
            - Currently only used on EDF datasets. But attaching new methods to the attach_objects method in another handler will enable the same behavior.
                - Argparse can be given new keywords to modify logic for postprocessor usage.
            
    Args:
        Subject (class): Subject class that allows for linking observers to this class
    """

    def __init__(self,args):
        """
        Initialize the EDF conversion to BIDS. 
        Clean up input arguments for this use case, then create the observation objects.

        Args:
            args (Namespace): Argument parser.
        """

        # Read or create datalake object
        self.imaging_keys = ['data_type', 'scan_type', 'modality', 'task', 'acq', 'ce']
        if args.datalake != None:
            self.datalake = pickle.load(open(args.datalake,'rb'))['HUP']
        else:
            self.datalake = {}

        # Manage input argument exceptions and then save the data
        IE        = InputExceptions()
        self.args = IE.imaging_input_exceptions(args)

        # Create the object pointers to the backend and bids library of choice
        self.BH      = BIDS_handler_pybids(args)
        self.PHI     = phi_handler()
        self.backend = return_backend(self.args.backend)

        # Create the object pointers to the backend and bids library of choice.
        # NOTE: Not implemented for imaging. Need to figure out the best record for imaging data to conform with EEG data.
        # The base EEG record should be fine, but want to confirm we dont need more imaging metadata to properly tag data.
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

        # Loop over the files individually for edf files. This option has to handle large files.
        for fidx in range(len(self.imaging_files)):

            # Make a data validation flag. Originally we used a phi flag, but this is more general, in case some new use-case comes up to stop data getting loaded into memory.
            self.valid_data = True

            # Create objects to store info
            self.data_list  = []
            self.type_list  = []

            # Begin downloading the data
            self.load_data_manager(fidx)

            # Save the data
            self.save_data(fidx)

    def attach_objects(self):
        """
        Attach observers here so we can have each multiprocessor see the pointers correctly.
        """

        # Create the observer objects
        self._meta_observers        = []
        self._data_observers        = []
        self._postprocess_observers = []


        ##########################
        ##### Data Observers #####
        ##########################
        # Note. This is where you might want to add preprocessors.
        if self.args.deface:
            print("Defacing not yet implemented. This is a placeholder function.")
            print("Please check the documents/SOP/BIDSIFY.png to learn where the proper extension method would be for this behavior.")

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
        # This would be the place to put something like reconstruction, etc.

    def get_inputs(self, multiflag=False, multiinds=None):
        """
        Create the input objects that track what files and times to download, and any relevant keywords for the BIDS process.
        For single core pulls, has more flexibility to set parameters. For multicore, we restrict it to a pre-built input_args.
        """

        # Check for an input csv to manually set entries
        self.skipcheck = True
        if self.args.input_csv != None:
            
            # Read in the input data
            input_args = PD.read_csv(self.args.input_csv)

            # Convert nan to none
            input_args = input_args.replace({np.nan:None})

            # Pull out the relevant data pointers for required columns.
            self.imaging_files = list(input_args['orig_filename'].values)

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

            # Check for the imaging keywords
            if 'data_type' in input_args.columns:
                self.data_type_list = list(input_args['data_type'].values)
            else:
                ival                = self.args.imaging_data_type
                self.data_type_list = [ival for idx in range(input_args.shape[0])]
                if ival == None: self.skipcheck=False

            if 'scan_type' in input_args.columns:
                self.scan_type_list = list(input_args['scan_type'].values)
            else:
                ival                = self.args.imaging_scan_type
                self.scan_type_list = [ival for idx in range(input_args.shape[0])]
                if ival == None: self.skipcheck=False

            if 'modality' in input_args.columns:
                self.modality_list = list(input_args['modality'].values)
            else:
                ival               = self.args.imaging_modality
                self.modality_list = [ival for idx in range(input_args.shape[0])]
                if ival == None: self.skipcheck=False

            if 'task' in input_args.columns:
                self.task_list = list(input_args['task'].values)
            else:
                ival           = self.args.imaging_task
                self.task_list = [ival for idx in range(input_args.shape[0])]
                if ival == None: self.skipcheck=False

            if 'acq' in input_args.columns:
                self.acq_list = list(input_args['acq'].values)
            else:
                ival          = self.args.imaging_acq
                self.acq_list = [ival for idx in range(input_args.shape[0])]
                if ival == None: self.skipcheck=False

            if 'ce' in input_args.columns:
                self.ce_list = list(input_args['ce'].values)
            else:
                ival         = self.args.imaging_ce
                self.ce_list = [ival for idx in range(input_args.shape[0])]
                if ival == None: self.skipcheck=False

        else:
            # Get the required information if we don't have an input csv
            self.imaging_files    = [self.args.dataset]
            self.uid_list       = [self.args.uid_number]
            self.subject_list   = [self.args.subject_number]
            self.session_list   = [self.args.session]
            self.run_list       = [self.args.run]
            self.data_type_list = [self.args.imaging_data_type]
            self.scan_type_list = [self.args.imaging_scan_type]
            self.modality_list  = [self.args.imaging_modality]
            self.task_list      = [self.args.task]
            self.acq_list       = [self.args.imaging_acq]
            self.ce_list        = [self.args.imaging_ce]

            combined_args = [self.args.imaging_data_type,self.args.imaging_scan_type,self.args.imaging_modality,self.args.task,self.args.imaging_acq,self.args.imaging_ce]
            if any([ival==None for ival in combined_args]):
                self.skipcheck = False

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
        Loop over the ieeg file list and download data. If annotations, does a first pass to get annotation layers and times, then downloads.
        """

        # Load the data exists exception handler so we can avoid already downloaded data.
        DE = DataExists(self.data_record)

        if DE.check_default_records(self.imaging_files[file_cntr],None,None,overwrite=self.args.overwrite):
            self.load_data(self.imaging_files[file_cntr])
                    
            # Notify data observer if successful, otherwise pad a None to the output manifest
            if self.success_flag:
                # Data object is a way to package data relevant to whatever workflow you want to send to a backend. Named and packaged like this so the listener can send
                # an expected object to different backends.
                self.data_object = (self.data,)
                self.notify_data_observers()
            else:
                self.data_list.append(None)
                self.type_list.append(None)
        else:
            print(f"Skipping {self.imaging_files[file_cntr]}.")
            self.data_list.append(None)
            self.type_list.append(None)

    def load_data(self,infile):
        """
        Load the imaging data into memory and any associated objects. This is so we can make sure it is readable, and any preprocessing
        of the data can take place. Currently we do not do any preprocessing, but leave this method in so it is easier to perform.
        Suggested approach would be to add a listener to the data observer.

        Args:
            infile (str): Filepath to imaging data
        """

        self.data,self.success_flag,error_info = self.backend.read_data(infile)
        if self.success_flag == False and self.args.debug:
            print(f"Load error {error_info}")

    def save_data(self,fidx):
        """
        Notify the BIDS code about data updates and save the results when possible.
        """
        
        # Loop over the data, assign keys, and save
        self.new_data_record = self.data_record.copy()
        for idx,idata in enumerate(self.data_list):
            if idata != None:

                # Update keywords
                self.keywords = {'filename':self.imaging_files[fidx],'root':self.args.bids_root,'uid':self.uid_list[fidx],
                                 'subject':self.subject_list[fidx],'session':self.session_list[fidx],'run':self.run_list[fidx],
                                 'data_type':self.data_type_list[fidx],'scan_type':self.scan_type_list[fidx],'modality':self.modality_list[fidx],
                                 'task':self.task_list[fidx],'acq':self.acq_list[fidx],'ce':self.ce_list[fidx]}
                
                # get the protocol name
                json_path     = self.imaging_files[fidx].split(".ni")[0]+'.json'
                self.metadata = json.load(open(json_path,'r'))
                self.series   = self.metadata["ProtocolName"].lower()

                # Notify metadata observer
                self.notify_metadata_observers(self.args.backend)
                
                # Save is a path was successfully created
                if self.success_flag:
                    self.BH.save_data(idata)
            else:
                if self.args.error_code:
                    sys.exit(1)