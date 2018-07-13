## GTBD project to synchronise data in TRICS and GTWH ## 

## Import Python libraries
from Levenshtein import *
import multiprocessing as mt
import numpy as np
import os
import pandas as pd
import pyodbc

## Initialize variables
remit_dict = {'TRICS_REMITTER': [], 'TRICS_CCIF': [], 'TRICS_REMITTING_BANK': [], 
              'GDWH_COMPANY':[], 'GDWH_CCIF':[]}
ben_dict = {'TRICS_BENEFICIARY': [], 'TRICS_CCIF': [], 'TRICS_BENEFICIARY_BANK': [], 
              'GDWH_COMPANY':[], 'GDWH_CCIF':[]}
#remit_dict = {'TRICS_REMITTER': [], 'TRICS_CCIF': [], 'TRICS_REMITTING_BANK': [], 
#              'GDWH_COMPANY':[], 'GDWH_CCIF':[], 'Matched_Flag': []}


## Establish connection to mySQL server
def start_mySQL():
    conn = pyodbc.connect(r'DRIVER={MySQL ODBC 5.3 ANSI Driver};'
                            r'SERVER=203.24.43.91;'
                            r'PORT=3306;'
                            r'DATABASE=gtbd;'
                            r'UID=root;'
                            r'PWD=root')
    cursor = conn.cursor()
    return conn, cursor


## Run query to return every trics table in mySQL server
def return_DB():   
    # Execute SQL to list tables
    cursor.execute('SHOW TABLES;')
    response = cursor.fetchall()
    mySQLtables = []
    for row in response:
        if 'trics_rm_worldwide' in row[0]:
            mySQLtables.append(row[0]) 
    return mySQLtables
  
    
## Query all valid customer names, C_CIF and banks
def return_table_data(table):
    df_trics_remit = pd.read_sql('SELECT REMITTER_ENGLISH, REMITTER_C_CIF, REMITTING_BANK_JP_BANK_GRP FROM %s WHERE REMITTER_C_CIF IS NOT NULL;' 
                         % table, con = conn)
    df_trics_remit.dropna(inplace = True)
    df_trics_remit['REMITTER_ENGLISH_NEW'] = df_trics_remit['REMITTER_ENGLISH'].str.replace('[^\w\s]','')
    
    df_trics_ben = pd.read_sql('SELECT BENEFICIARY_ENGLISH, BENEFICIARY_C_CIF, BENEFICIARY_BANK_JP_BANK_GRP FROM %s WHERE BENEFICIARY_C_CIF IS NOT NULL;' 
                         % table, con = conn)
    df_trics_ben.dropna(inplace = True)
    df_trics_ben['BENEFICIARY_ENGLISH_NEW'] = df_trics_ben['BENEFICIARY_ENGLISH'].str.replace('[^\w\s]','')
    
    df_customers = pd.read_sql('SELECT CUST_NAME, C_CIF_NO FROM t_gtbd_custlist WHERE CUST_NAME IS NOT NULL;', 
                               con = conn)
    df_customers.dropna(inplace = True)
    df_customers.drop_duplicates(subset = ['CUST_NAME', 'C_CIF_NO'], inplace = True)
    df_customers['CUST_NAME_NEW'] = df_customers['CUST_NAME'].str.replace('[^\w\s]',' ')
    
    # Remove sub_string from each row of DataFrame
    sub_string = ['CO LTD', 'COMPANY', 'CORP', 'CORPORATION', 'INC', 'LIMITED', 'LTD', 'PLC', 'PRIVATE', 'PTE', 'PTY']
    for string in sub_string:
        df_trics_remit['REMITTER_ENGLISH_NEW'] = [company.split(string)[0].replace('  ', ' ').strip() 
                                                 for company in list(df_trics_remit['REMITTER_ENGLISH_NEW'])]
        df_trics_ben['BENEFICIARY_ENGLISH_NEW'] = [company.split(string)[0].replace('  ', ' ').strip() 
                                                 for company in list(df_trics_ben['BENEFICIARY_ENGLISH_NEW'])]
        df_customers['CUST_NAME_NEW'] = [company.split(string)[0].replace('  ', ' ').strip() 
                                        for company in list(df_customers['CUST_NAME_NEW'])]
        
    return df_trics_remit, df_trics_ben, df_customers


## Perform fuzzy matching using Levenshtein distance
def get_closest_match(previous_string, sample_string, df, fun):
    # Initialize variables
    best_match = ''
    highest_ratio = 0
    # Compare sample_string with previous_string to identify duplicates
    if sample_string == previous_string:
        # If it is duplicate, skip fuzzy matching for efficiency
        best_match = previous_string
        # If it is not duplicate, perform subsequent matching
    else:
        # Compare sample_string with current_string in actual customer list
        for current_string in df.itertuples():
            if sample_string == current_string[3]:
                # If total match, skip fuzzy matching for efficiency 
                highest_ratio =  1
                best_match = current_string[1]
                print(current_string[1])
                
            elif (sample_string.split(' ')[0] == current_string[3].split(' ')[0]) and (highest_ratio != 1):
                # If it is not total match and pass first word matching, proceed with fuzzy matching 
                current_score = fun(sample_string, current_string[1])
                if(current_score > highest_ratio):
                    highest_ratio = current_score
                    best_match = current_string[1]
    return best_match

def LevRatioRemit(df1, df2, fun):
    temp_string = ''
    for row in df1.itertuples():
        best_match = get_closest_match(temp_string, row[4], df2, fun)
        if best_match == '':
            ccif = ''
        else:
            ccif = df2[df2['CUST_NAME'] == best_match].iloc[0]['C_CIF_NO']
        temp_string = best_match
        remit_dict['TRICS_REMITTER'].append(row[1])
        remit_dict['TRICS_CCIF'].append(row[2])
        remit_dict['TRICS_REMITTING_BANK'].append(row[3])
        remit_dict['GDWH_COMPANY'].append(best_match)
        remit_dict['GDWH_CCIF'].append(ccif)

#def LevRatioBen(df1, df2, fun):
#    temp_string = ''
#    for row in df1.itertuples():
#        best_match = get_closest_match(temp_string, row[4], df2, fun)
#        if best_match == '':
#            ccif = ''
#        else:
#            ccif = df2[df2['CUST_NAME'] == best_match].iloc[0]['C_CIF_NO']
#        temp_string = best_match
#        ben_dict['TRICS_BENEFICIARY'].append(row[1])
#        ben_dict['TRICS_CCIF'].append(row[2])
#        ben_dict['TRICS_BENEFICIARY_BANK'].append(row[3])
#        ben_dict['GDWH_COMPANY'].append(best_match)
#        ben_dict['GDWH_CCIF'].append(ccif)

      
## Execute conditions
conn, cursor = start_mySQL()
mySQLtables = return_DB()
df_trics_remit, df_trics_ben, df_customers = return_table_data(mySQLtables[0])
#LevRatioRemit(df_trics_remit, df_customers, ratio)  
#LevRatioBen(df_trics_ben, df_customers, ratio)  
## may need to use lists instead of dataframe!!!
