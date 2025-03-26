import os
import argparse
import pandas as PD
from sys import exit
from prettytable import PrettyTable, HRuleStyle

# Local import
from components.internal.BIDS_handler import *
from components.public.edf_handler import edf_handler
from components.public.iEEG_handler import ieeg_handler
from components.public.iEEG_handler import ieeg_handler
from components.public.nifti_handler import nifti_handler
from components.public.pennsieve_handler import pennsieve_handler

# MNE is very chatty. Turn off some warnings. Shouldn't supress legit errors.
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)
warnings.simplefilter(action='ignore', category=RuntimeWarning)

def print_examples():
    """
    This function is to provide samples of input tables for mass BIDS creation.
    """

    def resize_table_entry(DF,colname,screenwidth=0.2):
        """
        Create a shortened string for a given dataframe column. Allows better displays when used with things like prettytable.

        Args:
            DF (pandas dataframe): A dataframe with a string column to resize.
            colname (string): Column name in dataframe with strings to resize.
            screenwidth (float, Optional): Percent of the screen width to set as column maximum width.

        Returns:
            dataframe: Dataframe with new shortened strings.
        """
        max_width = np.floor(0.2*os.get_terminal_size().columns)
        pad_width = int(0.5*max_width)
        values    = DF[colname].values
        for idx,ival in enumerate(values):
            if len(ival) > max_width:
                newval = f"{ival[:pad_width]}...{ival[-pad_width:]}"
            else:
                newval = ival
            values[idx] = newval
        DF.loc[:,[colname]] = values
        return DF

    def print_table(inpath):
        """
        Print example inputs from an input csv file.

        Args:
            inpath (string,filepath)): Relative path from the script directory to the example table.
        """
        
        # Read in the data
        script_dir  = '/'.join(os.path.abspath(__file__).split('/')[:-1])
        example_csv = PD.read_csv(f"{script_dir}{inpath}")

        # Make sure the filename path isnt too long
        example_csv = resize_table_entry(example_csv,'orig_filename')
        if 'target' in example_csv.columns:
            example_csv = resize_table_entry(example_csv,'target')
        
        # Initialize a pretty table for easy reading
        HRuleStyle(1)
        table = PrettyTable()
        table.field_names = example_csv.columns
        for irow in example_csv.index:
            iDF           = example_csv.loc[irow]
            formatted_row = [iDF[icol] for icol in example_csv.columns]
            table.add_row(formatted_row)
        table.align['path'] = 'l'
        print(table)

    ######################################################################################
    ##### General message to remind user to check the readme for more documentation. #####
    ######################################################################################

    # Print a header block for the ieeg.org section.
    print("################################")
    print("####### BIDSIFY Examples #######")
    print("################################")
    print("These are a few of the most common use cases for BDISIFY.py.")
    print("For a more in-depth exaplanation of various options, please refer to the README.md located at the repository here:")
    print("    https://github.com/penn-cnt/EEG_BIDS")
    print("\n\n")

    ##############################################
    ##### Example of how to convert EDF data #####
    ##############################################

    # Print a header block for the EDF section.
    print("############################")
    print("####### EDF Commands #######")
    print("############################")

    # Read in the samples without targets
    print("Convert a single EDF file without a csv, using command line keyword calls. Read in a target file to associate with the bids dataset.")
    print("Example instantiation:")
    print("    python BIDSIFY.py --edf --bids_root <path-to-output-root-directory> --dataset <path-to-edf> --subject HUP001 --uid_number 1 --session 1 --run 1 --target <path-to-target-file>")
    print("\n\n")

    # Read in the samples without targets
    print("Convert multiple EDF files into a BIDS directory.")
    print_table('/samples/inputs/sample_edf_inputs.csv')
    print("Path to sample csv: ./samples/inputs/sample_edf_inputs.csv")
    print("Example instantiation:")
    print("    python BIDSIFY.py --edf --bids_root <path-to-output-root-directory> --input_csv <path-to-csv>")
    print("\n\n")

    # Read in the samples with targets
    print("Convert multiple EDF files into a BIDS directory with target data.")
    print_table('/samples/inputs/sample_edf_inputs_w_target.csv')
    print("Path to sample csv: ./samples/inputs/sample_edf_inputs_w_target.csv")
    print("Example instantiation:")
    print("    python BIDSIFY.py --edf --bids_root <path-to-output-root-directory> --input_csv <path-to-csv>")
    print("\n\n")

    #########################################################
    ##### Example of how to convert NIFTI data to BIDS. #####
    #########################################################
    
    # Print a header block for the ieeg.org section.
    print("##############################")
    print("####### NIFTI Commands #######")
    print("##############################")

    # How to convert a single nifti file
    print("Convert a single NIFTI file without a csv, using command line keyword calls.")
    print("Example instantiation:")
    print("    python BIDSIFY.py --nifti --bids_root <path-to-output-root-directory> --dataset <path-to-nifti>  --subject_number HUP001 --uid_number 0 --session 001 --run 01 --imaging_data_type anat --imaging_scan_type MR --imaging_modality flair --imaging_task None --imaging_acq ax --imaging_ce None")
    print("\n\n")

    # Read in the samples with targets
    print("Convert multiple NIFTI files into a BIDS directory. Also use a datalake to help convert data not in the csv using known protocol names.")
    print_table('/samples/inputs/sample_nifti_inputs.csv')
    print("Path to sample csv: ./samples/inputs/sample_nifti_inputs.csv")
    print("Example instantiation:")
    print("    python BIDSIFY.py --nifti --datalake datalakes/R61_datalake.pickle --bids_root  <path-to-output-root-directory> --input_csv <path-to-csv>")
    print("\n\n")

    ##########################################################
    ##### Example of how to download data from iEEG.org. #####
    ##########################################################
    
    # Print a header block for the ieeg.org section.
    print("#################################")
    print("####### iEEG.org Commands #######")
    print("#################################")

    # Read in the sample time csv
    print("Download multiple files from iEEG.org using a csv file with download times and storing specific annotations/targets as sidecar information.")
    print_table('/samples/inputs/download_by_times.csv')
    print("Path to sample csv: ./samples/inputs/download_by_times.csv")
    print("Example instantiation:")
    print("    python BIDSIFY.py --ieeg --username <ieeg.org-username> --bids_root <path-to-output-root-directory>  --input_csv <path-to-csv>")
    print("\n\n")

    # Read in the sample annotation csv
    print("Download multiple files from iEEG.org using a csv file with filenames, downloading all annotation clip layers from the dataset, and storing specific annotations/targets as sidecar information to each clip.")
    print_table('/samples/inputs/download_by_annotations.csv')
    print("Path to sample csv: ./samples/inputs/download_by_anotations.csv")
    print("Example instantiation:")
    print("    python BIDSIFY.py --ieeg --username <ieeg.org-username> --bids_root <path-to-output-root-directory>  --annotations --input_csv <path-to-csv>")
    print("\n\n")

