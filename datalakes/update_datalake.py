import sys
import pickle
import argparse
import numpy as np
import pandas as PD
from prettytable import PrettyTable

class data_view:
    """
    Generate views of the datalake.
    """

    def __init__(self):

        # Create variables for initial display
        self.view_manager = True
        self.dataslice    = self.dataframe.copy()
        
        # Create loop for substring searching
        while self.view_manager:
            self.display()
            user_input = ""
            while user_input not in ['y','n']:
                user_input=input("Search for protocol by substring (y/n)? ").lower()
            if user_input == 'n':
                self.view_manager = False
            else:
                substr = input("Please enter substring to search for: ").lower()
                self.create_dataslice(substr)

    def create_dataslice(self,substr):
        """
        Creates a temporary slice of the dataframe for viewing purposes only.

        Args:
            substr (str): Substring of the protocol names to display.
        """
        new_index = []
        for ival in list(self.dataframe.index):
            if substr in ival.lower():
                new_index.append(ival)
        self.dataslice = self.dataframe.loc[new_index]

    def display(self):
        
        # Initialize a pretty table for easy reading
        table = PrettyTable()
        table.field_names = ['protocol'] + self.dataslice.columns.tolist()

        # Step through the data and populate the pretty table with the current dataslice
        for idx, row in enumerate(self.dataslice.itertuples()):
                table.add_row([self.dataslice.index[idx]] + list(row[1:]))

        # Display pretty table
        print(table)

class data_update:

    def __init__(self,outfile):
        self.outfile = outfile

    def manual_update(self):

        # Provide user instruction
        print("Please provide new data row in comma separated variable format.")
        print("Columns without a value should be left blank.")
        print("Columns are: protocol,"+','.join(self.dataframe.columns))

        while True:
            user_input = input()
            user_array = user_input.split(',')
            if len(user_array) == 7:
                break
            else:
                print("Invalid input.")

        # Append new entry in memory and display
        iDF            = PD.DataFrame([user_array[1:]],index=[user_array[0]],columns=self.dataframe.columns)
        self.dataframe = PD.concat([self.dataframe,iDF])
        self.dataframe = self.dataframe.loc[~self.dataframe.index.duplicated(keep='last')]
        data_view.create_dataslice(self,user_array[0])
        data_view.display(self)

        # Confirm changes
        user_input = ""
        while user_input not in ['y','n']:
            user_input=input("Confirm changes (y/n)? ").lower()
        
        # Make dictionary
        self.datalake[self.site][user_array[0]] = {}
        self.datalake[self.site][user_array[0]]['scan_type'] = user_array[1]
        self.datalake[self.site][user_array[0]]['data_type'] = user_array[2]
        self.datalake[self.site][user_array[0]]['modality']  = user_array[3]
        self.datalake[self.site][user_array[0]]['task']      = user_array[4]
        self.datalake[self.site][user_array[0]]['acq']       = user_array[5]
        self.datalake[self.site][user_array[0]]['ce']        = user_array[6]

        # Save output if requested
        pickle.dump(self.datalake,open(self.outfile,'wb'))

    def bulk_update(self,upload_file):

        # Provide user instruction
        print("Attempting to read in %s." %(upload_file))

        # Read in upload and check for column headers
        cols      = self.dataframe.columns
        iDF       = PD.read_csv(upload_file,names=cols,index_col=0)
        intersect = np.intersect1d(cols,iDF.iloc[0].values)
        if intersect.size == cols.size:
            iDF = PD.read_csv(upload_file,index_col=0)
        elif intersect.size == 0:
            pass
        else:
            raise Exception("Unable to parse columns. Please provide data without column names or matching names to the datalake.")

        # Append new entry in memory and display
        self.dataframe = PD.concat([self.dataframe,iDF])
        self.dataframe = self.dataframe.loc[~self.dataframe.index.duplicated(keep='last')]
        self.dataslice = iDF.copy()
        data_view.display(self)

        # Confirm changes
        user_input = ""
        while user_input not in ['y','n']:
            user_input=input("Confirm changes (y/n)? ").lower()
        
        # Save output if requested
        print(self.dataframe)
        pickle.dump(self.dataframe,open(self.outfile,'wb'))
        

class data_manager(data_view,data_update):

    def __init__(self, args):
        self.datalake = pickle.load(open(args.datalake,"rb"))
        self.site     = args.site
        self.datalake_to_dataframe()
        data_update.__init__(self,args.output)

        # Case statement for usage type
        if args.review:
            data_view.__init__(self)
        if args.manual:
            data_update.manual_update(self)
        if args.upload:
            data_update.bulk_update(self,args.upload_file)

    def datalake_to_dataframe(self):
        """
        Restructure the nested dictionary to an easier format to work in.
        """

        # Get the protocol keys
        protocol_keys = list(self.datalake[self.site].keys())

        # Loop over keys to make dataframe
        for idx,ikey in enumerate(protocol_keys):
            iDF       = PD.DataFrame()
            iDF[ikey] = self.datalake[self.site][ikey]
            if idx>0:
                self.dataframe = PD.concat([self.dataframe,iDF.T])
            else:
                self.dataframe = iDF.T
        self.dataframe.sort_index(inplace=True)
        self.dataframe = self.dataframe[self.dataframe.index.notnull()]

def argparser():

    # Command line options needed to obtain data.
    parser   = argparse.ArgumentParser()
    parser.add_argument('-D', '--datalake', help='Path to pickled datalake file. If not found, a new file will be generated.')
    parser.add_argument('-R', '--review', default=False, action='store_true', help='Review protocol information. Default.')
    parser.add_argument('-U', '--upload', default=False, action='store_true', help='Upload new protocol information.')
    parser.add_argument('-M', '--manual', default=False, action='store_true', help='Manually input new protocol information.')
    parser.add_argument('-O', '--output', help='Output datalake. By default same as input.')
    parser.add_argument('-S', '--site', default="HUP", help='Institution site.')
    parser.add_argument('--upload_file', help='If uploading, path to a csv file with same dimensions and column order as datalake.')
    args = parser.parse_args()

    # Make sure all command line options filled
    flag_sum = int(args.review)+int(args.upload)+int(args.manual)
    if flag_sum==0:
        args.review = True
    elif flag_sum > 1:
        print("Please specify only one mode.")
        sys.exit()

    # Confirm output path
    argsdict = vars(args)
    if not argsdict['output']:
        args.output = args.datalake

    return args
    
if __name__=="__main__":

    # Argument parsing
    args = argparser()

    # Update output if needed
    if args.output == None:
        args.output == args.datalake

    # Enter main body of code
    DM = data_manager(args)