# Import Python libraries
import difflib as dl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import re
from sklearn.feature_extraction.text import TfidfVectorizer

# Creating Generator 
for n in range(1000000):
    x = n + n
    print(x)
    
simpleGen = (n+n for n in range(100000 0))
for n in simpleGen:
    print(n)
# Load file as DataFrame
df = pd.read_csv('sec__edgar_company_info.csv', index_col = 0)

# Using N-Grams Approach
def ngrams(string, n=3):
    string = re.sub(r'[,-./]|\sBD',r'', string)
    ngrams = zip(*[string[i:] for i in range(n)])
    return [''.join(ngram) for ngram in ngrams]

#ngrams('McDonalds')

# Using Term Frequency - Inverse Document Frequency (TF-IDF) Approach 
company_names = df['Company Name']
vectorizer = TfidfVectorizer(min_df=1, analyzer=ngrams)
tf_idf_matrix = vectorizer.fit_transform(company_names)
print(tf_idf_matrix[0])


#sample_list = []
#actual_list = []
#df = pd.read_excel(r'C:\Users\r15\.spyder-py3\testdifflib.xlsx')
## Remember to include .dropna for both Dataframes #
#sample_list = np.array([df['Sample']])
#sample_list.resize(6,1)
#actual_list = np.array(df['Actual'].dropna())
#
#def name_match(sample, actual):
#    print(sample)
##    s = sample.flatten()
#    
##    for company in s:
##        print(company)
##        name = dl.get_close_matches(company, actual, 1, 0.8)
##        if len(name) != 0:
##            result = np.array(name)
#
#myfunc = np.vectorize(name_match)
#myfunc(sample_list, actual_list)


#N=30
#x=np.random.normal(0,1,N)
#X=np.vstack((x,x))
#cov=np.cov(X)
#print (cov)