# Imports
import pandas as pd
import numpy as np
import tensorflow_hub as hub
from stqdm import stqdm

# Streamlit
import streamlit as st
import preshed
import cymem

# PDF
import sys
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.pdfpage import PDFPage
from pdfminer.converter import XMLConverter, HTMLConverter, TextConverter
from pdfminer.layout import LAParams
import io

# Summarization using extractive bert
from summarizer import Summarizer

# BERT based models for document search
from sentence_transformers import SentenceTransformer
import pickle

st.set_page_config(layout="wide")
file, text, q = None, None, None
stqdm.pandas()



@st.cache(allow_output_mutation=True)
def load_models():
    a = hub.load("https://tfhub.dev/google/universal-sentence-encoder/4")
    b = SentenceTransformer('stsb-distilbert-base')
    c = SentenceTransformer('stsb-roberta-large') 
    d = SentenceTransformer('msmarco-distilbert-base-v2')
    return a,b,c,d       

@st.cache(hash_funcs={preshed.maps.PreshMap:id, cymem.cymem.Pool:id}, allow_output_mutation=True)#hash_funcs={preshed.maps.PreshMap: lambda x: 1, cymem.cymem.Pool:      lambda x: 1})
def load_summarizer():
    return Summarizer()

@st.cache()
def load_pdf(file)->str:
    
    if isinstance(file, str):
        fp = open(file, 'rb')
    else: 
        fp = file
        
    rsrcmgr = PDFResourceManager()
    retstr = io.StringIO()
    laparams = LAParams()
    device = TextConverter(rsrcmgr, retstr, laparams=laparams)
    
    # Create a PDF interpreter object.
    interpreter = PDFPageInterpreter(rsrcmgr, device)
    
    # Process each page contained in the document.
    pages = []
    for i, page in enumerate(PDFPage.get_pages(fp)):
        interpreter.process_page(page)
        text = retstr.getvalue()
        pages.append(text)
        
    full_text = pages[-1]
    return full_text

@st.cache()
def get_articles(text:str)->pd.Series:
    
    data = pd.Series(text.split('\n\nARTICLE'))

    s = (data
         .str.strip()
         .loc[46:]
         .loc[lambda x: x.astype(bool)]
         .loc[lambda x: x.apply(len)>10]
         .str.replace('\s+',' ')
         .drop_duplicates()
        )
    
    return s

    
    
@st.cache()
def ask(q:str, X:pd.DataFrame, s:pd.Series, n: int, model, embeddings_option)->pd.Series:
    
    if embeddings_option == selectbox_list[0]:
        embedding = np.array(model([q])[0])
    else:
        embedding = np.array(model.encode([q])[0])
        
    sorted_index = (X
                    .apply(lambda row: np.dot(row, embedding), axis=1)
                    .abs()
                    .sort_values(ascending=False)
                   )
    
    return s.loc[sorted_index.index].head(n)

#@st.cache()
def summarize(text, model, n=1):
    result = model(text, num_sentences=n)
    return result

def get_embeddings(embeddings_option):
    return pd.read_pickle(options[embeddings_option][0])

### APP
st.title('BERT Passage Scoring')

# ALWAYS
use,dbert,rbert,qbert = load_models()


options = {'Universal Sentence Encoder': ['use.pkl',use],
           'DistillBERT':['distilbert.pkl',dbert], 
           'RoBERTa Large':['robert.pkl',rbert],
           'DistillBERT Q&A':['distilbertqa.pkl',qbert],
           'Select a model...':['','']}

selectbox_list = list(options.keys())

summarizer_model = load_summarizer()



    
file = 'DRAFT_UK-EU_Comprehensive_Free_Trade_Agreement.pdf'

text = load_pdf(file)
s = get_articles(text)
embeddings_option = st.selectbox('Which model?', selectbox_list, index=4)
q = st.text_input('What is your query?')

if q:
    X = get_embeddings(embeddings_option)
    ans = ask(q, X=X, s=s, n=3, model=options[embeddings_option][1],embeddings_option=embeddings_option)
    for i, t in enumerate(ans):
        with st.beta_expander(f'ARTICLE {t.split()[0]}'):
            if len(t.split('. '))>3:
                summary = summarize(t, summarizer_model, 1)
                st.success(summary)
            st.write(t)
    
        








