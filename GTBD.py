## GTBD project to synchronise data in TRICS and GTWH ## 

## Import Python libraries
from Levenshtein import *
import numpy as np
import os
import pandas as pd
import pyodbc


## Initialize variables
company_dict = {'Matched_Company':[], 'Matched_CCIF':[]}
#company_dict = {'Matched_Company':[], 'Matched_CCIF':[], 'Matched_Flag':[]}

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
  
    
## Query all entities with valid customer names & C_CIF
def return_table_data(table):
    df_trics_remit = pd.read_sql('SELECT REMITTER_ENGLISH, REMITTER_C_CIF FROM %s WHERE REMITTER_C_CIF IS NOT NULL;' 
                         % table, con = conn)
    df_trics_remit.dropna(inplace = True)

    df_trics_ben = pd.read_sql('SELECT BENEFICIARY_ENGLISH, BENEFICIARY_C_CIF FROM %s WHERE BENEFICIARY_C_CIF IS NOT NULL;' 
                         % table, con = conn)
    df_trics_ben.dropna(inplace = True)

    df_customers = pd.read_sql('SELECT CUST_NAME, C_CIF_NO FROM t_gtbd_custlist WHERE CUST_NAME IS NOT NULL;', 
                               con = conn)
    df_customers.dropna(inplace = True)
    df_customers.drop_duplicates(subset = ['CUST_NAME', 'C_CIF_NO'], inplace = True)

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
        for current_string in df.values.tolist():
            if sample_string == current_string[0]:
                # If total match, skip fuzzy matching for efficiency 
                highest_ratio =  1
                best_match = current_string[0]
                
            elif (sample_string.split(' ')[0] == current_string[0].split(' ')[0]) and (highest_ratio != 1):
                # If it is not total match and pass first word matching, proceed with fuzzy matching 
                current_score = fun(sample_string, current_string[0])
                if(current_score > highest_ratio):
                    highest_ratio = current_score
                    best_match = current_string[0]
    return best_match
    
def LevRatioMerge(df1, df2, fun):
    temp_string = ''
    for row in df1.itertuples():
        best_match = get_closest_match(temp_string, row[1], df2, fun)
        if best_match == '':
            ccif = ''
        else:
            ccif = df2[df2['CUST_NAME'] == best_match].iloc[0]['C_CIF_NO']
        temp_string = best_match
        company_dict['Matched_Company'].append(best_match)
        company_dict['Matched_CCIF'].append(ccif)

      
## Execute conditions
conn, cursor = start_mySQL()
mySQLtables = return_DB()
df_trics_remit, df_trics_ben, df_customers = return_table_data(mySQLtables[0])
LevRatioMerge(df_trics_remit, df_customers, ratio)  
#LevRatioMerge(df_trics_ben, df_customers, ratio)  



#def name_match(trics_cust, cust_list):
#    name = dl.get_close_matches(trics_cust, cust_list, 1, 0.8)
#    print(name)
#    # Valid match and first word is identical
#    for i in range(len(sample.flatten)):
#        if len(name) > 0 and sample.split(" ") == name[0].split(" ")[0]:
#        matched_cust.append(name[0])
##            matched_CCIF.append(df_customers.loc[df_customers['CUST_NAME']==name[0], 'C_CIF_NO'].tolist()[0])
#            matched_flag.append('1')            
#        # No valid match or valid match and first word is not identical
#        else:
#            matched_cust.append('')
##            matched_CCIF.append('')
#            matched_flag.append('0')    

#    matched_cust = []
#    matched_CCIF = []
#    matched_flag = []
#    
#    for company in sample_list:
#        name = dl.get_close_matches(company, actual_list, 1, 0.8)
#        print(name)
#        # Valid match and first word is identical
#        if len(name) > 0 and company.split(" ")[0] == name[0].split(" ")[0]:
#            matched_cust.append(name[0])
##            matched_CCIF.append(df_customers.loc[df_customers['CUST_NAME']==name[0], 'C_CIF_NO'].tolist()[0])
#            matched_flag.append('1')            
#        # No valid match or valid match and first word is not identical
#        else:
#            matched_cust.append('')
##            matched_CCIF.append('')
#            matched_flag.append('0')
#        
#    return matched_cust, matched_flag

#    # Display results in DataFrame
#    df_customers ['Matched_Cust'] = matched_cust
#    df_customers ['Matched_CCIF'] = matched_CCIF
#    df_customers ['Matched_Flag'] = matched_flag
    
