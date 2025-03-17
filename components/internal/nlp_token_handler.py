import os
import pickle
from nltk.corpus import stopwords
from nltk.data import find as NLFIND
from nltk.tokenize import RegexpTokenizer


# Local Imports
from components.internal.observer_handler import *

# Get stop words
if not NLFIND('corpora/stopwords'):
    import nltk
    nltk.download('stopwords')

class nlp_token_observer(Observer):

    def listen_postprocess(self):

        NLPTKN = nlp_token_handler(self.args.bids_root,self.data_path,self.target_path,f"{self.args.bids_root}filetokens.dict")
        NLPTKN.workflow()

class nlp_token_handler:

    def __init__(self,bids_root,data_path,target_path,token_path):
        self.bids_root   = bids_root
        self.data_path   = data_path
        self.target_path = target_path
        self.token_path  = token_path

    def workflow(self):

        # Obtain the token object
        self.token_pointer()

        # Get the tokens from the target object
        self.get_tokens()

        # Update the filetoken object
        self.update_tokendict()

        # Save the new filetoken object
        self.save_tokendict()

    def token_pointer(self):

        if os.path.exists(self.token_path):
            
            # Grab existing token dictionary
            fp              = open(self.token_path,'rb')
            self.token_dict = pickle.load(fp)
            fp.close()
        else:

            # Create token dictionary
            self.token_dict = {}

    def get_tokens(self):

        def return_tokens(istr):

            stop_words      = set(stopwords.words('english'))
            tokenizer       = RegexpTokenizer(r'\w+')
            tokens          = tokenizer.tokenize(istr.lower())
            filtered_tokens = [token for token in tokens if token not in stop_words and len(token) > 1]
            return filtered_tokens

        # Grab the target data
        fp          = open(self.target_path,'rb')
        target_dict = pickle.load(fp)
        fp.close()

        # Extract the tokens
        annot_str       = target_dict['annotation']
        target_str      = target_dict['target']
        all_tokens      = return_tokens(annot_str)
        self.all_tokens = all_tokens + return_tokens(target_str)

    def update_tokendict(self):

        for itoken in self.all_tokens:

            if itoken not in self.token_dict.keys():
                self.token_dict[itoken]          = {}
                self.token_dict[itoken]['count'] = 1
                self.token_dict[itoken]['files'] = [self.data_path]
            else:
                if self.data_path not in self.token_dict[itoken]:
                    self.token_dict[itoken]['count'] += 1
                    self.token_dict[itoken]['files'].append(self.data_path)
        
    def save_tokendict(self):
        # Grab existing token dictionary
        fp = open(self.token_path,'wb')
        pickle.dump(self.token_dict,fp)
        fp.close()