## GTBD project to synchronise data in TRICS and GDWH - Focus on Philippines ## 

## Import Python libraries
from Levenshtein import *
import numpy as np
import pandas as pd
import pyodbc
import re
import threading
import time


## Initialize variables
remit_dict = {'REMITTING_BANK': [], 'BENEFICIARY_BANK': [], 'REMITTER_ENGLISH': [], 'TRICS_CCIF': [], 
              'REMIT_COMPANY_BEST_MATCH':[], 'REMIT_CCIF_BEST_MATCH':[], 'REMIT_HIGHEST_RATIO': []}
ben_dict = {'REMITTING_BANK': [], 'BENEFICIARY_BANK': [], 'BENEFICIARY_ENGLISH': [], 'TRICS_CCIF': [],  
            'BEN_COMPANY_BEST_MATCH':[], 'BEN_CCIF_BEST_MATCH':[], 'BEN_HIGHEST_RATIO': []}


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
  

## Process countries and capitals (cc) from Excel file
def get_cc(file):
    df_cc = pd.read_excel(file)
    # Create a new column to store the countries and capitals separately
    df_cc['COUNTRY'] = [re.split('[^\w\s]',entity)[1].strip().upper() for entity in df_cc['ENTITIES'].values.tolist()]
    df_cc['CAPITAL'] = [re.split('[^\w\s]',entity)[2].strip().upper() for entity in df_cc['ENTITIES'].values.tolist()]
    return df_cc

    
