# EEG BIDS Creation

EEG Bids is a package designed to convert timeseries data into BIDS-compliant datasets. As the push for standardized datasets grows, harmonizing how we collect and store data has become increasingly important.

## Features

Currently, the package supports:

- Pulling data from iEEG.org (using the `--ieeg` flag)
- Converting raw EDF files to BIDS format (using the `--edf` flag)
- Converting csv files to BIDS format (using the `--jar` flag)
    - **Note**: This is an experimental feature for Pennsieve and is not well supported yet.

We aim to make it easy to add new data pull methods by using an observer coding style, allowing new code to integrate with just a few lines. For more details, refer to the contribution section.

Additionally, the package generates various sidecar files used by other components of the CNT codehub for a range of tasks.

## Usage

At present, EEG BIDS is designed to download and/or convert data to the preferred data format for epilepsy data, BIDS. Within the CNT, iEEG.org is a common data source, but the python API, data standards, and specifics of BIDS present a number of hurdles for conversion. This script aims to resolve these issues and streamline the process. We explain a few key concepts for usage here.

### Selecting a data source
You can select a data source from the `data source options`, which can be found by using the `--help` option.

At present we support:
1. `--ieeg`: This options tells the script to pull from iEEG.org. This option requires you to provide at minimum:
    - iEEG.org Username
    - Dataset id
    - Start time
    - Duration
2. `--edf`: This option will take a local .edf file and create/place it into a BIDS structure for you. This option requires you to provide at minimum:
    - Dataset path

### Creating a list of files to pull
You can download/convert multiple files at once using the `--input_csv` flag. 

#### Inputs to input_csv

- `orig_filename`
    - Required. The original filename on iEEG.or or on your local machine.
- `start`
    - Optional. The start time of the clip.
    - Required if downloading from iEEG.org without using the annotation clip times.
- `duration`
    - Optional. The duration of the clip.
    - Required if downloading from iEEG.org without using the annotation clip times.
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

#### Example Inputs

