import os
import ast
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

        if hasattr(self,'target_path'):
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
            blacklist       = ['bjprager']
            tokenizer       = RegexpTokenizer(r'\w+')
            tokens          = tokenizer.tokenize(istr.lower())
            filtered_tokens = [token for token in tokens if token not in stop_words and len(token) > 1]
            outtokens       = []
            for token in filtered_tokens:
                tflag = True
                for iblacklist in blacklist:
                    if iblacklist in token:
                        tflag = False
                if tflag:
                    outtokens.append(token)
            return outtokens

        # Grab the target data
        fp          = open(self.target_path,'rb')
        target_dict = pickle.load(fp)
        fp.close()

        # Extract the tokens
        annot_str       = target_dict['annotation']
        target_str      = target_dict['target']

        # Get tokens for targets
        all_tokens = []
        try:
            # Some cleanup for the ast library
            tmp   = target_str.replace("'","")
            tmp   = tmp.replace('"',"")
            tmp   = tmp.replace("{","{'")
            tmp   = tmp.replace("}","'}")
            tmp   = tmp.replace(":","':'")
            tmp   = tmp.replace(",","','")
            tdict = ast.literal_eval(tmp)
            
            for ival in tdict.values():
                all_tokens.extend(return_tokens(ival))
        except Exception as e:
            all_tokens.extend(return_tokens(target_str))

        # get tokens for annotations
        try:
            tmp   = annot_str.replace("'","")
            tmp   = tmp.replace('"',"")
            tmp   = tmp.replace("{","{'")
            tmp   = tmp.replace("}","'}")
            tmp   = tmp.replace(":","':'")
            tmp   = tmp.replace(",","','")
            adict = ast.literal_eval(annot_str)

            for ival in adict.values():
                all_tokens.extend(return_tokens(ival))
        except Exception as e:
            all_tokens.extend(return_tokens(annot_str))

        # Store result to self
        self.all_tokens = all_tokens

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