## Query all valid customer names, C_CIF and banks, and update them in standardized format
def return_table_data(table):
    # Import TRICS REMIT DataFrame from mySQL server
    df_trics_remit = pd.read_sql('SELECT COUNTRY_FROM, REMITTING_BANK, BENEFICIARY_BANK, REMITTER_ENGLISH, REMITTER_C_CIF FROM %s WHERE COUNTRY_FROM LIKE \'PHILIPPINES\';' 
                         % table, con = conn)
    df_trics_remit.sort_values(by = 'REMITTER_ENGLISH', inplace = True)
    # Drop all non-alphanumeric characters from TRICS REMIT customer names
    df_trics_remit['REMITTER_ENGLISH_NEW'] = df_trics_remit['REMITTER_ENGLISH']
    df_trics_remit['REMITTER_ENGLISH_NEW'] = [re.sub(r'[^\w\s]', ' ', row) for row in df_trics_remit['REMITTER_ENGLISH_NEW']]
    df_trics_remit['REMITTER_ENGLISH_NEW'] = [re.sub(r'\b%s\b' % 'AND', '', row) for row in df_trics_remit['REMITTER_ENGLISH_NEW']]
    df_trics_remit['REMITTER_ENGLISH_NEW'] = df_trics_remit['REMITTER_ENGLISH_NEW'].str.replace('   ', ' ')
    df_trics_remit['REMITTER_ENGLISH_NEW'] = df_trics_remit['REMITTER_ENGLISH_NEW'].str.replace('  ', ' ')
    df_trics_remit['REMITTER_ENGLISH_NEW'] = df_trics_remit['REMITTER_ENGLISH_NEW'].str.strip()
    
     # Import TRICS BEN DataFrame from mySQL server
    df_trics_ben = pd.read_sql('SELECT COUNTRY_FROM, REMITTING_BANK, BENEFICIARY_BANK, BENEFICIARY_ENGLISH, BENEFICIARY_C_CIF FROM %s WHERE COUNTRY_FROM LIKE \'PHILIPPINES\';' 
                         % table, con = conn)
    df_trics_ben.sort_values(by = 'BENEFICIARY_ENGLISH', inplace = True)
    # Drop all non-alphanumeric characters from TRICS BEN customer names
    df_trics_ben['BENEFICIARY_ENGLISH_NEW'] = df_trics_ben['BENEFICIARY_ENGLISH']
    df_trics_ben['BENEFICIARY_ENGLISH_NEW'] = [re.sub(r'[^\w\s]', ' ', row) for row in df_trics_ben['BENEFICIARY_ENGLISH_NEW']]
    df_trics_ben['BENEFICIARY_ENGLISH_NEW'] = [re.sub(r'\b%s\b' % 'AND', '', row) for row in df_trics_ben['BENEFICIARY_ENGLISH_NEW']]
    df_trics_ben['BENEFICIARY_ENGLISH_NEW'] = df_trics_ben['BENEFICIARY_ENGLISH_NEW'].str.replace('   ' , ' ')
    df_trics_ben['BENEFICIARY_ENGLISH_NEW'] = df_trics_ben['BENEFICIARY_ENGLISH_NEW'].str.replace('  ' , ' ')
    df_trics_ben['BENEFICIARY_ENGLISH_NEW'] = df_trics_ben['BENEFICIARY_ENGLISH_NEW'].str.strip()
    
    # Import GDWH Customer DataFrame from mySQL server
    df_customers = pd.read_sql('SELECT CUST_NAME, C_CIF_NO FROM t_gtbd_custlist WHERE CUST_NAME IS NOT NULL;', 
                               con = conn)
    # Drop all duplicates and non-alphanumeric characters from GDWH customer names
    df_customers.dropna(inplace = True)    
    df_customers.drop_duplicates('CUST_NAME', inplace = True)
    df_customers['CUST_NAME_NEW'] = df_customers['CUST_NAME']
    df_customers['CUST_NAME_NEW'] = [re.sub(r'[^\w\s]', ' ', row) for row in df_customers['CUST_NAME_NEW']]
    df_customers['CUST_NAME_NEW'] = [re.sub(r'\b%s\b' % 'AND', '', row) for row in df_customers['CUST_NAME_NEW']]
    df_customers['CUST_NAME_NEW'] = df_customers['CUST_NAME_NEW'].str.replace('   ', ' ')
    df_customers['CUST_NAME_NEW'] = df_customers['CUST_NAME_NEW'].str.replace('  ', ' ')
    df_customers['CUST_NAME_NEW'] = df_customers['CUST_NAME_NEW'].str.strip()
    
    # Standardize countries' abbreviations in all 3 DataFrames
    df_ca = pd.read_excel('CountryAbbreviations.xlsx')
    
    for abb in df_ca.values.tolist():
        df_trics_remit['REMITTER_ENGLISH_NEW'] = [re.sub(r'\b%s\b' % abb[1], abb[0], company) 
                                                 for company in df_trics_remit['REMITTER_ENGLISH_NEW']]
        df_trics_ben['BENEFICIARY_ENGLISH_NEW'] = [re.sub(r'\b%s\b' % abb[1], abb[0], company) 
                                                  for company in df_trics_ben['BENEFICIARY_ENGLISH_NEW']]
        df_customers['CUST_NAME_NEW'] = [re.sub(r'\b%s\b' % abb[1], abb[0], company) 
                                        for company in df_customers['CUST_NAME_NEW']]
    
    # Standardize common root keywords, e.g. MFG, in all 3 DataFrames
    df_ca = pd.read_excel('SectorAbbreviations.xlsx')
    
    for abb in df_ca.values.tolist():
        df_trics_remit['REMITTER_ENGLISH_NEW'] = [re.sub(r'\b%s\b' % abb[1], abb[0], company) 
                                                 for company in df_trics_remit['REMITTER_ENGLISH_NEW']]
        df_trics_ben['BENEFICIARY_ENGLISH_NEW'] = [re.sub(r'\b%s\b' % abb[1], abb[0], company) 
                                                  for company in df_trics_ben['BENEFICIARY_ENGLISH_NEW']]
        df_customers['CUST_NAME_NEW'] = [re.sub(r'\b%s\b' % abb[1], abb[0], company) 
                                        for company in df_customers['CUST_NAME_NEW']]
    
    # Standardize company abbreviations and drop all company addresses in all 3 DataFrames
    df_ca = pd.read_excel('CompanyAbbreviations.xlsx')
    
    df_trics_remit['REMITTER_ENGLISH_CO'] = df_trics_remit['REMITTER_ENGLISH_NEW']
    df_trics_ben['BENEFICIARY_ENGLISH_CO'] = df_trics_ben['BENEFICIARY_ENGLISH_NEW']
    df_customers['CUST_NAME_CO'] = df_customers['CUST_NAME_NEW']
    
    for abb in df_ca.values.tolist():
        df_trics_remit['REMITTER_ENGLISH_NEW'] = [re.split(r'\b%s\b' % abb[1], company)[0] + abb[0] 
                                                 for company in df_trics_remit['REMITTER_ENGLISH_NEW']]
        df_trics_ben['BENEFICIARY_ENGLISH_NEW'] = [re.split(r'\b%s\b' % abb[1], company)[0] + abb[0]  
                                                  for company in df_trics_ben['BENEFICIARY_ENGLISH_NEW']]
        df_customers['CUST_NAME_NEW'] = [re.split(r'\b%s\b' % abb[1], company)[0] + abb[0] 
                                        for company in df_customers['CUST_NAME_NEW']]
        
        df_trics_remit['REMITTER_ENGLISH_CO'] = [re.split(r'\b%s\b' % abb[1], company)[0] + abb[0]  
                                                 for company in df_trics_remit['REMITTER_ENGLISH_CO']]
        df_trics_ben['BENEFICIARY_ENGLISH_CO'] = [re.split(r'\b%s\b' % abb[1], company)[0] + abb[0] 
                                                  for company in df_trics_ben['BENEFICIARY_ENGLISH_CO']]
        df_customers['CUST_NAME_CO'] = [re.split(r'\b%s\b' % abb[1], company)[0] + abb[0]  
                                        for company in df_customers['CUST_NAME_CO']]
     
    df_trics_remit['REMITTER_ENGLISH_CO'] = [re.split("\S*\d\S*", company)[0].strip()
                                             for company in df_trics_remit['REMITTER_ENGLISH_CO']]
    df_trics_ben['BENEFICIARY_ENGLISH_CO'] = [re.split("\S*\d\S*", company)[0].strip()
                                              for company in df_trics_ben['BENEFICIARY_ENGLISH_CO']]
    df_customers['CUST_NAME_CO'] = [re.split("\S*\d\S*", company)[0].strip()
                                    for company in df_customers['CUST_NAME_CO']]
    
    # Drop all words after country/capital for matching
    for country in df_cc['COUNTRY'].values.tolist():
        df_trics_remit['REMITTER_ENGLISH_NEW'] = [(re.split(r'\b%s\b' % country, company)[0] + country).strip()
                                                 if (country in company) and 
                                                 (re.split(r'\b%s\b' % country, company)[0] != '') and 
                                                 (len(re.split(' ', re.split(r'\b%s\b' % country, company)[0])) > 2)
                                                 else company
                                                 for company in df_trics_remit['REMITTER_ENGLISH_NEW']]
        df_trics_ben['BENEFICIARY_ENGLISH_NEW'] = [(re.split(r'\b%s\b' % country, company)[0] + country).strip()
                                                  if (country in company) and 
                                                  (re.split(r'\b%s\b' % country, company)[0] != '') and 
                                                  (len(re.split(' ', re.split(r'\b%s\b' % country, company)[0])) > 2)
                                                  else company
                                                  for company in df_trics_ben['BENEFICIARY_ENGLISH_NEW']]
        df_customers['CUST_NAME_NEW'] = [(re.split(r'\b%s\b' % country, company)[0] + country).strip()
                                        if (country in company) and 
                                        (re.split(r'\b%s\b' % country, company)[0] != '') and 
                                        (len(re.split(' ', re.split(r'\b%s\b' % country, company)[0])) > 2)
                                        else company
                                        for company in df_customers['CUST_NAME_NEW']]
    
    for capital in df_cc['CAPITAL'].values.tolist():
        df_trics_remit['REMITTER_ENGLISH_NEW'] = [(re.split(r'\b%s\b' % capital, company)[0] + capital).strip()
                                                  if (capital in company) and 
                                                 (re.split(r'\b%s\b' % capital, company)[0] != '') and 
                                                 (len(re.split(' ', re.split(r'\b%s\b' % capital, company)[0])) > 2)
                                                 else company
                                                 for company in df_trics_remit['REMITTER_ENGLISH_NEW']]
        df_trics_ben['BENEFICIARY_ENGLISH_NEW'] = [(re.split(r'\b%s\b' % capital, company)[0] + capital).strip()
                                                  if (capital in company) and 
                                                 (re.split(r'\b%s\b' % capital, company)[0] != '') and 
                                                 (len(re.split(' ', re.split(r'\b%s\b' % capital, company)[0])) > 2)
                                                 else company
                                                  for company in df_trics_ben['BENEFICIARY_ENGLISH_NEW']]
        df_customers['CUST_NAME_NEW'] = [(re.split(r'\b%s\b' % capital, company)[0] + capital).strip()
                                        if (capital in company) and 
                                        (re.split(r'\b%s\b' % capital, company)[0] != '') and 
                                        (len(re.split(' ', re.split(r'\b%s\b' % capital, company)[0])) > 2)
                                        else company
                                        for company in df_customers['CUST_NAME_NEW']]      

    return df_trics_remit, df_trics_ben, df_customers