def ieeg(args):
    """
    Kick off iEEG data pulls.

    Args:
        args (Namespace): Argument parser.
    """

    IH = ieeg_handler(args)
    IH.workflow()

def raw_edf(args):
    """
    Kick off raw edf conversions.

    Args:
        args (Namespace): Argument parser.
    """
    EH = edf_handler(args)
    EH.workflow()

def nifti(args):
    NH = nifti_handler(args)
    NH.workflow()

def pennsieve(args):
    """
    Perform pennsieve data pull.

    Args:
        args (Namespace): Argument parser.
    """

    PH = pennsieve_handler(args)
    PH.workflow()

if __name__ == '__main__':

    # Command line options needed to obtain data.
    parser = argparse.ArgumentParser(description="Make an EEG BIDS dataset from various sources. Also manages helper scripts for the CNT.")

    # If the user wants an example input file, print it then close application
    parser.add_argument("--example_input", action='store_true', default=False, help="Show example input file structure.")   
    partial_args, _ = parser.parse_known_args()
    if partial_args.example_input:
        print_examples()
        exit()

    # Define the source dataset
    source_group = parser.add_argument_group('Data source options')
    source_option_group = source_group.add_mutually_exclusive_group(required=True)
    source_option_group.add_argument("--ieeg", action='store_true', default=False, help="iEEG data pull.")
    source_option_group.add_argument("--edf", action='store_true', default=False, help="Raw edf data pull.")
    source_option_group.add_argument("--pennsieve", action='store_true', default=False, help="Pennsieve data pull.")
    source_option_group.add_argument("--nifti", action='store_true', default=False, help="Imaging data BIDS creation.")

    # Check for as yet unimplemnted pennsieve api
    partial_args, _ = parser.parse_known_args()
    if partial_args.pennsieve:
        print(f"Pennsieve support is not yet implmented.")
        print(f"The Python API is still in development, and the agent only pulls down whole files.")
        print(f"Python support for targeted downloads, including time segment downloads, is available on request from the Data team. (Not publically available code)")
        print("Once Pennsieve releases a full api, this code should be updated to call on the API properly and rescope variables to pennsieve equivalents and update the subject map.")
        exit()

    # Continue with remaining arguments for script
    data_group = parser.add_argument_group('Data configuration options')
    data_group.add_argument("--bids_root", type=str, required=True, default=None, help="Output directory to store BIDS data.")
    data_group.add_argument("--data_record", type=str, default='subject_map.csv', help="Filename for data record. Outputs to bids_root.")
    data_group.add_argument("--input_csv", type=str, help="CSV file with the relevant filenames, start times, durations, and keywords. For an example, use the --example_input flag.")
    data_group.add_argument("--dataset", type=str, help="Dataset name/Path to dataset. Useful if working with just one dataset,")
    data_group.add_argument("--overwrite", action='store_true', default=False, help="Overwrite existing records with the same bids keywords.")
    data_group.add_argument("--anonymize", action='store_true', default=False, help="Anonymize the data before writeout. (Currently only anonymizes EDF data.)")

    ieeg_group = parser.add_argument_group('iEEG connection options')
    ieeg_group.add_argument("--username", type=str, help="Username for iEEG.org.")
    ieeg_group.add_argument("--start", type=float, help="Start time of clip in usec. Useful if downloading just one dataset,")
    ieeg_group.add_argument("--duration", type=float, help="Duration of clip in usec. Useful if downloading just one dataset,")
    ieeg_group.add_argument("--failure_file", default='./failed_ieeg_calls.csv', type=str, help="CSV containing failed iEEG calls.")    
    ieeg_group.add_argument("--annotations", action='store_true', default=False, help="Download by annotation layers. Defaults to scalp layer names.")
    ieeg_group.add_argument("--time_layer", type=str, default='EEG clip times', help="Annotation layer name for clip times.")
    ieeg_group.add_argument("--annot_layer", type=str, default='Imported Natus ENT annotations', help="Annotation layer name for annotation strings.")
    ieeg_group.add_argument("--timeout", type=int, default=60, help="Timeout interval for ieeg.org calls")
    ieeg_group.add_argument("--download_time_window", type=int, default=10, help="The length of data to pull from iEEG.org for subprocess calls (in minutes). For high frequency, many channeled data, consider lowering. ")

    imaging_group = parser.add_argument_group('Imaging options')
    imaging_group.add_argument("--datalake", type=str, help="Path to datalake of imaging protocol names mapped to BIDS keywords. (Optional)")
    imaging_group.add_argument("--imaging_data_type", type=str, help="Data type for imaging data. (Optional. Will query if not provided.)")
    imaging_group.add_argument("--imaging_scan_type", type=str, help="Scan type for imaging data. (Optional. Will query if not provided.)")
    imaging_group.add_argument("--imaging_modality", type=str, help="Modality for imaging data. (Optional. Will query if not provided.)")
    imaging_group.add_argument("--imaging_task", type=str, help="Task for imaging data. (Optional. Will query if not provided.)")
    imaging_group.add_argument("--imaging_acq", type=str, help="Acquisition for imaging data. (Optional. Will query if not provided.)")
    imaging_group.add_argument("--imaging_ce", type=str, help="Contrast for imaging data. (Optional. Will query if not provided.)")

    bids_group = parser.add_argument_group('BIDS keyword options')
    bids_group.add_argument("--uid_number", type=str, help="Unique identifier string to use when not referencing a input_csv file. Only used for single data pulls. Can be used to map the same patient across different datasets to something like an MRN behind clinical firewalls.")
    bids_group.add_argument("--subject_number", type=str, help="Subject string to use when not referencing a input_csv file. Only used for single data pulls.")
    bids_group.add_argument("--session", type=str, help="Session string to use when not referencing a input_csv file. Only used for single data pulls.")
    bids_group.add_argument("--run", type=int, help="Run string to use when not referencing a input_csv file. Only used for single data pulls.")
    bids_group.add_argument("--task", type=str, default='rest', help="Task string to use when not referencing a input_csv file value. Used to populate all entries if not explicitly set.")
    bids_group.add_argument("--target", type=str, help="Target to associate with the data. (i.e. PNES/EPILEPSY/etc.)")
    bids_group.add_argument("--event_file", type=str, default=None, help="Path to an events file, if applicable.")
    
    multithread_group = parser.add_argument_group('Multithreading Options')
    multithread_group.add_argument("--multithread", action='store_true', default=False, help="Multithreaded download.")
    multithread_group.add_argument("--ncpu", default=1, type=int, help="Number of CPUs to use when downloading.")
    multithread_group.add_argument("--writeout_frequency", default=10, type=int, help="How many files to download before writing out results and continuing downloads. Too frequent can result in a large slowdown. But for buggy iEEG pulls, frequent saves save progress.")

    debug_group = parser.add_argument_group('Debugging and Hardcoded Options to deal with oddballs.')
    debug_group.add_argument("--debug", action='store_true', default=False, help="Debug tools. Mainly removes files after generation.")
    debug_group.add_argument("--ch_type", default=None, type=str, help="Manual set of channel type if not matched by known patterns. (i.e. 'seeg' for intracranial data)")
    debug_group.add_argument("--randomize", action='store_true', default=False, help="Randomize load order. Useful if doing a big multi part download and most of the work left is by default on a single core.")

    misc_group = parser.add_argument_group('Misc options')
    misc_group.add_argument("--include_annotation", action='store_true', default=False, help="If downloading by time, include annotations/events file. Defaults to scalp layer names.")
    misc_group.add_argument("--backend", type=str, default='MNE', help="Backend data handler.")
    misc_group.add_argument("--zero_bad_data", action='store_true', default=False, help="Zero out bad data potions.")
    misc_group.add_argument("--copy_edf", action='store_true', default=False, help="Straight copy an edf to bids format. Do not writeout via mne. (Still checks for valid data using mne)")
    misc_group.add_argument("--connection_error_folder", default=None, type=str, help="If provided, save connection errors to this folder. Helps determine access issues after a large download.")
    misc_group.add_argument("--save_raw", action='store_true', default=False, help="Save the data as a raw csv")
    misc_group.add_argument("--event_from_backend", action='store_true', default=False, help="Use backend software to try and infer events.")
    args = parser.parse_args()

    # Basic clean-up of path names
    if args.bids_root[-1] != '/': args.bids_root+='/'

    # Select use case
    if args.ieeg:
        ieeg(args)
    elif args.edf:
        raw_edf(args)
    elif args.nifti:
        if args.backend.lower() == 'mne':
            print("Changing default backend to nibabel... (Use --backend to manually set backend.)")
            args.backend = 'nibabel'
        nifti(args)
    else:
        print("Please select at least one source from the source group. (--help for all options.)")
