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

# MNE is very chatty. Turn off some warnings.
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)
warnings.simplefilter(action='ignore', category=RuntimeWarning)

def print_examples():
    """
    This function is to provide samples of input tables for mass BIDS creation.
    """
        
    # Read in the sample time csv
    script_dir  = '/'.join(os.path.abspath(__file__).split('/')[:-1])
    example_csv = PD.read_csv(f"{script_dir}/samples/inputs/download_by_times.csv")
    
    # Initialize a pretty table for easy reading
    HRuleStyle(1)
    table = PrettyTable()
    table.field_names = example_csv.columns
    for irow in example_csv.index:
        iDF           = example_csv.loc[irow]
        formatted_row = [iDF[icol] for icol in example_csv.columns]
        table.add_row(formatted_row)
    table.align['path'] = 'l'
    print("Sample inputs that explicitly set the download times.")
    print(table)

    # Read in the sample annotation csv
    script_dir  = '/'.join(os.path.abspath(__file__).split('/')[:-1])
    example_csv = PD.read_csv(f"{script_dir}/samples/inputs/download_by_annotations.csv")
    
    # Initialize a pretty table for easy reading
    table = PrettyTable()
    table.field_names = example_csv.columns
    for irow in example_csv.index:
        iDF           = example_csv.loc[irow]
        formatted_row = [iDF[icol] for icol in example_csv.columns]
        table.add_row(formatted_row)
    table.align['path'] = 'l'
    print("Sample inputs that use annotations.")
    print(table)

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

def read_jar(args):
    """
    Kick off jar conversions.

    Args:
        args (Namespace): Argument parser.
    """

    JH = jar_handler(args)
    JH.workflow()

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
    bids_group.add_argument("--event_file", type=str, default=None, help="Path to an events file, if applicable.")

    multithread_group = parser.add_argument_group('Multithreading Options')
    multithread_group.add_argument("--multithread", action='store_true', default=False, help="Multithreaded download.")
    multithread_group.add_argument("--ncpu", default=1, type=int, help="Number of CPUs to use when downloading.")
    multithread_group.add_argument("--writeout_frequency", default=10, type=int, help="How many files to download before writing out results and continuing downloads. Too frequent can result in a large slowdown. But for buggy iEEG pulls, frequent saves save progress.")

    misc_group = parser.add_argument_group('Misc options')
    misc_group.add_argument("--include_annotation", action='store_true', default=False, help="If downloading by time, include annotations/events file. Defaults to scalp layer names.")
    misc_group.add_argument("--target", type=str, help="Target to associate with the data. (i.e. PNES/EPILEPSY/etc.)")
    misc_group.add_argument("--backend", type=str, default='MNE', help="Backend data handler.")
    misc_group.add_argument("--ch_type", default=None, type=str, help="Manual set of channel type if not matched by known patterns. (i.e. 'seeg' for intracranial data)")
    misc_group.add_argument("--debug", action='store_true', default=False, help="Debug tools. Mainly removes files after generation.")
    misc_group.add_argument("--randomize", action='store_true', default=False, help="Randomize load order. Useful if doing a bit multipull and we're left with most of the work on a single core.")
    misc_group.add_argument("--zero_bad_data", action='store_true', default=False, help="Zero out bad data potions.")
    misc_group.add_argument("--copy_edf", action='store_true', default=False, help="Straight copy an edf to bids format. Do not writeout via mne. (Still checks for valid data using mne)")
    misc_group.add_argument("--connection_error_folder", default=None, type=str, help="If provided, save connection errors to this folder. Helps determine access issues after a large download.")
    misc_group.add_argument("--save_raw", action='store_true', default=False, help="Save the data as a raw csv")
    misc_group.add_argument("--event_from_backend", action='store_true', default=False, help="Use backend software to try and infer events.")
    misc_group.add_argument("--overwrite", action='store_true', default=False, help="Overwrite existing records with the same bids keywords.")
    misc_group.add_argument("--anonymize", action='store_true', default=False, help="Anonymize the data before writeout.")
    args = parser.parse_args()

    # Basic clean-up of path names
    if args.bids_root[-1] != '/': args.bids_root+='/'

    # Main Logic
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
