import numpy as np
import pandas as PD

# API timeout class
import signal
class TimeoutException(Exception):
    pass

class Timeout:
    """
    Manage timeouts to the iEEG.org API call. It can go stale, and sit for long periods of time otherwise.
    """

    def __init__(self, seconds=1, multiflag=False, error_message='Function call timed out'):
        self.seconds       = seconds
        self.error_message = error_message
        self.multiflag     = multiflag

    def handle_timeout(self, signum, frame):
        raise TimeoutException(self.error_message)

    def __enter__(self):
        if not self.multiflag:
            signal.signal(signal.SIGALRM, self.handle_timeout)
            signal.alarm(self.seconds)
        else:
            pass

    def __exit__(self, exc_type, exc_value, traceback):
        if not self.multiflag:
            signal.alarm(0)
        else:
            pass

class DataExists:
    """
    Checks data records for existing data.
    """

    def __init__(self,data_record):
        self.data_record      = data_record
        self.record_checkfile = ''
        self.record_start     = -1
        self.record_duration  = -1

    def check_default_records(self,checkfile,checkstart,checkduration,overwrite=False):
        """
        Check the data record for data that matched the current query.

        Args:
            checkfile (_type_): Current filename.
            checkstart (_type_): Current start time in seconds.
            checkduration (_type_): Current duration in seconds.

        Returns:
            bool: True if no data found in record. False is found.
        """

        if overwrite:
            return True
        else:
            if self.data_record.shape[0] > 0:
                # Update file mask as needed
                if checkfile != self.record_checkfile:
                    self.record_checkfile = checkfile
                    self.record_file_mask = (self.data_record['orig_filename'].values==checkfile)
                mask = self.record_file_mask

                # Update the start mask as needed. Due to writeout rounding, using tolerance of 1 second.
                if type(checkstart) == float or type (checkstart) == int:
                    if checkstart != self.record_start:
                        self.record_start      = checkstart
                        self.record_start_mask = np.isclose(self.data_record['start_sec'].values,checkstart,atol=1)
                        mask                  *= self.record_start_mask

                # Update the duration mask as needed. Due to writeout rounding, using tolerance of 1 second.
                if type(checkduration) == float or type (checkduration) == int:
                    if checkduration != self.record_duration:
                        self.record_duration      = checkduration
                        self.record_duration_mask = np.isclose(self.data_record['duration_sec'].values,checkduration,atol=1)
                        mask                     *= self.record_duration_mask

                # Check for any existing records
                return not(any(mask))
            else:
                return True

class InputExceptions:

    def __init__(self):
        pass

    def edf_input_exceptions(self,args):
        """
        Custom argument exceptions for EDF data conversion. 

        Args:
            args (Namespace): Argument parser.

        Raises:
            Exception: Generic exception to alert user to EDF specific argument configuration.

        Returns:
            args (Namespace): Updated Argument parser.
        """

        # Input csv exceptions
        if args.input_csv:
            input_cols = PD.read_csv(args.input_csv, index_col=0, nrows=0).columns.tolist()
            if 'subject_number' not in input_cols:
                raise Exception("Please provide a --subject_number to the input csv.")
            if 'session_number' not in input_cols:
                raise Exception("Please provide a --session_number to the input csv.")
            if 'run_number' not in input_cols:
                raise Exception("Please provide a --run_number to the input csv.")
            if 'uid' not in input_cols:
                raise Exception("Please provide a --uid_number to the input csv.")
        else:
            if args.subject_number == None:
                raise Exception("Please provide a --subject_number input to the command line.")
            if args.uid_number == None:
                raise Exception("Please provide a --uid_number input to the command line.")
            if args.session == None:
                while True:
                    flag = input(f"Use Session Number {1:03d} (Yy/Nn)? ")
                    if flag.lower() == 'y':
                        break
                    elif flag.lower() == 'n':
                        raise Exception("Please provide a --session_number input to the command line.")
                args.session=1
            if args.run == None:
                while True:
                    flag = input(f"Use Run Number {1:03d} (Yy/Nn)? ")
                    if flag.lower() == 'y':
                        break
                    elif flag.lower() == 'n':
                        raise Exception("Please provide a --run_number input to the command line.")
                args.run=1

        return args
    
    def nifti_input_exceptions(self,args):
        """
        Custom argument exceptions for imaging data conversion. 

        Args:
            args (Namespace): Argument parser.

        Raises:
            Exception: Generic exception to alert user to EDF specific argument configuration.

        Returns:
            args (Namespace): Updated Argument parser.
        """

        # Manage the high level bids keywords
        if args.input_csv:
            input_cols = PD.read_csv(args.input_csv, index_col=0, nrows=0).columns.tolist()
            if 'subject_number' not in input_cols:
                raise Exception("Please provide a --subject_number to the input csv.")
            if 'session_number' not in input_cols:
                raise Exception("Please provide a --session_number to the input csv.")
            if 'run_number' not in input_cols:
                raise Exception("Please provide a --run_number to the input csv.")
            if 'uid' not in input_cols:
                raise Exception("Please provide a --uid_number to the input csv.")
        else:
            if args.subject_number == None:
                raise Exception("Please provide a --subject_number input to the command line.")
            if args.uid_number == None:
                raise Exception("Please provide a --uid_number input to the command line.")
            if args.session == None:
                while True:
                    flag = input(f"Use Session Number {1:03d} (Yy/Nn)? ")
                    if flag.lower() == 'y':
                        break
                    elif flag.lower() == 'n':
                        raise Exception("Please provide a --session_number input to the command line.")
                args.session=1
            if args.run == None:
                while True:
                    flag = input(f"Use Run Number {1:03d} (Yy/Nn)? ")
                    if flag.lower() == 'y':
                        break
                    elif flag.lower() == 'n':
                        raise Exception("Please provide a --run_number input to the command line.")
                args.run=1

        return args