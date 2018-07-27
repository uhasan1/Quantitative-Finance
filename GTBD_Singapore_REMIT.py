## GTBD project to synchronise data in TRICS and GDWH - Focus on Singapore ## 

## Import Python libraries
from Levenshtein import *
import multiprocessing as mt
import numpy as np
import pandas as pd
import pyodbc
import re
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


## Run query to return every trics table residing in mySQL server
def return_DB():   
    # Execute SQL to list tables
    cursor.execute('SHOW TABLES;')
    response = cursor.fetchall()
    mySQLtables = []
    for row in response:
        if 'trics_rm_worldwide' in row[0]:
            mySQLtables.append(row[0]) 
    return mySQLtables


## Run query to return selected trics table data and GDWH customer list from mySQL server
def return_table_data(table):
    # Import selected TRICS DataFrame from mySQL server
    df_trics = pd.read_sql("""SELECT COUNTRY_FROM, REMITTING_BANK_JP_BANK_GRP, BENEFICIARY_BANK_JP_BANK_GRP, 
                           REMITTER_ENGLISH, REMITTER_C_CIF, BENEFICIARY_ENGLISH, BENEFICIARY_C_CIF
                           FROM %s WHERE COUNTRY_FROM LIKE \'SINGAPORE\';"""  
                           % table, con = conn)  
    df_gdwh = pd.read_sql('SELECT CUST_NAME, C_CIF_NO FROM t_gtbd_custlist WHERE CUST_NAME IS NOT NULL;', 
                          con = conn)
    return df_trics, df_gdwh


