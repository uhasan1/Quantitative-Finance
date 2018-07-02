# Gaussian Copula

import numpy as np
import difflib as dl
import pandas as pd
import matplotlib.pyplot as plt

sample_list = []
actual_list = []
df = pd.read_excel(r'C:\Users\r15\.spyder-py3\testdifflib.xlsx')
# Remember to include .dropna for both Dataframes #
sample_list = np.array([df['Sample']])
sample_list.resize(6,1)
actual_list = np.array(df['Actual'].dropna())

def name_match(sample, actual):
    print(sample)
#    s = sample.flatten()
    
#    for company in s:
#        print(company)
#        name = dl.get_close_matches(company, actual, 1, 0.8)
#        if len(name) != 0:
#            result = np.array(name)

myfunc = np.vectorize(name_match)
myfunc(sample_list, actual_list)

#https://jakevdp.github.io/PythonDataScienceHandbook/02.05-computation-on-arrays-broadcasting.html
#N=30
#x=np.random.normal(0,1,N)
#X=np.vstack((x,x))
#cov=np.cov(X)
#print (cov)