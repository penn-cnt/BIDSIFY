import os
import string
import numpy as np
import pandas as PD
from sys import argv
from nltk.corpus import stopwords
from datetime import datetime as DT
from nltk.tokenize import RegexpTokenizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import CountVectorizer

# Unique typing imports
from mne.io.edf.edf import RawEDF 
from mne.annotations import Annotations

# Get stop words
from nltk.data import find as NLFIND
if not NLFIND('corpora/stopwords'):
    import nltk
    nltk.download('stopwords')

# Local Imports
from components.internal.observer_handler import *

class phi_observer(Observer):

    def listen_data(self):
        
        if self.args.backend.lower() == 'mne':
            # Send the data through the PHI checker
            self.valid_data = self.PHI.check_for_phi(self.annotations,verbose=False)
            if not self.valid_data:
                print(f"Skipping   {self.file_name}. (Potential PHI found.)")
        elif self.args.backend.lower() == 'nibabel':
            # Send the data through the PHI checker
            self.valid_data = self.PHI._check_for_phi_nibabel(self.data,verbose=False)
            #if not self.valid_data:
            #    print(f"Skipping   {self.file_name}. (Potential PHI found.)")

class phi_handler:

    def __init__(self,input_data=None,backend='MNE'):

        # Determine input_data type to get relevant annotations
        if backend.lower() == 'mne':
            if input_data != None:
                if type(input_data) == RawEDF:
                    self.annotation = input_data.annotation
                elif type(input_data) == Annotations:
                    self.annotation = input_data

    def _check_for_phi_nibabel(self,image,phi_tolerance=1.5,verbose=True):

        # Set verbosity
        self.verbose = verbose

        # Store the tolerance to the class instance
        self.phi_tolerance = phi_tolerance

        # Convert description header field to an annotation like object
        description  = image.header['descrip'].astype(str).tolist()
        if type(description) == list:
            self.annotation_list = description
        elif type(description) == str:
            self.annotation_list = [description]

        # Run the PHI checker
        self.load_names()
        return self.check_annotations()

    def check_for_phi(self,annotation=None,phi_tolerance=1.5,backend='MNE',verbose=True):

        # Set verbosity
        self.verbose = verbose

        # Store the tolerance to the class instance
        self.phi_tolerance = phi_tolerance

        # Check if an annotation object was created when initalizing the class
        if annotation != None:
            self.annotation = annotation

        # Make a simple list of annotations
        if backend.lower() == 'mne':

            def get_annot(iannot):
                return iannot['description']
            self.annotation_list = list(map(get_annot,self.annotation))

        # Run the process for checking data
        self.load_names()
        return self.check_annotations()

    def load_names(self,namepath=None):

        # Try to establish location of names
        if namepath == None:
            proposed_name_path = '/'.join(os.path.abspath(__file__).split('/')[:-3])+'/samples/phi/names/combined_names_census2010_ssa2021.txt'
        else:
            proposed_name_path = namepath

        # Check if we've already loaded the names before, if not, read into instance and make cosine vector object
        if not hasattr(self,'phinames'):

            # Save names
            self.phinames          = PD.read_csv(proposed_name_path,names=['names'])
            self.phinames['names'] = self.phinames['names'].str.lower()

        # Save vectorized names
        self.CV = CountVectorizer(analyzer='char')
        self.CV.fit([string.ascii_lowercase])
        self.vectors_cosine = [self.CV.transform([iname]).toarray() for iname in self.phinames.names.values]
        self.vectors_jacard = [[*iname] for iname in self.phinames.names.values]

    def exact_match(self,itoken):

        potential_matches = self.phinames.loc[self.phinames.names==itoken]
        if potential_matches.shape[0] > 0:
            if self.verbose:
                print(f"Possible PHI leak found with string {itoken} matching known names in registry.")
            return False
        else:
            return True
        
    def approximate_match(self,itoken):

        # Get the cosine score
        cosine_vector = self.CV.transform([itoken]).toarray()
        for idx in range(len(self.vectors_cosine)):
            
            # Get the cosine score
            cosine_score = cosine_similarity(cosine_vector,self.vectors_cosine[idx])[0][0]

            # Get the jacardian score
            jacard_vector = [*itoken]
            if len(jacard_vector) > len(self.vectors_jacard[idx]):
                jacard_score = (np.array(self.vectors_jacard[idx])==np.array((jacard_vector[:len(self.vectors_jacard[idx])]))).sum()/len(jacard_vector)
            else:
                jacard_score = (np.array(jacard_vector)==np.array((self.vectors_jacard[idx][:len(jacard_vector)]))).sum()/len(self.vectors_jacard[idx])

            # Logic for potential phi hits
            if (cosine_score+jacard_score)>=self.phi_tolerance:
                if self.verbose:
                    print(f"Possible PHI leak found with string {itoken} compared to {self.phinames.names.values[idx]}.")
                return False
        return True

    def check_annotations(self):

        # Create tokens of the current annotation
        stop_words = set(stopwords.words('english'))
        tokenizer  = RegexpTokenizer(r'\w+')

        # Loop over annotations
        for iannot in self.annotation_list:

            # Create the token list
            tokens = tokenizer.tokenize(iannot.lower())

            # Filter the tokens slightly to non stop words or numerics
            filtered_tokens           = []
            partially_filtered_tokens = [token for token in tokens if token not in stop_words and len(token) > 1]
            for itoken in partially_filtered_tokens:
                try:
                    float(itoken)
                except:
                    filtered_tokens.append(itoken)

            # Loop over tokens to perform exact and approximate matches
            for itoken in filtered_tokens:
                exact_flag  = self.exact_match(itoken)
                approx_flag = self.approximate_match(itoken)

            if not exact_flag or not approx_flag:
                return False
        return True