## Parse data in standardized format
def parse_table_data(): 

    # Create df_trics_remit using df_trics
    df_trics_remit = df_trics.copy()
    df_trics_remit.drop(['BENEFICIARY_ENGLISH', 'BENEFICIARY_C_CIF'], axis = 1, inplace = True)  
    df_trics_remit.sort_values(by = 'REMITTER_ENGLISH', inplace = True)
    df_trics_remit['REMITTER_ENGLISH_NEW'] = df_trics_remit['REMITTER_ENGLISH']
    # Drop all non-alphanumeric characters from TRICS REMIT customer names
    df_trics_remit['REMITTER_ENGLISH_NEW'] = [re.sub(r'[^\w\s]', ' ', row) for row in df_trics_remit['REMITTER_ENGLISH_NEW']]
    df_trics_remit['REMITTER_ENGLISH_NEW'] = [re.sub(r'\b%s\b' % 'AND', '', row) for row in df_trics_remit['REMITTER_ENGLISH_NEW']]
    df_trics_remit['REMITTER_ENGLISH_NEW'] = df_trics_remit['REMITTER_ENGLISH_NEW'].str.replace('   ', ' ')
    df_trics_remit['REMITTER_ENGLISH_NEW'] = df_trics_remit['REMITTER_ENGLISH_NEW'].str.replace('  ', ' ')
    df_trics_remit['REMITTER_ENGLISH_NEW'] = df_trics_remit['REMITTER_ENGLISH_NEW'].str.strip()
    # Drop all leading numbers from TRICS REMIT customer names
    df_trics_remit['REMITTER_ENGLISH_NEW'] = [re.sub(' +', ' ', re.sub(r'\b\d+\b', '', company)).strip()
                                             if company[0:5].isdigit() else company                                         
                                             for company in df_trics_remit['REMITTER_ENGLISH_NEW']]    
    # Drop all potential addresses (if there are digits in middle of text) from TRICS REMIT customer names
    df_trics_remit['REMITTER_ENGLISH_NEW'] = [company
                                             if re.split(' ', company)[0].isdigit() else re.split(r'\s\d+', company)[0] 
                                             for company in df_trics_remit['REMITTER_ENGLISH_NEW']]  

    # Create df_trics_ben using df_trics
    df_trics_ben = df_trics.copy()
    df_trics_ben.drop(['REMITTER_ENGLISH', 'REMITTER_C_CIF'], axis = 1, inplace= True)  
    df_trics_ben.sort_values(by = 'BENEFICIARY_ENGLISH', inplace = True)
    df_trics_ben['BENEFICIARY_ENGLISH_NEW'] = df_trics_ben['BENEFICIARY_ENGLISH']
    # Drop all non-alphanumeric characters from TRICS BEN customer names
    df_trics_ben['BENEFICIARY_ENGLISH_NEW'] = [re.sub(r'[^\w\s]', ' ', row) for row in df_trics_ben['BENEFICIARY_ENGLISH_NEW']]
    df_trics_ben['BENEFICIARY_ENGLISH_NEW'] = [re.sub(r'\b%s\b' % 'AND', '', row) for row in df_trics_ben['BENEFICIARY_ENGLISH_NEW']]
    df_trics_ben['BENEFICIARY_ENGLISH_NEW'] = df_trics_ben['BENEFICIARY_ENGLISH_NEW'].str.replace('   ' , ' ')
    df_trics_ben['BENEFICIARY_ENGLISH_NEW'] = df_trics_ben['BENEFICIARY_ENGLISH_NEW'].str.replace('  ' , ' ')
    df_trics_ben['BENEFICIARY_ENGLISH_NEW'] = df_trics_ben['BENEFICIARY_ENGLISH_NEW'].str.strip()
    # Drop all leading numbers (if it is more than or equal to 5 digits) from TRICS BEN customer names
    df_trics_ben['BENEFICIARY_ENGLISH_NEW'] = [re.sub(' +', ' ', re.sub(r'\b\d+\b', '', company)).strip()
                                              if company[0:5].isdigit() else company                                         
                                              for company in df_trics_ben['BENEFICIARY_ENGLISH_NEW']]  
    # Drop all potential addresses (if there are digits in middle of text) from TRICS REMIT customer names
    df_trics_ben['BENEFICIARY_ENGLISH_NEW'] = [company
                                              if re.split(' ', company)[0].isdigit() else re.split(r'\s\d+', company)[0] 
                                              for company in df_trics_ben['BENEFICIARY_ENGLISH_NEW']]    
    
    # Create df_customers using df_gdwh
    df_customers = df_gdwh.copy()
    # Drop all duplicates and non-alphanumeric characters from GDWH customer names
    df_customers.dropna(inplace = True)    
    df_customers.drop_duplicates('CUST_NAME', inplace = True)
    df_customers['CUST_NAME_NEW'] = df_customers['CUST_NAME']
    df_customers['CUST_NAME_NEW'] = [re.sub(r'[^\w\s]', ' ', row) for row in df_customers['CUST_NAME_NEW']]
    df_customers['CUST_NAME_NEW'] = [re.sub(r'\b%s\b' % 'AND', '', row) for row in df_customers['CUST_NAME_NEW']]
    df_customers['CUST_NAME_NEW'] = df_customers['CUST_NAME_NEW'].str.replace('   ', ' ')
    df_customers['CUST_NAME_NEW'] = df_customers['CUST_NAME_NEW'].str.replace('  ', ' ')
    df_customers['CUST_NAME_NEW'] = df_customers['CUST_NAME_NEW'].str.strip()
    # Drop all leading numbers (if it is more than or equal to 5 digits) from GDWH customer names
    df_customers['CUST_NAME_NEW'] = [re.sub(' +', ' ', re.sub(r'\b\d+\b', '', company)).strip()
                                    if company[0:5].isdigit() else company                                         
                                    for company in df_customers['CUST_NAME_NEW']]  
    # Drop all potential addresses (if there are digits in middle of text) from TRICS REMIT customer names
    df_customers['CUST_NAME_NEW'] = [company
                                    if re.split(' ', company)[0].isdigit() else re.split(r'\s\d+', company)[0] 
                                    for company in df_customers['CUST_NAME_NEW']]    
        
    # Standardize each country's abbreviation in all 3 DataFrames
    df_std = pd.read_excel('CountryAbbreviations.xlsx')
    for abb in df_std.values.tolist():
        df_trics_remit['REMITTER_ENGLISH_NEW'] = df_trics_remit['REMITTER_ENGLISH_NEW'].str.replace(r'\b%s\b' % abb[1], abb[0])
        df_trics_ben['BENEFICIARY_ENGLISH_NEW'] = df_trics_ben['BENEFICIARY_ENGLISH_NEW'].str.replace(r'\b%s\b' % abb[1], abb[0])
        df_customers['CUST_NAME_NEW'] = df_customers['CUST_NAME_NEW'].str.replace(r'\b%s\b' % abb[1], abb[0])

    # Standardize each sector's abbreviations in all 3 DataFrames
    df_std = pd.read_excel('SectorAbbreviations.xlsx')
    for abb in df_std.values.tolist():
        df_trics_remit['REMITTER_ENGLISH_NEW'] = df_trics_remit['REMITTER_ENGLISH_NEW'].str.replace(r'\b%s\b' % abb[1], abb[0])
        df_trics_ben['BENEFICIARY_ENGLISH_NEW'] = df_trics_ben['BENEFICIARY_ENGLISH_NEW'].str.replace(r'\b%s\b' % abb[1], abb[0])
        df_customers['CUST_NAME_NEW'] = df_customers['CUST_NAME_NEW'].str.replace(r'\b%s\b' % abb[1], abb[0])
    
    # Standardize each company's abbreviation in all 3 DataFrames and drop all other words after company's abbreviation 
    # for first-level matching
    df_std = pd.read_excel('CompanyAbbreviations.xlsx')           
    for abb in df_std.values.tolist():
        df_trics_remit['REMITTER_ENGLISH_NEW'] = df_trics_remit['REMITTER_ENGLISH_NEW'].apply(lambda x: 
                                                 re.sub(r'\b%s\b' %abb[1], abb[0], x) if (re.search(r'\b%s\b' % abb[1], x)) and \
                                                 (x.split()[0] != abb[1]) else x)
        df_trics_ben['BENEFICIARY_ENGLISH_NEW'] = df_trics_ben['BENEFICIARY_ENGLISH_NEW'].apply(lambda x: 
                                                 re.sub(r'\b%s\b' %abb[1], abb[0], x) if (re.search(r'\b%s\b' % abb[1], x)) and \
                                                 (x.split()[0] != abb[1]) else x)
        df_customers['CUST_NAME_NEW'] = df_customers['CUST_NAME_NEW'].apply(lambda x: 
                                        re.sub(r'\b%s\b' %abb[1], abb[0], x) if (re.search(r'\b%s\b' % abb[1], x)) and \
                                        (x.split()[0] != abb[1]) else x)
                 
    # Create a new column to store REMITTER_ENGLISH_NEW 
    df_trics_remit['REMITTER_ENGLISH_CCC'] = df_trics_remit['REMITTER_ENGLISH_NEW']
    df_trics_ben['BENEFICIARY_ENGLISH_CCC'] = df_trics_ben['BENEFICIARY_ENGLISH_NEW']
    df_customers['CUST_NAME_CCC'] = df_customers['CUST_NAME_NEW']
             
    # Find country/capital/city and drop all words after country/capital/city for second-level matching
    df_ccc = pd.read_excel('CountriesCapitalsCities.xlsx')    
    for ccc in df_ccc['ENTITIES'].values.tolist():
        df_trics_remit['REMITTER_ENGLISH_CCC'] = df_trics_remit['REMITTER_ENGLISH_CCC'].apply(lambda x: 
                                                re.split(r'\b%s\b' % ccc, x)[0] + ccc if (re.search(r'\b%s\b' % ccc, x)) and \
                                                (len(re.split(' ', re.split(r'\b%s\b' % ccc, x)[0] + ccc)) > 2)
                                                else x)
        df_trics_ben['BENEFICIARY_ENGLISH_CCC'] = df_trics_ben['BENEFICIARY_ENGLISH_CCC'].apply(lambda x: 
                                                 re.split(r'\b%s\b' % ccc, x)[0] + ccc if (re.search(r'\b%s\b' % ccc, x)) and \
                                                 (len(re.split(' ', re.split(r'\b%s\b' % ccc, x)[0] + ccc)) > 2) 
                                                 else x)
        df_customers['CUST_NAME_CCC'] = df_customers['CUST_NAME_CCC'].apply(lambda x: 
                                       re.split(r'\b%s\b' % ccc, x)[0] + ccc if (re.search(r'\b%s\b' % ccc, x)) and \
                                       (len(re.split(' ', re.split(r'\b%s\b' % ccc, x)[0] + ccc)) > 2)
                                       else x)
    
    return df_trics_remit, df_trics_ben, df_customers, df_ccc
   

