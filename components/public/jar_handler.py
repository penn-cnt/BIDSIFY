import os 
import time
import getpass

# Local import
from components.internal.BIDS_handler import *
from components.internal.observer_handler import *
from components.internal.exception_handler import *
from components.internal.data_backends import *

class jar_handler(Subject):

    def __init__(self,args):

        # Save the input objects
        self.args = args

        # Create the object pointers
        self.BH      = BIDS_handler(args)
        self.backend = return_backend(args.backend)

        # Get the data record
        self.get_data_record()

        # Create objects that interact with observers
        self.data_list     = []
        self.type_list     = []
        self.BIDS_keywords = {'root':self.args.bids_root,'datatype':None,'session':None,'subject':None,'run':None,'task':None}

    def workflow(self):
        """
        Run a workflow that downloads data from iEEG.org, creates the correct objects in memory, and saves it to BIDS format.
        """

        # Attach observers
        self.attach_objects()

        # Determine what files to download and to where
        self.get_inputs()

        # Begin downloading the data
        self.convert_data_manager()

        # Save the data
        self.save_data()

        # Save the data record
        self.new_data_record = self.new_data_record.sort_values(by=['subject_number','session_number','run_number'])
        self.new_data_record.to_csv(self.data_record_path,index=False)

        # Remove if debugging
        #if self.args.debug:
        #    os.system(f"rm -r {self.args.bids_root}*")

    def attach_objects(self):
        """
        Attach observers here so we can have each multiprocessor see the pointers correctly.
        """

        # Create the observer objects
        self._meta_observers = []
        self._data_observers = []

        # Attach observers
        self.add_meta_observer(BIDS_observer)
        self.add_data_observer(backend_observer)

    def get_data_record(self):
        """
        Get the data record. This is typically 'subject_map.csv' and is used to locate data and prevent duplicate downloads.
        """
        
        # Get the proposed data record
        self.data_record_path = self.args.bids_root+self.args.data_record

        # Check if the file exists
        if os.path.exists(self.data_record_path):
            self.data_record = PD.read_csv(self.data_record_path)
        else:
            self.data_record = PD.DataFrame(columns=['orig_filename','source','creator','gendate','uid','subject_number','session_number','run_number','start_sec','duration_sec'])   

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
            self.jar_files = list(input_args['orig_filename'].values)

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
        else:
            # Get the required information if we don't have an input csv
            self.jar_files   = [self.args.dataset]
            self.start_times = [self.args.start]
            self.durations   = [self.args.duration]

            # Get the information that can be inferred
            if self.args.uid_number != None:
                self.uid_list = [self.args.uid_number]
            
            if self.args.subject_number != None:
                self.subject_list = [self.args.subject_number]
            
            if self.args.session != None:
                self.session_list = [self.args.session]
            
            if self.args.run != None:
                self.run_list = [self.args.run]
            
            if self.args.task != None:
                self.task_list = [self.args.task]

            if self.args.target != None:
                self.target_list = [self.args.target]

    def convert_data_manager(self):

        # Load the data exists exception handler so we can avoid already downloaded data.
        DE = DataExists(self.data_record)

        # Loop over the requested data
        for idx in range(len(self.jar_files)):

            # Check if we have a specific set of times for this file
            try:
                istart    = self.start_times[idx]
                iduration = self.durations[idx]
            except TypeError:
                istart    = None
                iduration = None

            if DE.check_default_records(self.jar_files[idx],istart,iduration,overwrite=self.args.overwrite):

                # Run the java script here
                # Reference the orig_filename to the mef folder
                # java.run()

                # Look for data quality flags from java
                #java.pass_fail()
                # if pass then continue
                # if fail: self.success_flag=False

                # Loop over channel files

                self.read_jar_data(self.jar_files[idx])
                        
                # If successful, notify data observer. Else, add a skip
                if self.success_flag:
                    self.notify_data_observers()
                else:
                    self.data_list.append(None)
            else:
                print(f"Skipping {self.jar_files[idx]}.")
                self.data_list.append(None)

    def read_jar_data(self,data_file):

        try:

            header_file   = data_file.split('values_data')[0]+"header_info.csv"
            self.data     = PD.read_csv(data_file).values
            #self.channels = PD.read_csv(header_file)['Channel Name'].values
            #self.fs       = PD.read_csv(header_file)['Sampling Frequency'].values
            self.channels  = ['Sin 10Hz']
            self.fs        = 800
            self.success_flag = True
        except Exception as e:
            self.success_flag = False
            if self.args.debug:
                print(f"Load error {e}")

    def save_data(self):
        """
        Notify the BIDS code about data updates and save the results when possible.
        """
        
        # Loop over the data, assign keys, and save
        self.new_data_record = self.data_record.copy()
        for idx,iraw in enumerate(self.data_list):
            if iraw != None:

                # Define start time and duration. Can differ for different filetypes
                # May not exist for a raw file transfer, so add a None outcome.
                try:
                    istart    = self.start_times[idx]
                    iduration = self.durations[idx]
                except TypeError:
                    istart    = None
                    iduration = None

                # Update keywords
                self.keywords = {'filename':self.jar_files[idx],'root':self.args.bids_root,'datatype':self.type_list[idx],
                                 'session':self.session_list[idx],'subject':self.subject_list[idx],'run':self.run_list[idx],
                                 'task':'rest','fs':iraw.info["sfreq"],'start':istart,'duration':iduration,'uid':self.uid_list[idx]}
                self.notify_metadata_observers()

                # Save the data without events until a future release
                print(f"Converting {self.jar_files[idx]} to BIDS...")
                success_flag = self.BH.save_data_wo_events(iraw, debug=self.args.debug)

                # If the data wrote out correctly, update the data record
                if success_flag:
                    # Save the target info
                    try:
                        self.BH.save_targets(self.target_list[idx])
                    except:
                        pass

                    # Add the datarow to the records
                    self.current_record  = self.BH.make_records('jar_file')
                    self.new_data_record = PD.concat((self.new_data_record,self.current_record))