## Fuzzy matching
def get_closest_match(sample_string, df, fun):
    # Initialize variables
    best_match = ''
    highest_ratio = 0
    # Compare sample_string with GDWH DataFrame to identify exact match
    if len(df[df['CUST_NAME'] == sample_string[4]]['CUST_NAME']) == 1:
        # If it is exact match, skip fuzzy matching for efficiency
        best_match = df[df['CUST_NAME'] == sample_string[4]].iloc[0]['CUST_NAME']
        highest_ratio =  1
        # If it is not exact match, perform subsequent matching with modified names
    elif len(df[df['CUST_NAME_CO'] == sample_string[7]]['CUST_NAME_CO']) == 1:
        # If it is exact match, skip fuzzy matching for efficiency
        best_match = df[df['CUST_NAME_CO'] == sample_string[7]].iloc[0]['CUST_NAME']
        highest_ratio =  0.999
    else:
        # Compare sample_string with current_string in actual customer list
        for current_string in df.itertuples():
            if (sample_string[6] == current_string[3]):
                # If total match, skip fuzzy matching for efficiency 
                highest_ratio =  0.999
                best_match = current_string[1]
                break              
                    
            elif (sample_string[6].split(' ')[0:2] == current_string[3].split(' ')[0:2]) and \
                 ([country for country in df_cc['COUNTRY'].values.tolist() if country in sample_string[6]] \
                 == [country for country in df_cc['COUNTRY'].values.tolist() if country in current_string[3]]) and \
                 len([country for country in df_cc['COUNTRY'].values.tolist() if country in sample_string[6]]) >= 1 and \
                 len([country for country in df_cc['COUNTRY'].values.tolist() if country in current_string[3]]) >= 1 and \
                 (highest_ratio <= 0.999):
                # If it is not total match but pass first word/country matching, proceed with fuzzy matching 
                current_score = fun(sample_string[6], current_string[3])
                if(current_score > highest_ratio):
                    highest_ratio = current_score
                    best_match = current_string[1]
                    
            elif (sample_string[6].split(' ')[0:2] == current_string[3].split(' ')[0:2]) and \
                 ([capital for capital in df_cc['CAPITAL'].values.tolist() if capital in sample_string[6]] \
                 == [capital for capital in df_cc['CAPITAL'].values.tolist() if capital in current_string[3]]) and \
                 len([capital for capital in df_cc['CAPITAL'].values.tolist() if capital in sample_string[6]]) >= 1 and \
                 len([capital for capital in df_cc['CAPITAL'].values.tolist() if capital in current_string[3]]) >= 1 and \
                 (highest_ratio <= 0.999):
                # If it is not total match but pass first word/capital matching, proceed with fuzzy matching 
                current_score = fun(sample_string[6], current_string[3])
                if(current_score > highest_ratio):
                    highest_ratio = current_score
                    best_match = current_string[1]    
                    
            elif (sample_string[6].split()[0:2] == current_string[3].split()[0:2]) and \
                (highest_ratio <= 0.999):
                # If it is not total match and fail all other conditions above, proceed with fuzzy matching 
                current_score = fun(sample_string[6], current_string[3])
                if(current_score > highest_ratio):
                    highest_ratio = current_score
                    best_match = current_string[1]   
            
    return best_match, highest_ratio

