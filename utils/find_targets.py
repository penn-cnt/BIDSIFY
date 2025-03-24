import os
import nltk
import pickle
import argparse
import numpy as np
import pandas as PD
from sys import exit
from tqdm import tqdm
from nltk.corpus import stopwords
from nltk.data import find as NLFIND
from nltk.tokenize import RegexpTokenizer
from pyedflib.highlevel import read_edf_header

if not NLFIND('corpora/stopwords'):
    import nltk
    nltk.download('stopwords')

def return_tokens(istr):

    stop_words      = set(stopwords.words('english'))
    tokenizer       = RegexpTokenizer(r'\w+')
    tokens          = tokenizer.tokenize(istr.lower())
    filtered_tokens = [token for token in tokens if token not in stop_words and len(token) > 1]
    return filtered_tokens

def make_tokendict(args):

    # Get all the target dictionaries
    target_files = []
    for dirpath, dirs, files in os.walk(args.rootdir):  
        for filename in files:
            fname = os.path.join(dirpath,filename) 
            if fname.endswith('targets.pickle'): 
                target_files.append(fname)
    
    # Loop through each file and read in the target information. Then tokenize and store to final search dictionary
    lookup_dict = {}
    for ifile in tqdm(target_files, desc='Creating file tokens',total=len(target_files),leave=False):
        target_dict = pickle.load(open(ifile,"rb"))
        annot_str   = target_dict['annotation']
        target_str  = target_dict['target']
        all_tokens  = return_tokens(annot_str)
        all_tokens  = all_tokens + return_tokens(target_str)
        
        # Loop over the tokens to add to the lookup
        for itoken in all_tokens:
            if itoken not in lookup_dict.keys():
                lookup_dict[itoken]          = {}
                lookup_dict[itoken]['count'] = 0
                lookup_dict[itoken]['files'] = []

            # Find the proposed datafile path
            datafile = ifile.replace('_targets.pickle','.edf')

            # If we want to try the pickle backup, apply logic to figure out if edf or pickle
            if args.pickle_backup:
                if not os.path.exists(datafile):
                    datafile = ifile.replace('_targets.pickle','.pickle')
                else:
                    try:
                        read_edf_header(datafile)
                    except OSError:
                        datafile = ifile.replace('_targets.pickle','.pickle')

            # Store the results to the lookup dictionary
            lookup_dict[itoken]['count'] += 1
            lookup_dict[itoken]['files'].append(datafile)
    return lookup_dict

if __name__ == '__main__':

    # Argument parsing
    parser = argparse.ArgumentParser(description="iEEG to bids conversion tool.")
    parser.add_argument("--rootdir", type=str, help="Root directory to search within for target data.")
    parser.add_argument("--outfile", type=str, help="Path to save results to")
    parser.add_argument("--tokendict", type=str, default=None, help="Optional. Path to the token dictionary if already generated. Makes subsequent searches against large databases faster.")
    parser.add_argument("--pickle_backup", action='store_true', default=False, help="Check if edf data file can be read in. If not, try to use a pickle file.")
    args = parser.parse_args()

    # If token dict provided, load that. Otherwise, make dict.
    if args.tokendict != None:
        if os.path.exists(args.tokendict):
            lookup_dict = pickle.load(open(args.tokendict,"rb"))
        else:
            if args.rootdir == None:
                raise Exception("If creating a token dictionary for the first time, must provide root directory to search within using --rootdir.")

            # Make and save the tokendict
            print("Creating token dictionary. This may take awhile")
            lookup_dict = make_tokendict(args)
            pickle.dump(lookup_dict,open(args.tokendict,"wb"))
    else:
        if args.rootdir == None:
            raise Exception("If creating a token dictionary for the first time, must provide root directory to search within using --rootdir.")
        lookup_dict = make_tokendict(args)
    
    # Make a pretty lookup table for the user
    index         = np.array(list(lookup_dict.keys())).reshape((-1,1))
    counts        = np.array([lookup_dict[ikey]['count'] for ikey in lookup_dict.keys()]).reshape((-1,1))
    DF            = PD.DataFrame(counts,columns=['count'])
    DF['keyword'] = index
    DF            = DF.sort_values(by=['keyword'],ascending=True)
    DF.set_index('keyword',drop=True,inplace=True)
    
    # Print the results
    with PD.option_context('display.max_rows', None, 'display.max_columns', None):
        print(DF)

    # Ask the user for which keyword to save the filepaths for
    tokens = input("Enter the keyword (or comma separated keywords) you want the file list for? (Q/q quit). ")
    if tokens.lower() == 'q':exit()
    tokenlist = tokens.split(',')
    for idx,itoken in enumerate(tokenlist):tokenlist[idx]=itoken.lower()
    
    # Save the files to the output file
    outfiles = []
    for itoken in tokenlist:
        if itoken in DF.index:
            ifiles = lookup_dict[itoken]['files'] 
            outfiles.extend(ifiles)
        else:
            print(f"Could not find your token `{itoken}` in the token list from observed files.")

    # Make a dataframe, drop duplicates (which arise from list of tokens), and save
    DF = PD.DataFrame(outfiles,columns=['filepath'])
    DF.drop_duplicates(inplace=True)
    DF.to_csv(args.outfile,index=False)
    fp = open(args.outfile+'.keys','w')
    fp.write(tokens)
    fp.close()
