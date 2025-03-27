# BIDSIFY

BIDSIFY is a package designed to convert various epilepsy data sources into BIDS-compliant datasets without internet connection or third party data hosting. As the push for standardized datasets grows, harmonizing how we collect and store data has become increasingly important.

## Table of Contents
- [Requirements](#Requirements)
- [Installation](#Installation)
- [Supported Data Types](#Supported-Data-Types)
- [Examples](#examples)

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

- EDF (using the `--edf` flag)
- iEEG.org (using the `--ieeg` flag)
- Pennsieve (using the `--pennsieve` flag)
    - **Note**: This option is not yet fully implemented as the Pennsieve team works on a Python API.

### Imaging
We currently support the following imaging data sources

- Nifti data (using the `--nifti` flag)

### Future Data Sources
Future releases will change the use of specific input flags (i.e. --edf,--nifti,etc) to --timeseries, --imaging or similar logic. At present the back-end logic can read in different data types without breaking the workflow, but at the time of implementation the only required use cases have centered on these specific data formats.

#### Adding new data sources
The recommended method for adding a new data source is to add a new handler for the data source in the components/public folder. This public facing handler is meant to manage the general flow of data processing. Code responsible for actually reading in timeseries or imaging data, as well as running any postprocessing, is available within the components/internal folder, and can be called by attaching their associated observer method. For more information, we recommend visiting here.

## Usage

There are a number of different options inherent to this package and means to streamline the BIDS creation using sidecar files (typically .csv tabular data). We explain a few of these concepts, and present some examples below.

## Example

At present, EEG BIDS is designed to download and/or convert data to the preferred data format for epilepsy data, BIDS. Within the CNT, iEEG.org is a common data source, but the python API, data standards, and specifics of BIDS present a number of hurdles for conversion. This script aims to resolve these issues and streamline the process. We explain a few key concepts for usage here.

### Creating a list of files to pull
You can download/convert multiple files at once using the `--input_csv` flag. 

#### Inputs to input_csv

##### Generic Fields
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
- `task`
    - Optional. Task to assign to the data. (i.e. `rest`)
- `target`
    - Optional. Additional information to keep associated with the dataset in a `*_targets.pickle` file. This could be epilepsy diagnosis, sleep stage, etc.

#### Timeseries Fields

- `start`
    - Optional. The start time of the dataset.
    - **Note** Required if downloading from iEEG.org without using the annotation clip times.
- `duration`
    - Optional. The duration of the clip.
    - **Note** Required if downloading from iEEG.org without using the annotation clip times.

#### Imaging Fields

#### Example Inputs

You can find examples of various input files [here](https://github.com/penn-cnt/CNT-codehub/tree/main/scripts/codehub/utils/acquisition/BIDS/samples/inputs/).

- `download_by_annotations.csv`
    - This sample is used for downloading all of the data within a iEEG.org file according to the annotation layer times.
- `download_by_times.csv`
    - This sample is used for downloading specific time segments from iEEG.org.
- `sample_edf_inputs.csv`
    - This sample is for converting individual edf files on your computer into a BIDS compliant format.

<!---
### Exploring my data after conversion
In order to find specific files, and to avoid duplicate downloads, the code creates a manifest document that stores the original filename and resulting BIDS keywords for every file. By default this file is called `subject_map.csv` and is located in the bids root directory.

The output name for this file can be changed using the `--data_record` keyword.

## Sample commands

We provide a few sample commands here. Note, all examples utilize a username and filepaths that you will need to update to reflect your own system and credentials.

```
#### Single download without an input csv. Should create subject 562, session 1, run 1
`python BIDSIFY.py --ieeg --username BJPrager --bids_root /Users/bjprager/Documents/GitHub/CNT-codehub/user_data/tests/single/  --dataset EMU0562_Day01_1 --start 2925000000 --duration 10000000`

#### Single download without an input csv. Set subject to HUP001. Default to session 1, run 1
`python BIDSIFY.py --ieeg --username BJPrager --bids_root /Users/bjprager/Documents/GitHub/CNT-codehub/user_data/tests/single/  --dataset EMU0562_Day01_1 --start 2925000000 --duration 10000000 --subject HUP001`

#### Run the code in a debug mode. Prevent output. Good for testing.
***Note***: iEEG.org contains lots of different datasets, and sometimes a download may not work. This can range from an ill-formed request, server timeout, bad data, etc. This will let you know what went wrong.

`python BIDSIFY.py --ieeg --username BJPrager --bids_root /Users/bjprager/Documents/GitHub/CNT-codehub/user_data/tests/single/  --dataset EMU0562_Day01_1 --start 2925000000 --duration 10000000 --debug`

#### Download with an input csv that uses specific times
`python BIDSIFY.py --ieeg --username BJPrager --bids_root /Users/bjprager/Documents/GitHub/CNT-codehub/user_data/tests/single/  --input_csv utils/acquisition/BIDS/samples/inputs/download_by_times.csv`

#### Single raw edf file conversion without inputs. Should create subject HUP001, session 1, run 1
`python BIDSIFY.py --edf --username BJPrager --bids_root /Users/bjprager/Documents/GitHub/CNT-codehub/user_data/tests/single/  --dataset /Users/bjprager/Documents/GitHub/CNT-codehub/user_data/BIDS/sub-00001/ses-preimplant001/eeg/sub-00001_ses-preimplant001_task-task_run-01_eeg.edf --subject HUP001 --uid_number 1`
```

#### Single edf
`python BIDSIFY.py --edf --bids_root /Users/bjprager/Documents/GitHub/CNT-codehub/user_data/tests/single/  --dataset /Users/bjprager/Documents/GitHub/CNT-codehub/user_data/epipy_testing/BIDS/sub-HUP00001_ses-emu1648day01file1_task-rest_run-0002_eeg.edf --subject HUP001 --uid_number 1 --session 1 --run 1 --overwrite --target /Users/bjprager/Documents/GitHub/CNT-codehub/user_data/epipy_testing/BIDS/sub-HUP00001_ses-emu1648day01file1_task-rest_run-0002_eeg_targets.pickle`

#### Multi edf with anonymization/phi checks
`python BIDSIFY.py --edf  --bids_root /Users/bjprager/Documents/GitHub/CNT-codehub/user_data/tests/single/ --input_csv samples/inputs/sample_edf_inputs_w_target.csv --anonymize`

#### Download from iEEG.org using an input table with times
`python BIDSIFY.py --ieeg --username BJPrager --bids_root /Users/bjprager/Documents/GitHub/CNT-codehub/user_data/tests/single/  --input_csv samples/inputs/download_by_times.csv`

#### Download from iEEG.org using an input table with annotation layers
`python BIDSIFY.py --ieeg --username BJPrager --bids_root /Users/bjprager/Documents/GitHub/CNT-codehub/user_data/tests/single/  --annotations --input_csv samples/inputs/download_by_annotations.csv`

#### Single Nifti
`python BIDSIFY.py --nifti --bids_root /Users/bjprager/Documents/GitHub/CNT-codehub/user_data/tests/single/ --dataset /Users/bjprager/Documents/GitHub/CNT-codehub/user_data/RAW_IMAGING_DATA/data/sub-RID0280_AX_FLAIR_4_20161010125629.nii  --subject_number HUP001 --uid_number 0 --session 001 --run 01 --imaging_data_type anat --imaging_scan_type MR --imaging_modality flair --imaging_task None --imaging_acq ax --imaging_ce None`

#### Multi Nifti
`python BIDSIFY.py --nifti --datalake datalakes/R61_datalake.pickle --bids_root /Users/bjprager/Documents/GitHub/CNT-codehub/user_data/tests/single/ --input_csv samples/inputs/sample_nifti_inputs.csv`

#### Find targets
`python utils/find_targets.py --tokendict /Users/bjprager/Documents/GitHub/CNT-codehub/user_data/tests/single/filetokens.dict --outfile sample_files`

## Assigning a `--uid` 
This is an additional flag used by the CNT to create a unique identifier for each patient that may not map to the BIDS subject keyword. Each dataset may have slightly different naming conventions, but this identifier is meant to let us map data back a redcap ID or MRN when viewed behind a clinical firewall. 

If making a dataset for your own use, you can ignore this value. If you wish to make a lab dataset, please reach out to the data team for help with determining the correct uid to assign.

## Large data pulls
`EEG BIDS` currently provides a multithreading option to download larger collections of data quickly.

**Note** If planning to download lots of data to one of the lab servers, please reach out to the data team to discuss the best strategy. 

## Repository Breakdown

We provide a quick overview of the different parts of the repository here.

### Files

#### `BIDSIFY.py`
This is the user-interface portion of the code. You can access detailed usage instructions by running:
```bash
python BIDSIFY.py --help
```

### Folders

#### `modules`
This folder contains the backend code that makes up EEG BIDS, providing functionality to convert and handle timeseries data.

#### `samples`
Includes numerous sample CLI calls and input files to help you get started using the package.



## Contributing
(In Progress)

If adding support for new data inputs, you can make a new object in components.public that reads in your raw data and generates the proper bids keywords. 

Once you have read in your data and generated keywords, you just need to alert the observers to generate the actual backend data. You can do this by
-->