def LevRatioRemit(df1, df2, fun):
#    df_null = df1[df1['REMITTER_C_CIF'].isnull()]
#    df_null.drop_duplicates('REMITTER_ENGLISH', inplace = True)
    df1.drop_duplicates('REMITTER_ENGLISH', inplace = True)
    for row in df1.itertuples():
        best_match, highest_ratio = get_closest_match(row, df2, fun)
        if best_match == '':
            ccif = ''
        else:
            ccif = df2[df2['CUST_NAME'] == best_match].iloc[0]['C_CIF_NO']
        remit_dict['REMITTING_BANK'].append(row[2])
        remit_dict['BENEFICIARY_BANK'].append(row[3])
        remit_dict['REMITTER_ENGLISH'].append(row[4])
        remit_dict['TRICS_CCIF'].append(row[5])
        remit_dict['REMIT_COMPANY_BEST_MATCH'].append(best_match)
        remit_dict['REMIT_CCIF_BEST_MATCH'].append(ccif)
        remit_dict['REMIT_HIGHEST_RATIO'].append(highest_ratio)
    
    # Create DataFrame to store matched results and flag 
    df_remit_match = pd.DataFrame(remit_dict)
    df_remit_match['UPDATE_FLAG'] = ['Y' if ratio >= 0.9 else 'N' for ratio in df_remit_match['REMIT_HIGHEST_RATIO']]
    df_remit_match.to_excel('Remit_Philippines_20180724.xlsx')
    
    return df_remit_match
    