You can find examples of various input files [here](https://github.com/penn-cnt/CNT-codehub/tree/main/scripts/codehub/utils/acquisition/BIDS/samples/inputs/).

- `download_by_annotations.csv`
    - This sample is used for downloading all of the data within a iEEG.org file according to the annotation layer times.
- `download_by_times.csv`
    - This sample is used for downloading specific time segments from iEEG.org.
- `sample_edf_inputs.csv`
    - This sample is for converting individual edf files on your computer into a BIDS compliant format.

### Exploring my data after conversion
In order to find specific files, and to avoid duplicate downloads, the code creates a manifest document that stores the original filename and resulting BIDS keywords for every file. By default this file is called `subject_map.csv` and is located in the bids root directory.

The output name for this file can be changed using the `--data_record` keyword.

## Sample commands

We provide a few sample commands here. Note, all examples utilize a username and filepaths that you will need to update to reflect your own system and credentials.

```
#### Single download without an input csv. Should create subject 562, session 1, run 1
`python EEG_BIDS.py --ieeg --username BJPrager --bids_root /Users/bjprager/Documents/GitHub/CNT-codehub/user_data/tests/single/  --dataset EMU0562_Day01_1 --start 2925000000 --duration 10000000`

#### Single download without an input csv. Set subject to HUP001. Default to session 1, run 1
`python EEG_BIDS.py --ieeg --username BJPrager --bids_root /Users/bjprager/Documents/GitHub/CNT-codehub/user_data/tests/single/  --dataset EMU0562_Day01_1 --start 2925000000 --duration 10000000 --subject HUP001`

#### Run the code in a debug mode. Prevent output. Good for testing.
***Note***: iEEG.org contains lots of different datasets, and sometimes a download may not work. This can range from an ill-formed request, server timeout, bad data, etc. This will let you know what went wrong.

`python EEG_BIDS.py --ieeg --username BJPrager --bids_root /Users/bjprager/Documents/GitHub/CNT-codehub/user_data/tests/single/  --dataset EMU0562_Day01_1 --start 2925000000 --duration 10000000 --debug`

#### Download with an input csv that uses specific times
`python EEG_BIDS.py --ieeg --username BJPrager --bids_root /Users/bjprager/Documents/GitHub/CNT-codehub/user_data/tests/single/  --input_csv utils/acquisition/BIDS/samples/inputs/download_by_times.csv`

#### Single raw edf file conversion without inputs. Should create subject HUP001, session 1, run 1
`python EEG_BIDS.py --edf --username BJPrager --bids_root /Users/bjprager/Documents/GitHub/CNT-codehub/user_data/tests/single/  --dataset /Users/bjprager/Documents/GitHub/CNT-codehub/user_data/BIDS/sub-00001/ses-preimplant001/eeg/sub-00001_ses-preimplant001_task-task_run-01_eeg.edf --subject HUP001 --uid_number 1`
```

#### Single edf
`python EEG_BIDS.py --edf --username BJPrager --bids_root /Users/bjprager/Documents/GitHub/CNT-codehub/user_data/tests/single/  --dataset /Users/bjprager/Documents/GitHub/CNT-codehub/user_data/epipy_testing/BIDS/sub-HUP00001_ses-emu1648day01file1_task-rest_run-0002_eeg.edf --subject HUP001 --uid_number 1 --session 1 --run 1 --overwrite --target /Users/bjprager/Documents/GitHub/CNT-codehub/user_data/epipy_testing/BIDS/sub-HUP00001_ses-emu1648day01file1_task-rest_run-0002_eeg_targets.pickle`

#### Multi edf
`python EEG_BIDS.py --edf --username BJPrager --bids_root /Users/bjprager/Documents/GitHub/CNT-codehub/user_data/tests/single/  --dataset /Users/bjprager/Documents/GitHub/CNT-codehub/user_data/epipy_testing/BIDS/sub-HUP00001_ses-emu1648day01file1_task-rest_run-0002_eeg.edf --input_csv samples/inputs/sample_edf_inputs_w_target.csv --overwrite`

#### Find targets
`python find_targets.py --tokendict /Users/bjprager/Documents/GitHub/CNT-codehub/user_data/tests/single/filetokens.dict --outfile sample_files`

## Assigning a `--uid` 
This is an additional flag used by the CNT to create a unique identifier for each patient that may not map to the BIDS subject keyword. Each dataset may have slightly different naming conventions, but this identifier is meant to let us map data back a redcap ID or MRN when viewed behind a clinical firewall. 

If making a dataset for your own use, you can ignore this value. If you wish to make a lab dataset, please reach out to the data team for help with determining the correct uid to assign.

## Large data pulls
`EEG BIDS` currently provides a multithreading option to download larger collections of data quickly.

**Note** If planning to download lots of data to one of the lab servers, please reach out to the data team to discuss the best strategy. 

## Repository Breakdown

We provide a quick overview of the different parts of the repository here.

### Files

#### `EEG_BIDS.py`
This is the user-interface portion of the code. You can access detailed usage instructions by running:
```bash
python EEG_BIDS.py --help
```

### Folders

#### `modules`
This folder contains the backend code that makes up EEG BIDS, providing functionality to convert and handle timeseries data.

#### `samples`
Includes numerous sample CLI calls and input files to help you get started using the package.

## Installation

EEG_BIDS uses a number of specific packages, and it can be time consuming to build an environment just for the purposes of this script. We recommend starting with the directions for installing the cnt-codehub python environment found [here](https://github.com/penn-cnt/CNT-codehub/blob/main/README.md). You can then modify the cnt_codehub.yaml file as needed to match your needs.

## Contributing
(In Progress)

If adding support for new data inputs, you can make a new object in components.public that reads in your raw data and generates the proper bids keywords. 

Once you have read in your data and generated keywords, you just need to alert the observers to generate the actual backend data. You can do this by