## Fuzzy matching
def get_all_trics_data(table):
    # Drop duplicates and UPDATE_FLAG = N in df_remit_match
    df_remit_match = LevRatioRemit(df_trics_remit, df_customers, ratio)
    df_remit_match.drop_duplicates('REMITTER_ENGLISH', inplace = True)
    df_remit_match = df_remit_match[df_remit_match['UPDATE_FLAG'] == 'Y']
    df_remit_match.drop(['REMITTING_BANK', 'BENEFICIARY_BANK', 'TRICS_CCIF', 'UPDATE_FLAG'], axis = 1, inplace = True)
    # Drop duplicates and UPDATE_FLAG = N in df_ben_match
    df_ben_match = LevRatioBen(df_trics_ben, df_customers, ratio)
    df_ben_match.drop_duplicates('BENEFICIARY_ENGLISH', inplace = True)
    df_ben_match = df_ben_match[df_ben_match['UPDATE_FLAG'] == 'Y']
    df_ben_match.drop(['REMITTING_BANK', 'BENEFICIARY_BANK', 'TRICS_CCIF', 'UPDATE_FLAG'], axis = 1, inplace = True)
    # Update SINGAPORE TRICS DataFrame with df_remit_match and df_ben_match information
    df_trics_mod = pd.read_sql('SELECT * FROM %s WHERE COUNTRY_FROM LIKE \'SINGAPORE\';' % table, con = conn) 
    df_trics_mod = pd.merge(df_trics_mod, df_remit_match, how = 'left', on = 'REMITTER_ENGLISH')
    df_trics_mod = pd.merge(df_trics_mod, df_ben_match, how = 'left', on = 'BENEFICIARY_ENGLISH')
    df_trics_mod.to_excel('TRICS_Singapore_20180727.xlsx')
    
    return df_trics_mod