def LevRatioBen(df1, df2, fun):
#    df_null = df1[df1['BENEFICIARY_C_CIF'].isnull()]
#    df_null.drop_duplicates('BENEFICIARY_ENGLISH', inplace = True)
    df1.drop_duplicates('BENEFICIARY_ENGLISH', inplace = True)
    for row in df1.itertuples():
        best_match, highest_ratio = get_closest_match(row, df2, fun)
        if best_match == '':
            ccif = ''
        else:
            ccif = df2[df2['CUST_NAME'] == best_match].iloc[0]['C_CIF_NO']
        ben_dict['REMITTING_BANK'].append(row[2])
        ben_dict['BENEFICIARY_BANK'].append(row[3])
        ben_dict['BENEFICIARY_ENGLISH'].append(row[4])
        ben_dict['TRICS_CCIF'].append(row[5])
        ben_dict['BEN_COMPANY_BEST_MATCH'].append(best_match)
        ben_dict['BEN_CCIF_BEST_MATCH'].append(ccif)
        ben_dict['BEN_HIGHEST_RATIO'].append(highest_ratio)
    
    # Create DataFrame to store matched results and flag 
    df_ben_match = pd.DataFrame(ben_dict)
    df_ben_match['UPDATE_FLAG'] = ['Y' if ratio >= 0.9 else 'N' for ratio in df_ben_match['BEN_HIGHEST_RATIO']]
    df_ben_match.to_excel('Ben_Philippines_20180724.xlsx')
    
    return df_ben_match

