# BIDSIFY

BIDSIFY is a package designed to convert various epilepsy data sources into BIDS-compliant datasets without internet connection or third party data hosting. As the push for standardized datasets grows, harmonizing how we collect and store data has become increasingly important.

## Table of Contents
- [Requirements](#Requirements)
- [Installation](#Installation)
- [Supported Data Types](#Supported-Data-Types)
- [Usage](#Usage)
- [Converting Multiple files](#Converting-Multiple-files)
- [Sample Commands](#Sample-Commands)
- [Upcoming Features](#Upcoming-features)

<!--
- [Contributing](#contributing)
- [License](#license)
-->

## Requirements

BIDSIFY requires Python 3.0+. It was developed for Mac and Linux systems. If using on a windows machine, pathing may become an issue. This is a known bug and is meant to be fixed in a future release.

## Installation

BIDSIFY is a purely pythonic means of creating BIDS datasets. It endeavors to do this without the need for an internet connection or data sharing. This allows for more secure BIDS generation that can take place behind clinical firewalls.

Below are two separate methods for installing BIDSIFY to your local workstation. If you are working behind a clinical firewall, and cannot download python packages, we recommend downloading the packages listed within [requirements.txt](./envs/requirements.txt) and installing them locally.

### Conda
1. Install Python
2. Clone the repo
   ```
    git clone https://github.com/penn-cnt/BIDSIFY
   ```
4. Create the conda environment
    ```
    conda env create --file BIDSIFY.yml
   ```
    By default, the provided conda yaml will set the environment name to bidify. You can change this in the bidsify.yml file, or provide an additional flag to this command along the lines of `-n <new-environment-name>`
5. Activate conda environment (Optional)
    ```
    conda activate bidsify
    ```
    If you set a new environment name, make sure to change bidsify to the correct environment name.
6. Attach default postprocessors (Optional)
    ```
    conda develop <path-to-cnt-codehub>
    ```
7. Test installation
   ```
   python BIDSIFY.py --example_input
   ```

### PIP
1. Install Python
2. Clone the repo
   ```
    git clone https://github.com/penn-cnt/BIDSIFY
   ```
4. Create the python environment
    ```
    pip -m venv <path-to-environment-folder>
   ```
    Your environment will be saved to a folder on the filesystem, and you will need to provide a path to a folder you want to use for storing these python packages.
5. Activate environment
    ```
    source <path-to-environment-folder>/bin/activate
    ```
    If you plan to use this package often, you may want to consider setting an alias to quickly enter this environment. For more on setting up aliases, please refer [here](https://www.geeksforgeeks.org/alias-command-in-linux-with-examples/).
6. Install packages
    ```
    pip install -r requirements.txt
    ```
7. Attach default postprocessors (Optional)
    ```
    export PYTHONPATH="${PYTHONPATH}:<path-to-cnt-codehub>"
    ```
   If you're working on a windows machine, or can't otherwise modify your path, you can also add a .pth file contain the path to the codehub to your environment folder's site packages.
    
8. Test installation
   ```
   python BIDSIFY.py --example_input
   ```
   
## Supported Data Types

BIDSIFY supports both time series and imaging data conversion to BIDS format. This is accomplished by creating different back-ends for data ingestion and BIDS path generation that can be called at run-time. We aim to provide the most general coverage with this alpha release, with design choices meant to ensure future data type additions can be done so as seamlessly as possible.

Currently, the package supports the following data sources:

### Timeseries
We currently support the following timeseries data sources

- EDF (using the `--eeg` flag)
- iEEG.org (using the `--ieeg` flag)
- Pennsieve (using the `--pennsieve` flag)
    - **Note**: This option is not yet fully implemented as the Pennsieve team works on a Python API.

### Imaging
We currently support the following imaging data sources

- Nifti data (using the `--imaging` flag)

#### Adding new data sources
The recommended method for adding a new data source is to add a new handler for the data source in the components/public folder. This public facing handler is meant to manage the general flow of data processing. Code responsible for actually reading in timeseries or imaging data, as well as running any postprocessing, is available within the components/internal folder, and can be called by attaching their associated observer method. For more information, we recommend visiting [here](https://github.com/penn-cnt/BIDSIFY/blob/main/documents/SOP/BIDSIFY.png).

## Usage

There are a number of different options inherent to this package and means to streamline the BIDS creation using sidecar files (typically .csv tabular data). We explain a few of these concepts, and present some examples below.

For a comprehensive list of commands, you should run

> python BIDSIFY.py --help

for a detailed help document. For printed examples in terminal, you can also run:

> python BIDSIFY.py --print_example

## Converting Multiple files

You can download/convert multiple files at once using the `--input_csv` flag. A breakdown of the allowed headers to the input csv file are as follows:

### Generic Fields
These fields are shared across both timeseries and imaging input_csv files.

- `orig_filename`
    - Required. The original filepath on your local machine or the dataset id for iEEG.org/Pennsieve.
- `uid`
    - Optional. A mapping number used when data is generated by the data team. Its a secret map to a PHI id that is persistant across different datasets.
- `subject_number`
    - Optional. Subject number to assign to the data. Defaults to 1. Can be entered as a string (i.e. `HUP001`)
- `session_number`
    - Optional. Session number to assign to the data. Defaults to 1. Can be entered as a string (i.e. `implant01`)
- `run_number`
    - Optional. Run number to assign to the data. Defaults to 1. 
- `target`
    - Optional. Additional information to keep associated with the dataset in a `*_targets.pickle` file. This could be epilepsy diagnosis, sleep stage, etc.

### Timeseries Fields

- `start`
    - Optional. The start time of the dataset.
    - **Note** Required if downloading from iEEG.org without using the annotation clip times.
- `duration`
    - Optional. The duration of the clip.
    - **Note** Required if downloading from iEEG.org without using the annotation clip times.
- `task`
    - Optional. Task to assign to the data. (i.e. `rest`)
      
### Imaging Fields

- `imaging_data_type`
    - Data Type of the image (i.e. anat/ct/etc.) 
- `imaging_scan_type`
    - Scan Type of the image (i.e. MRI/fMRI/etc.) 
- `imaging_modality`
    - Modality of the image (i.e. T1/flair/etc.)  
- `imaging_task`
    - Task of the image (rest/etc.)
- `imaging_acq`
    - Acquisition Type of the image (i.e. axial/sagittal/etc.) 
- `imaging_ce`
    - Contrast enrichment type of the image (i.e. ce-gad/etc.)

### Example Inputs

You can find specific examples of various input files [here](https://github.com/penn-cnt/BIDSIFY/tree/main/samples/inputs). The provided examples are:

#### EDF Examples
- `sample_edf_inputs.csv`
    - This sample is for converting individual edf files on your computer into a BIDS compliant format.
- `sample_edf_inputs_w_targets.csv`
    - This sample is for converting individual edf files on your computer into a BIDS compliant format with target data (i.e. epilepsy diagnosis, demographic info, etc,) associated.

#### iEEG.org Examples
- `download_by_annotations.csv`
    - This sample is used for downloading all of the data within a iEEG.org file according to the annotation layer times.
- `download_by_times.csv`
    - This sample is used for downloading specific time segments from iEEG.org.

#### Imaging Exmples
- `sample_nifti_inputs.csv`
    - This sample is for converting individual NIFTI files on your computer into a BIDS compliant format.

## Sample commands

We provide a few sample commands here. Note, all examples utilize a username and filepaths that you will need to update to reflect your own system and credentials.

### EDF Conversions

#### Single edf with BIDS keywords in CLI (and optional target file to include)
> python BIDSIFY.py --eeg --bids_root <path-to-bids-root>  --dataset <path-to-edf> --subject HUP001 --uid_number 1 --session 1 --run 1 --overwrite --target <path-to-target-file>

#### Multi edf with anonymization/phi checks and BIDS keywords in an input_csv
> python BIDSIFY.py --eeg  --bids_root <path-to-bids-root> --input_csv samples/inputs/sample_edf_inputs_w_target.csv --anonymize

### Nifti Datasets

#### Single Nifti
> python BIDSIFY.py --imaging --bids_root <path-to-bids-root> --dataset <path-to-nifti-file>  --subject_number HUP001 --uid_number 0 --session 001 --run 01 --imaging_data_type anat --imaging_scan_type MR --imaging_modality flair --imaging_task None --imaging_acq ax --imaging_ce None

### Single Nifti with interactive imaging keyword selection
>python BIDSIFY.py --imaging --bids_root <path-to-bids-root> --dataset <path-to-nifti-file> --subject_number HUP001 --uid_number 0 --session 001 --run 01

#### Multi Nifti with Datalake for easier keyword generation
> python BIDSIFY.py --imaging --datalake <path-to-datalake> --bids_root <path-to-bids-root> --input_csv samples/inputs/sample_nifti_inputs.csv

### iEEG.org Downloads

#### Download from iEEG.org using an input table with times
> python BIDSIFY.py --ieeg --username BJPrager --bids_root <path-to-bids-root>  --input_csv samples/inputs/download_by_times.csv

#### Download from iEEG.org using an input table with annotation layers
> python BIDSIFY.py --ieeg --username BJPrager --bids_root <path-to-bids-root>  --annotations --input_csv samples/inputs/download_by_annotations.csv

## Notes

A few important notes:

1. Overwriting data
    - If data with the same bids path already exists, BIDSIFY will skip creating new data by default. If you wish to overwrite data, you should use the `--overwrite` flag.

## Upcoming Features
1. Data Error Handling
    - When working with data that has errors, the code fails to save. There should be options added to either save data before and after a bad data segment or mask bad data. This shouldn't be the default, but for projects where large datasets are expected, the ability to excise bad segments should be allowed.
2. Imaging BIDS Dataset Information
    - At present, the BIDS dataset for imaging data is minimal. The required data is present, but the dataset meta information needs to be expanded.