def LevRatioRemit(df1, df2, fun):
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
    df_remit_match.to_excel('Remit_Singapore_20180727.xlsx')
    
    return df_remit_match
    
def LevRatioBen(df1, df2, fun):
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
    df_ben_match.to_excel('Ben_Singapore_20180727.xlsx')
    
    return df_ben_match

def get_closest_match(sample_string, df, fun):
    # Initialize variables
    best_match = ''
    highest_ratio = 0
    # Compare sample_string with GDWH DataFrame to identify exact match
    if len(df[df['CUST_NAME'].str.replace(' ', '') == sample_string[4].replace(' ', '')]['CUST_NAME']) >= 1:
        # If it is exact match, skip fuzzy matching for efficiency
        best_match = df[df['CUST_NAME'].str.replace(' ', '') == sample_string[4].replace(' ', '')].iloc[0]['CUST_NAME']
        highest_ratio =  1
        # If it is not exact match, perform subsequent matching with modified names, i.e. NEW AND CO
    elif len(df[df['CUST_NAME_NEW'].str.replace(' ', '') == sample_string[6].replace(' ', '')]['CUST_NAME_NEW']) >= 1:
        # If it is exact match, skip fuzzy matching for efficiency
        best_match = df[df['CUST_NAME_NEW'].str.replace(' ', '') == sample_string[6].replace(' ', '')].iloc[0]['CUST_NAME']
        highest_ratio =  0.999
    elif len(df[df['CUST_NAME_CCC'].str.replace(' ', '') == sample_string[7].replace(' ', '')]['CUST_NAME_CCC']) >= 1:
        # If it is exact match, skip fuzzy matching for efficiency
        best_match = df[df['CUST_NAME_CCC'].str.replace(' ', '') == sample_string[7].replace(' ', '')].iloc[0]['CUST_NAME']
        highest_ratio =  0.998
    else:
        # Compare sample_string with current_string in actual customer list
        for current_string in df.itertuples():
            if (sample_string[6].split(' ')[0:2] == current_string[3].split(' ')[0:2]) and \
                 ([ccc for ccc in df_ccc['ENTITIES'] if ccc in sample_string[6]] \
                 == [ccc for ccc in df_ccc['ENTITIES'] if ccc in current_string[3]]) and \
                 len([ccc for ccc in df_ccc['ENTITIES'] if ccc in sample_string[6]]) >= 1 and \
                 len([ccc for ccc in df_ccc['ENTITIES'] if ccc in current_string[3]]) >= 1 and \
                 (highest_ratio < 0.998):
                # If it is not total match but pass first word/country matching, proceed with fuzzy matching 
                current_score = fun(sample_string[6], current_string[3])
                if(current_score > highest_ratio):
                    highest_ratio = current_score
                    best_match = current_string[1]
                    
            elif (sample_string[6].split()[0:2] == current_string[3].split()[0:2]) and \
                 len([ccc for ccc in df_ccc['ENTITIES'] if ccc in sample_string[6]]) == 0 and \
                 len([ccc for ccc in df_ccc['ENTITIES'] if ccc in current_string[3]]) == 0 and \
                 (highest_ratio < 0.998):
                 # If it is not total match and fail all other conditions above, proceed with fuzzy matching 
                current_score = fun(sample_string[6], current_string[3])
                if(current_score > highest_ratio):
                    highest_ratio = current_score
                    best_match = current_string[1]   
                    
    return best_match, highest_ratio


