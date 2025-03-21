import re
import os
import time
import uuid
import getpass
import numpy as np
import multiprocessing
from time import sleep
from typing import List
import ieeg.ieeg_api as IIA
from ieeg.auth import Session
from requests.exceptions import ReadTimeout as RTIMEOUT

# Local import
from components.internal.BIDS_handler import *
from components.internal.observer_handler import *
from components.internal.exception_handler import *
from components.internal.data_backends import *

class ieeg_handler(Subject):

    def __init__(self,args):

        # Save the input objects
        self.args = args

        # Create the object pointers
        self.BH      = BIDS_handler_MNE(args)
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
        
        # Get credentials
        self.get_password()

        # Manage mutltithreading requests
        if not self.args.multithread:

            # Make a unique id for this core
            self.unique_id = uuid.uuid4()

            # Attach observers
            self.attach_objects()

            # Determine what files to download and to where
            self.get_inputs()

            # Begin downloading the data
            self.download_data_manager()

            # Save the results
            if not self.args.save_raw:
                self.save_data()
            else:
                self.save_rawdata()

            # Save the data record
            self.new_data_record = self.new_data_record.sort_values(by=['subject_number','session_number','run_number'])
            self.new_data_record.to_csv(self.data_record_path,index=False)
        else:
            self.multipull_manager()

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

    #########################################
    ####### Multiprocessing functions #######
    #########################################

    def multipull_manager(self):

        # Make sure we have an input csv for multithreading. By default, this should be used for large data pulls.
        if self.args.input_csv == None:
            raise Exception("Please provide an input_csv with multiple files if using multithreading. For single files, you can just turn off --multithread.")
        
        # Read in the input csv
        input_args = PD.read_csv(self.args.input_csv)
        if input_args.shape[0] == 1:
            error_msg  = "--multithread requires the number of files to be greater than the requested cores."
            error_msg += " For single files, you can just turn off --multithread. Otherwise adjust --ncpu."
            raise Exception(error_msg)
        
        # Read in the load data for us to figure out best load strategy
        input_args = PD.read_csv(self.args.input_csv)

        # Add a sempahore to allow orderly file access
        semaphore = multiprocessing.Semaphore(1)

        # Create a load list for each cpu
        all_inds     = np.arange(input_args.shape[0])
        if self.args.randomize: np.random.shuffle(all_inds)
        split_arrays = np.array_split(all_inds, self.args.ncpu)

        # Start the multipull processing
        processes = []
        for data_chunk in split_arrays:
            process = multiprocessing.Process(target=self.multipull, args=(data_chunk,semaphore))
            processes.append(process)
            process.start()

        # Wait for all processes to complete
        for process in processes:
            process.join()

    def multipull(self,multiind,semaphore):
        """
        Handles a multithread data pull.

        Args:
            multiind (_type_): _description_
            semaphore (_type_): _description_
        """

        # Stagger the start of the multipull due to underlying iEEG concurrency issue
        tsleep = np.fabs(np.random.normal(loc=10,scale=2))
        time.sleep(tsleep)

        # Make a unique id for this core
        self.unique_id = uuid.uuid4()

        # Attach observers
        self.attach_objects()

        # Loop over the writeout frequency
        niter = np.ceil(multiind.size/self.args.writeout_frequency).astype('int')
        for iwrite in range(niter):
            
            # Get the current indice slice
            index_slice = multiind[iwrite*self.args.writeout_frequency:(iwrite+1)*self.args.writeout_frequency]

            # Determine what files to download and to where
            self.get_inputs(multiflag=True,multiinds=index_slice)

            # Begin downloading the data
            self.download_data_manager()

            # Hide disk i/o behind the semaphore. EDF writers sometimes access the same reference file for different runs
            with semaphore:

                # Save the results
                if not self.args.save_raw:
                    self.save_data()
                else:
                    self.save_rawdata()

                # Reset the data and type lists
                self.data_list = []
                self.type_list = []

                # Update the data records
                self.get_data_record()
                self.new_data_record = PD.concat((self.data_record,self.new_data_record))
                self.new_data_record = self.new_data_record.drop_duplicates()
                self.new_data_record = self.new_data_record.sort_values(by=['subject_number','session_number','run_number'])
                self.new_data_record.to_csv(self.data_record_path,index=False)

    ##############################
    ####### iEEG functions #######
    ##############################

    def get_password(self):
        """
        Get password for iEEG.org via Keyring or user input.
        """

        # Determine the method to get passwords. Not all systems can use a keyring easily.
        try:
            import keyring

            # Get the password from the user or the keyring. If needed, add to keyring.
            self.password = keyring.get_password("eeg_bids_ieeg_pass", self.args.username)
            if self.password == None:
                self.password = getpass.getpass("Enter your password. (This will be stored to your keyring): ")                            
                keyring.set_password("eeg_bids_ieeg_pass", self.args.username, self.password)
        except:
            self.password = getpass.getpass("Enter your password: ")

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

            # Check for any exceptions in the inputs
            IE         = InputExceptions()
            input_args = IE.ieeg_input_exceptions(input_args)

            # Grab the relevant indices if using multithreading
            if multiflag:
                input_args = input_args.iloc[multiinds].reset_index(drop=True)

            # Pull out the relevant data pointers for required columns.
            self.ieeg_files = list(input_args['orig_filename'].values)
            if not self.args.annotations:
                self.start_times = list(input_args['start'].values)
                self.durations   = list(input_args['duration'].values)

            # Get candidate keywords for missing columns
            self.ieegfile_to_keys()

            # Get the unique identifier if provided
            if 'uid' in input_args.columns:
                self.uid_list=list(input_args['uid'].values)
            
            # Get the subejct number if provided
            if 'subject_number' in input_args.columns:
                self.subject_list=list(input_args['subject_number'].values)

            # Get the session number if provided
            if 'session_number' in input_args.columns:
                self.session_list=list(input_args['session_number'].values)

            # Get the run number if provided
            if 'run_number' in input_args.columns:
                self.run_list=list(input_args['run_number'].values)

            # Get the task if provided
            if 'task' in input_args.columns:
                self.task_list=list(input_args['task'].values)

            # Get the target if provided
            if 'target' in input_args.columns:
                self.target_list = list(input_args['target'].values)

        # Conditions for no input csv file
        else:
            # Get the required information if we don't have an input csv
            self.ieeg_files  = [self.args.dataset]
            self.start_times = [self.args.start]
            self.durations   = [self.args.duration]

            # Infer input information from filename
            self.ieegfile_to_keys()

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
        
        # Add an object to store information via annotation downloads
        if self.args.annotations:
            self.annot_files      = []
            self.start_times      = []
            self.durations        = []
            self.annotation_uid   = []
            self.annotation_sub   = []
            self.annotation_ses   = []
            self.run_list         = []
            self.annotation_flats = []
        
        # Make the annotation object 
        self.annotations = {}
            
    def annotation_cleanup(self,ifile,iuid,isub,ises,itarget):
        """
        Restructure annotation information to be used as new inputs.
        """

        # Remove start clip time if it is just the machine starting up
        if self.clips[0].type.lower() == 'clip end' and self.clips[0].end_time_offset_usec == 2000:
            self.clips = self.clips[1:]

        # Manage edge cases
        if self.clips[0].type.lower() == 'clip end':
            self.clips = list(np.concatenate(([0],self.clips), axis=0))
        if self.clips[-1].type.lower() == 'clip start':
            self.clips = list(np.concatenate((self.clips,[self.ieeg_end_time-self.ieeg_start_time]), axis=0))

        clip_vals = []
        for iclip in self.clips:
            try:
                clip_vals.append(iclip.start_time_offset_usec)
            except AttributeError:
                clip_vals.append(iclip)

        # Turn the clip times into start and end arrays
        clip_start_times = np.array([iclip for iclip in clip_vals[::2]])
        clip_end_times   = np.array([iclip for iclip in clip_vals[1::2]])
        clip_durations   = clip_end_times-clip_start_times

        # Match the annotations to the clips
        self.annotations[ifile] = {ival:{} for ival in range(clip_start_times.size)}
        annotation_flats = []
        for annot in self.raw_annotations:
            time = annot.start_time_offset_usec
            desc = annot.description
            for idx, istart in enumerate(clip_start_times):
                if (time >= istart) and (time <= clip_end_times[idx]):
                    event_time_shift = (time-istart)
                    self.annotations[ifile][idx][event_time_shift] = desc
                    annotation_flats.append(desc)
        
        # Update the instance wide values
        self.annot_files.extend([ifile for idx in range(len(clip_start_times))])
        self.annotation_uid.extend([iuid for idx in range(len(clip_start_times))])
        self.annotation_sub.extend([isub for idx in range(len(clip_start_times))])
        self.annotation_ses.extend([ises for idx in range(len(clip_start_times))])
        self.target_list.extend([itarget for idx in range(len(clip_start_times))])
        self.start_times.extend(clip_start_times)
        self.durations.extend(clip_durations)
        self.run_list.extend(np.arange(len(clip_start_times)))
        self.annotation_flats.extend(annotation_flats)

    def annotation_cleanup_set_time(self,idx):
        
        # Get just the current annotation block from ieeg
        self.download_data(self.ieeg_files[idx],self.start_times[idx],self.durations[idx],True)
        
        # Make the annotation object
        if self.ieeg_files[idx] not in self.annotations.keys():
            self.annotations[self.ieeg_files[idx]] = {}
        self.annotations[self.ieeg_files[idx]][self.run_list[idx]] = {}

        for annot in self.raw_annotations:

            # get the information out of the annotation layer
            time = annot.start_time_offset_usec
            desc = annot.description

            # figure out its time relative to the download start
            event_time_shift = (time-self.start_times[idx])

            # Store the results
            self.annotations[self.ieeg_files[idx]][self.run_list[idx]][event_time_shift] = desc


    def ieegfile_to_keys(self):
        """
        Use the iEEG.org filename to determine keywords.
        """

        # Extract possible keywords from the ieeg filename
        self.uid_list     = []
        self.subject_list = []
        self.session_list = []
        self.run_list     = []
        for ifile in self.ieeg_files:

            # Create a match object to search for relevant subject and session data
            match = re.search(r'\D+(\d+)_\D+(\d+)', ifile)

            # Get numerical portions of filename that correspond to subject and session
            if match:
                candidate_uid = int(match.group(1))
                candidate_sub = match.group(1)
                candidate_ses = match.group(2)
            else:
                candidate_uid = None
                candidate_sub = None
                candidate_ses = None

            # Look for this informaion in the records
            iDF = self.data_record.loc[self.data_record.orig_filename==ifile]

            # If the data already exists, get its previous information
            if iDF.shape[0] > 0:

                # Get the existing information
                candidate_uid = iDF.iloc[0].uid
                candidate_sub = str(iDF.iloc[0].subject_number)
                candidate_ses = str(iDF.iloc[0].session_number)

            # Create the subject and session lists
            self.uid_list.append(candidate_uid)
            self.subject_list.append(candidate_sub)
            self.session_list.append(candidate_ses)
            self.run_list.append(1)

    def download_data_manager(self):
        """
        Loop over the ieeg file list and download data. If annotations, does a first pass to get annotation layers and times, then downloads.
        """

        # Load the data exists exception handler so we can avoid already downloaded data.
        DE = DataExists(self.data_record)

        # Loop over the requested data
        for idx in range(len(self.ieeg_files)):

            # Download the data
            if self.args.annotations:
                self.download_data(self.ieeg_files[idx],0,0,True)
                if self.success_flag:
                    self.annotation_cleanup(self.ieeg_files[idx],self.uid_list[idx],self.subject_list[idx],self.session_list[idx],self.target_list[idx])
            else:
                # If-else around if the data already exists in our records. Add a skip to the data list if found to maintain run order.
                if DE.check_default_records(self.ieeg_files[idx],1e-6*self.start_times[idx],1e-6*self.durations[idx],overwrite=self.args.overwrite):

                    # Get the annotations for just this download if requested
                    if self.args.include_annotation:
                        self.annotation_cleanup_set_time(idx)

                    # Download the data
                    self.download_data(self.ieeg_files[idx],self.start_times[idx],self.durations[idx],False)
                    
                    # If successful, notify data observer. Else, add a skip
                    if self.success_flag:
                        # Data object is a way to package data relevant to whatever workflow you want to send to a backend. Named and packaged like this so the listener can send
                        # an expected object to different backends.
                        self.data_object = (self.data,self.channels,self.fs)
                        self.notify_data_observers()
                    else:
                        self.data_list.append(None)
                        self.type_list.append(None)
                else:
                    print(f"Skipping {self.ieeg_files[idx]} starting at {1e-6*self.start_times[idx]:011.2f} seconds for {1e-6*self.durations[idx]:08.2f} seconds.")
                    self.data_list.append(None)
                    self.type_list.append(None)

        # If downloading by annotations, now loop over the clip level info and save
        if self.args.annotations:
            # Update the object pointers for subject, session, etc. info
            self.ieeg_files   = self.annot_files
            self.uid_list     = self.annotation_uid
            self.subject_list = self.annotation_sub
            self.session_list = self.annotation_ses

            # Loop over the file list that is expanded by all the annotations
            for idx in range(len(self.ieeg_files)):

                # If-else around if the data already exists in our records. Add a skip to the data list if found to maintain run order.
                if DE.check_default_records(self.ieeg_files[idx],1e-6*self.start_times[idx],1e-6*self.durations[idx],overwrite=self.args.overwrite):

                    # Download the data
                    self.download_data(self.ieeg_files[idx],self.start_times[idx],self.durations[idx],False)
                    
                    # If successful, notify data observer. Else, add a skip
                    if self.success_flag:
                        # Data object is a way to package data relevant to whatever workflow you want to send to a backend. Named and packaged like this so the listener can send
                        # an expected object to different backends.
                        self.data_object = (self.data,self.channels,self.fs)
                        self.notify_data_observers()
                    else:
                        self.data_list.append(None)
                        self.type_list.append(None)
                else:
                    print(f"Skipping {self.ieeg_files[idx]} starting at {1e-6*self.start_times[idx]:011.2f} seconds for {1e-6*self.durations[idx]:08.2f} seconds.")
                    self.data_list.append(None)
                    self.type_list.append(None)
                
    def save_rawdata(self):
        """
        Save data directly as a csv
        """

        # Loop over the data, assign keys, and save
        self.new_data_record = self.data_record.copy()
        for idx,iraw in enumerate(self.data_list):
            if iraw != None:

                try:
                    # Define start time and duration. Can differ for different filetypes
                    # iEEG.org uses microseconds. So we convert here to seconds for output.
                    istart    = 1e-6*self.start_times[idx]
                    iduration = 1e-6*self.durations[idx]

                    # Get the raw data
                    DF    = PD.DataFrame(iraw.get_data().T,columns=iraw.ch_names)
                    sfreq = iraw.info['sfreq']

                    # Make the output filename
                    outbasename = f"{self.ieeg_files[idx]}_{istart}_{iduration}_{sfreq}HZ.csv"
                    outpath     = f"{self.args.bids_root}{outbasename}"
                    
                    # Save the output
                    DF.to_csv(outpath,index=False)
                except Exception as e:
                    print("Unable to save data.")
                    if self.args.debug:
                        print(f"Error {e}")


    def save_data(self):
        """
        Notify the BIDS code about data updates and save the results when possible.
        """
        
        # Loop over the data, assign keys, and save
        self.new_data_record = self.data_record.copy()
        for idx,iraw in enumerate(self.data_list):
            if iraw != None:

                # Define start time and duration. Can differ for different filetypes
                # iEEG.org uses microseconds. So we convert here to seconds for output.
                istart    = 1e-6*self.start_times[idx]
                iduration = 1e-6*self.durations[idx]

                # Update keywords
                self.keywords = {'filename':self.ieeg_files[idx],'root':self.args.bids_root,'datatype':self.type_list[idx],
                                'session':self.session_list[idx],'subject':self.subject_list[idx],'run':self.run_list[idx],
                                'task':'rest','fs':iraw.info["sfreq"],'start':istart,'duration':iduration,'uid':self.uid_list[idx]}
                self.notify_metadata_observers(self.args.backend)

                # Save the data
                if self.args.include_annotation or self.args.annotations:
                    success_flag = self.BH.save_data_w_events(iraw, debug=self.args.debug)
                else:
                    success_flag = self.BH.save_data_wo_events(iraw, debug=self.args.debug)

                # Check if its all zero data if we failed
                if not success_flag and self.args.zero_bad_data:
                    
                    # Store the meta data for this raw to copy to the new zeroed out data
                    newinfo = iraw.info
                    newchan = dict(map(lambda i,j : (i,j) , iraw.ch_names,iraw.get_channel_types()))
                    idata   = 0*iraw.get_data()
                    
                    # Make a new zero mne object
                    newraw = mne.io.RawArray(idata,newinfo, verbose=False)
                    newraw.set_channel_types(newchan)

                    # Try to save the zero data
                    success_flag = self.BH.save_raw_edf(newraw,self.type_list[idx],debug=self.args.debug)
                elif not success_flag and not self.args.zero_bad_data:
                    print(f"Unable to save clip starting at {istart} seconds with duration {iduration} seconds.")

                # If the data wrote out correctly, update the data record
                if success_flag:
                    # Save the target info
                    try:
                        self.BH.save_targets(self.target_list[idx])
                    except:
                        pass

                    # Add the datarow to the records
                    self.current_record  = self.BH.make_records('ieeg.org')
                    self.new_data_record = PD.concat((self.new_data_record,self.current_record))

    ###############################################
    ###### IEEG Connection related functions ######
    ###############################################

    def download_data(self,ieegfile,start,duration,annotation_flag,n_retry=5):

        # Attempt connection to iEEG.org up to the retry limit
        self.global_timeout = self.args.timeout
        n_attempts          = 0
        self.success_flag   = False
        while True:
            with Timeout(self.global_timeout,False):
                try:
                    self.ieeg_session(ieegfile,start,duration,annotation_flag)
                    self.success_flag = True
                    break
                except (IIA.IeegConnectionError,IIA.IeegServiceError,TimeoutException,RTIMEOUT,TypeError) as e:
                    # Get more info through debug
                    if self.args.debug:
                        print(self.logmsg)

                    if n_attempts<n_retry:
                        sleep(5)
                        n_attempts += 1
                    else:
                        print(f"Connection Error: {e}")
                        if self.args.connection_error_folder != None:
                            fp = open(f"{self.args.connection_error_folder}{self.unique_id}.errors","a")
                            fp.write(f"{e}\n")
                            fp.close()
                        break

    def ieeg_session(self,ieegfile,start,duration,annotation_flag):
        """
        Call ieeg.org for data and return data or annotations.

        Args:
            start (float): Start time (referenced to data start) in microseconds to request data from
            duration (float): Duration in microseconds of data to request
            annotation_flag (bool, optional): Flag whether we just want annotation data or not. Defaults to False.

        Raises:
            IndexError: If there are multiple sampling frequencies, bids does not readily support this. Alerts user and stops.
        """

        with Session(self.args.username,self.password) as session:
            
            # Open dataset session
            self.logmsg = f"Tried accessing {ieegfile} "
            dataset     = session.open_dataset(ieegfile)
            
            # Logic gate for annotation call (faster, no time data needed) or get actual data
            if not annotation_flag:

                # Status
                print(f"Core {self.unique_id} is downloading {ieegfile} starting at {1e-6*start:011.2f} seconds for {1e-6*duration:08.2f} seconds.")

                # Get the channel names and integer representations for data call
                self.channels  = dataset.ch_labels
                channel_cntr   = list(range(len(self.channels)))
                nchan_win      = 50
                channel_chunks = [channel_cntr[i:i+nchan_win] for i in range(0, len(channel_cntr), nchan_win)] 

                # If duration is greater than 10 min, break up the call. Make array of start,duration with max 10 min each chunk
                twin_min    = self.args.download_time_window
                time_cutoff = int(twin_min*60*1e6)
                end_time    = start+duration
                ival        = start
                chunks      = []
                while ival < end_time:
                    if ival+time_cutoff >= end_time:
                        chunks.append([ival,end_time-ival])
                    else:
                        chunks.append([ival,time_cutoff])
                    ival += time_cutoff

                # Call data and concatenate calls if greater than 10 min
                self.data    = []
                for idx,ival in enumerate(chunks):
                    self.logmsg += f"at {ival[0]} seconds for {ival[1]} seconds."
                    for chunk_cntr,ichunk in enumerate(channel_chunks):
                        if chunk_cntr == 0:
                            idata = dataset.get_data(ival[0],ival[1],ichunk)
                        else:
                            tmp   = dataset.get_data(ival[0],ival[1],ichunk)
                            idata = np.hstack((idata,tmp))
                    self.data.append(idata)

                if len(self.data) > 1:
                    self.data = np.concatenate(self.data)
                else:
                    self.data = self.data[0]

                # Apply the voltage factors
                self.data = 1e-6*self.data

                # Get the channel labels
                self.channels = dataset.ch_labels

                # Get the samping frequencies
                self.fs = [dataset.get_time_series_details(ichannel).sample_rate for ichannel in self.channels]

                # Data quality checks before saving
                if np.unique(self.fs).size == 1:
                    self.fs = self.fs[0]
                else:
                    raise Exception("Too many unique values for sampling frequency.")
            else:
                self.raw_annotations = dataset.get_annotations(self.args.annot_layer)
                if self.args.annotations:
                    self.clips = dataset.get_annotations(self.args.time_layer)
                self.ieeg_start_time = dataset.start_time
                self.ieeg_end_time   = dataset.end_time
            session.close()

    ###############################
    ###### Custom exceptions ######
    ###############################

    def input_exceptions(self,input_args):

        # Raise some exceptions if we find data we can't work with
        if 'orig_filename' not in input_args.columns:
            raise Exception("Please provide 'orig_filename' in the input csv file.")
        elif 'orig_filename' in input_args.columns:
            if 'start' not in input_args.columns and not self.args.annotations:
                raise Exception("A 'start' column is required in the input csv if not using the --annotations flag.")
            elif 'duration' not in input_args.columns and not self.args.annotations:
                raise Exception("A 'duration' column is required in the input csv if not using the --annotations flag.")
        
        # Handle situations where the user requested annotations but also provided times
        if self.args.annotations:
            if 'start' in input_args.columns or 'duration' in input_args.columns:
                userinput = ''
                while userinput.lower() not in ['y','n']:
                    userinput = input("--annotations flag set to True, but start times and durations were provided in the input. Override these times with annotations clips (Yy/Nn)? ")
                if userinput.lower() == 'n':
                    print("Ignoring --annotation flag. Using user provided times.")
                    self.args.annotations = False
                if userinput.lower() == 'y':
                    print("Ignoring user provided times in favor of annotation layer times.")
                    if 'start' in input_args.columns: input_args.drop(['start'],axis=1,inplace=True)
                    if 'duration' in input_args.columns: input_args.drop(['duration'],axis=1,inplace=True)

        return input_args