## Import remaining PHILIPPINES data
def get_all_trics_data(table):
    # Import PHILIPPINES TRICS DataFrame from mySQL server
    df_trics = pd.read_sql('SELECT * FROM %s WHERE COUNTRY_FROM LIKE \'PHILIPPINES\';' % table, con = conn) 
    # Drop duplicates and UPDATE_FLAG = N in df_remit_match
    df_remit_match = LevRatioRemit(df_trics_remit, df_customers, ratio)
    end_remit_time = time.time()
    print('Time taken to finish Remitter matching:', end_remit_time - start)
    df_remit_match.drop_duplicates('REMITTER_ENGLISH', inplace = True)
    df_remit_match = df_remit_match[df_remit_match['UPDATE_FLAG'] == 'Y']
    df_remit_match.drop(['REMITTING_BANK', 'BENEFICIARY_BANK', 'TRICS_CCIF', 'UPDATE_FLAG'], axis = 1, inplace = True)
    # Drop duplicates and UPDATE_FLAG = N in df_ben_match
    df_ben_match = LevRatioBen(df_trics_ben, df_customers, ratio)
    end_ben_time = time.time()
    print('Time taken to finish Beneficiary matching:', end_ben_time - end_remit_time)
    df_ben_match.drop_duplicates('BENEFICIARY_ENGLISH', inplace = True)
    df_ben_match = df_ben_match[df_ben_match['UPDATE_FLAG'] == 'Y']
    df_ben_match.drop(['REMITTING_BANK', 'BENEFICIARY_BANK', 'TRICS_CCIF', 'UPDATE_FLAG'], axis = 1, inplace = True)
    # Update PHILIPPINES TRICS DataFrame with df_remit_match and df_ben_match information
    df_trics = pd.merge(df_trics, df_remit_match, how = 'left', on = 'REMITTER_ENGLISH')
    df_trics = pd.merge(df_trics, df_ben_match, how = 'left', on = 'BENEFICIARY_ENGLISH')
    df_trics.to_excel('TRICS_Philippines_20180724.xlsx')
    
    return df_trics


## Execute conditions
conn, cursor = start_mySQL()
mySQLtables = return_DB()
df_cc = get_cc('CountriesCapitals.xlsx')
df_trics_remit, df_trics_ben, df_customers = return_table_data(mySQLtables[-2])
start = time.time()
df_trics = get_all_trics_data(mySQLtables[-2])  
#    for country in df_cc['COUNTRY'].values.tolist():
#        df_trics_remit['REMITTER_ENGLISH_NEW'] = [(company.split(country)[0] + country).strip()
#                                                 if (country in company) and (company.split(country)[0] != '') else company
#                                                 for company in df_trics_remit['REMITTER_ENGLISH_NEW']]    
#        df_trics_ben['BENEFICIARY_ENGLISH_NEW'] = [(company.split(country)[0] + country).strip()
#                                                  if (country in company) and (company.split(country)[0] != '') else company
#                                                  for company in df_trics_ben['BENEFICIARY_ENGLISH_NEW']]
#        df_customers['CUST_NAME_NEW'] = [(company.split(country)[0] + country).strip()
#                                        if (country in company) and (company.split(country)[0] != '') else company
#                                        for company in df_customers['CUST_NAME_NEW']]
#    
#    for capital in df_cc['CAPITAL'].values.tolist():
#        df_trics_remit['REMITTER_ENGLISH_NEW'] = [(company.split(capital)[0] + capital).strip()
#                                                 if (capital in company) and (company.split(capital)[0] != '') else company
#                                                 for company in df_trics_remit['REMITTER_ENGLISH_NEW']]
#        df_trics_ben['BENEFICIARY_ENGLISH_NEW'] = [(company.split(capital)[0] + capital).strip()
#                                                  if (capital in company) and (company.split(capital)[0] != '') else company
#                                                  for company in df_trics_ben['BENEFICIARY_ENGLISH_NEW']]
#        df_customers['CUST_NAME_NEW'] = [(company.split(capital)[0] + capital).strip()
#                                        if (capital in company) and (company.split(capital)[0] != '') else company
#                                        for company in df_customers['CUST_NAME_NEW']]    