## Execute conditions
#conn, cursor = start_mySQL()
#mySQLtables = return_DB()
#df_trics, df_gdwh = return_table_data(mySQLtables[-4])
df_trics_remit, df_trics_ben, df_customers, df_ccc = parse_table_data()
df_trics_mod = get_all_trics_data(mySQLtables[-4])  

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


     
#    for abb in df_std.values.tolist():
#        df_trics_remit['REMITTER_ENGLISH_NEW'] = df_trics_remit['REMITTER_ENGLISH_NEW'].map(lambda coy: 
#                                                 re.sub(r'\b%s\b' % abb[1], abb[0], coy))
#        df_trics_ben['BENEFICIARY_ENGLISH_NEW'] = df_trics_ben['BENEFICIARY_ENGLISH_NEW'].map(lambda coy: 
#                                                  re.sub(r'\b%s\b' % abb[1], abb[0], coy))
#        df_customers['CUST_NAME_NEW'] = df_customers['CUST_NAME_NEW'].map(lambda coy: re.sub(r'\b%s\b' % abb[1], abb[0], coy))
#
#        df_trics_remit['REMITTER_ENGLISH_NEW'] = df_trics_remit['REMITTER_ENGLISH_NEW'].map(lambda coy: 
#                                                 re.split(r'\b%s\b' % abb[1], coy)[0] + abb[0])
#        df_trics_ben['BENEFICIARY_ENGLISH_NEW'] = df_trics_ben['BENEFICIARY_ENGLISH_NEW'].map(lambda coy: 
#                                                 re.split(r'\b%s\b' % abb[1], coy)[0] + abb[0])
#        df_customers['CUST_NAME_NEW'] = df_customers['CUST_NAME_NEW'].map(lambda coy: re.split(r'\b%s\b' % abb[1], coy)[0] + abb[0])
#        [re.split(r'\b%s\b' % abb[1], company)[0] + abb[0] 
#                                                 for company in df_trics_remit['REMITTER_ENGLISH_NEW']]
#        df_trics_ben['BENEFICIARY_ENGLISH_NEW'] = [re.split(r'\b%s\b' % abb[1], company)[0] + abb[0]  
#                                                  for company in df_trics_ben['BENEFICIARY_ENGLISH_NEW']]
#        df_customers['CUST_NAME_NEW'] = [re.split(r'\b%s\b' % abb[1], company)[0] + abb[0] 
#                                        for company in df_customers['CUST_NAME_NEW']]