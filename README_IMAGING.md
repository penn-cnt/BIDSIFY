# Imaging BIDS Creation

Imaging BIDS is a package designed to convert imaging data into BIDS-compliant datasets. As the push for standardized datasets grows, harmonizing how we collect and store data has become increasingly important.

***Note.*** This is not meant to replace larger tools like EZ Bids. It is designed to be a script solution for use when a web-based platform, or sharing data onto an external server, is not viable.

## Features

Imaging BIDS uses a datalake of known protocols at HUP to try and assign the correct BIDS keywords to your data. It also informs the users of its choices, and allows for a human in the loop to correct any mistakenly assigned keywords. New keywords can be saved for later use.

To do this, the imaging data requires a .json file associated with the data file, and the `ProtocolName` field cannot be missing.

## Example Usage

```
python EEG_BIDS.py --nifti --datalake ~/Documents/GitHub/CNT-codehub/user_data/RAW_IMAGING_DATA/R61_datalake.pickle --bids_root /Users/bjprager/Documents/GitHub/CNT-codehub/user_data/tests/single/ --input_csv samples/inputs/sample_nifti_inputs.csv
```