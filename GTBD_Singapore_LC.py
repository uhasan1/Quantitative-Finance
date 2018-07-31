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
app_dict = {'ISSUING_BANK': [], 'ADVISING_BANK': [], 'APPLICANT': [], 'APPLICANT_CCIF': [], 
            'APPLICANT_COMPANY_BEST_MATCH':[], 'APPLICANT_CCIF_BEST_MATCH':[], 'APPLICANT_HIGHEST_RATIO': []}
ben_dict = {'ISSUING_BANK': [], 'ADVISING_BANK': [], 'BENEFICIARY': [], 'BENEFICIARY_CCIF': [],  
            'BEN_COMPANY_BEST_MATCH':[], 'BEN_CCIF_BEST_MATCH':[], 'BEN_HIGHEST_RATIO': []}
df_temp = pd.DataFrame({})

## Establish connection to mySQL server
def start_mySQL():
    conn = pyodbc.connect(r'DRIVER={MySQL ODBC 5.3 ANSI Driver};'
                            r'SERVER=localhost;'
                            r'PORT=3306;'
                            r'DATABASE=gtbd;'
                            r'UID=root;'
                            r'PWD=root')
    cursor = conn.cursor()
    return conn, cursor


## Run query to return every LC table in mySQL server
def return_DB(table):   
    # Execute SQL to list tables
    cursor.execute('SHOW TABLES;')
    response = cursor.fetchall()
    mySQLtables = []
    for row in response:
        if table in row[0]:
            mySQLtables.append(row[0]) 
    return mySQLtables


## Run query to return selected trics table data and GDWH customer list from mySQL server
def return_table_data(table):
    # Import selected DataFrame from mySQL server
    df_ = pd.read_sql("""SELECT COUNTRY_FROM, ISSUING_BANK_JP_BANK_GRP, ADVISING_BANK_JP_BANK_GRP, APPLICANT, APPLICANT_C_CIF, 
                      BENEFICIARY, BENEFICIARY_C_CIF FROM %s;""" % table, con = conn)  
    df_gdwh = pd.read_sql('SELECT CUST_NAME, C_CIF_NO FROM t_gtbd_custlist WHERE CUST_NAME IS NOT NULL;', con = conn)
    return df_, df_gdwh


## Parse data in standardized format
def parse_table_data(): 
    # Create df1 containing LC Applicant details using df_
    df1 = df_.copy()
    df1.drop(['BENEFICIARY', 'BENEFICIARY_C_CIF'], axis = 1, inplace = True)  
    df1.sort_values(by = 'APPLICANT', inplace = True)
    # Drop all non-alphanumeric characters from LC Applicant customer names
    df1['APPLICANT_NEW'] = df1['APPLICANT'].str.replace(r'[^\w\s]', ' ')
    df1['APPLICANT_NEW'] = df1['APPLICANT_NEW'].str.replace(r'\b%s\b' % 'AND', '')  
    # Drop all leading (supsicious) numbers from LC Applicant customer names
    df1['APPLICANT_NEW'] = df1['APPLICANT_NEW'][df1['APPLICANT_NEW'].str[0:5].replace(' ', '').str.isdigit()].str.replace(r'^\d+', '')
    df1['APPLICANT_NEW'].fillna(df1['APPLICANT'][df1['APPLICANT_NEW'].isnull()], inplace = True)
    df1['APPLICANT_NEW'] = df1['APPLICANT_NEW'].str.replace(r'^\d+\s\d+', '')
    # Drop all potential addresses from LC Applicant customer names
    df1['APPLICANT_NEW'] = df1['APPLICANT_NEW'].str.split(r'\b%s\b' % 'NO').str[0]
    df1['APPLICANT_NEW'] = df1['APPLICANT_NEW'].str.split(r'\b%s\b' % 'SEE').str[0]
    df1['APPLICANT_NEW'] = df1['APPLICANT_NEW'].str.split(r'\s\d+').str[0]
    df1['APPLICANT_NEW'] = df1['APPLICANT_NEW'].str.split(r'\D\d+').str[0]
    # Strip redundant spaces
    df1['APPLICANT_NEW'] = df1['APPLICANT_NEW'].str.replace('[\s{Zs}]{2,}', ' ')
    df1['APPLICANT_NEW'] = df1['APPLICANT_NEW'].str.strip()  

    # Create df2 containing LC Beneficiary details using df_
    df2 = df_.copy()
    df2.drop(['APPLICANT', 'APPLICANT_C_CIF'], axis = 1, inplace= True)  
    df2.sort_values(by = 'BENEFICIARY', inplace = True)
    # Drop all non-alphanumeric characters from LC Bene customer names
    df2['BENEFICIARY_NEW'] = df2['BENEFICIARY'].str.replace(r'[^\w\s]', ' ')
    df2['BENEFICIARY_NEW'] = df2['BENEFICIARY_NEW'].str.replace(r'\b%s\b' % 'AND', '')  
    # Drop all leading (supsicious) numbers from LC Bene customer names
    df2['BENEFICIARY_NEW'] = df2['BENEFICIARY_NEW'][df2['BENEFICIARY_NEW'].str[0:5].replace(' ', '').str.isdigit()].str.replace(r'^\d+', '')
    df2['BENEFICIARY_NEW'].fillna(df2['BENEFICIARY'][df2['BENEFICIARY_NEW'].isnull()], inplace = True)
    df2['BENEFICIARY_NEW'] = df2['BENEFICIARY_NEW'].str.replace(r'^\d+\s\d+', '')
    # Drop all potential addresses from LC Bene customer names
    df2['BENEFICIARY_NEW'] = df2['BENEFICIARY_NEW'].str.split(r'\b%s\b' % 'NO').str[0]
    df2['BENEFICIARY_NEW'] = df2['BENEFICIARY_NEW'].str.split(r'\b%s\b' % 'SEE').str[0]
    df2['BENEFICIARY_NEW'] = df2['BENEFICIARY_NEW'].str.split(r'\s\d+').str[0]
    df2['BENEFICIARY_NEW'] = df2['BENEFICIARY_NEW'].str.split(r'\D\d+').str[0]
    # Strip redundant spaces
    df2['BENEFICIARY_NEW'] = df2['BENEFICIARY_NEW'].str.replace('[\s{Zs}]{2,}', ' ')
    df2['BENEFICIARY_NEW'] = df2['BENEFICIARY_NEW'].str.strip()  

    # Create df_customers using df_gdwh
    df_customers = df_gdwh.copy()
    # Drop all duplicates and non-alphanumeric characters from GDWH customer names
    df_customers.dropna(inplace = True)    
    df_customers.drop_duplicates('CUST_NAME', inplace = True)
    df_customers['CUST_NAME_NEW'] = df_customers['CUST_NAME'].str.replace(r'[^\w\s]', ' ')
    df_customers['CUST_NAME_NEW'] = df_customers['CUST_NAME_NEW'].str.replace(r'\b%s\b' % 'AND', '')
    # Drop all leading (supsicious) numbers from GDWH customer names
    df_customers['CUST_NAME_NEW'] = df_customers['CUST_NAME_NEW'][df_customers['CUST_NAME_NEW'].str[0:5].replace(' ', '').str.isdigit()].str.replace(r'^\d+', '')
    df_customers['CUST_NAME_NEW'].fillna(df_customers['CUST_NAME'][df_customers['CUST_NAME_NEW'].isnull()], inplace = True)
    df_customers['CUST_NAME_NEW'] = df_customers['CUST_NAME_NEW'].str.replace(r'^\d+\s\d+', '')
    # Drop all potential addresses from GDWH customer names
    df_customers['CUST_NAME_NEW'] = df_customers['CUST_NAME_NEW'].str.split(r'\b%s\b' % 'NO').str[0]
    df_customers['CUST_NAME_NEW'] = df_customers['CUST_NAME_NEW'].str.split(r'\b%s\b' % 'SEE').str[0]
    df_customers['CUST_NAME_NEW'] = df_customers['CUST_NAME_NEW'].str.split(r'\s\d+').str[0]
    df_customers['CUST_NAME_NEW'] = df_customers['CUST_NAME_NEW'].str.split(r'\D\d+').str[0]
    # Strip redundant spaces
    df_customers['CUST_NAME_NEW'] = df_customers['CUST_NAME_NEW'].str.replace('[\s{Zs}]{2,}', ' ')
    df_customers['CUST_NAME_NEW'] = df_customers['CUST_NAME_NEW'].str.strip()  
    
    # Standardize each country's abbreviation in all 3 DataFrames
    df_std = pd.read_excel('CountryAbbreviations.xlsx')
    pattern = "|".join(df_std['SHORT'])
    df1['APPLICANT_NEW'] = df1['APPLICANT_NEW'].str.replace(r'\b%s\b' % pattern, )
    for abb in df_std.values.tolist():
        df1['APPLICANT_NEW'] = df1['APPLICANT_NEW'].str.replace(r'\b%s\b' % abb[1], abb[0])
        df2['BENEFICIARY_NEW'] = df2['BENEFICIARY_NEW'].str.replace(r'\b%s\b' % abb[1], abb[0])
        df_customers['CUST_NAME_NEW'] = df_customers['CUST_NAME_NEW'].str.replace(r'\b%s\b' % abb[1], abb[0])

    # Standardize each sector's abbreviations in all 3 DataFrames
    df_std = pd.read_excel('SectorAbbreviations.xlsx')
    for abb in df_std.values.tolist():
        df1['APPLICANT_NEW'] = df1['APPLICANT_NEW'].str.replace(r'\b%s\b' % abb[1], abb[0])
        df2['BENEFICIARY_NEW'] = df2['BENEFICIARY_NEW'].str.replace(r'\b%s\b' % abb[1], abb[0])
        df_customers['CUST_NAME_NEW'] = df_customers['CUST_NAME_NEW'].str.replace(r'\b%s\b' % abb[1], abb[0])
    
    # Remove company's abbreviation if it is found at the beginning of string
    df_std = pd.read_excel('CompanyAbbreviations.xlsx')  
    df1['APPLICANT_NEW'] = df1['APPLICANT_NEW'][df1['APPLICANT_NEW'].str[0:5].replace(' ', '').str.isdigit()].str.replace(r'^\d+', '')
    
    
    # Standardize each company's abbreviation and country/capital/city in all 3 DataFrames 
    df_std = pd.read_excel('CompanyAbbreviations.xlsx')  
    df_ccc = pd.read_excel('CountriesCapitalsCities.xlsx')
    
    
    for abb in df_std['SHORT'].values.tolist():
        df1['APPLICANT_NEW'] = df1['APPLICANT_NEW'].apply(lambda x: 
                                          re.sub(r'\b%s\b' %abb[1], abb[0], x) if (re.search(r'\b%s\b' % abb[1], x)) and \
                                          (x.split()[0] != abb[1]) else x)
        df2['BENEFICIARY_NEW'] = df2['BENEFICIARY_NEW'].apply(lambda x: 
                                          re.sub(r'\b%s\b' %abb[1], abb[0], x) if (re.search(r'\b%s\b' % abb[1], x)) and \
                                          (x.split()[0] != abb[1]) else x)
        df_customers['CUST_NAME_NEW'] = df_customers['CUST_NAME_NEW'].apply(lambda x: 
                                        re.sub(r'\b%s\b' %abb[1], abb[0], x) if (re.search(r'\b%s\b' % abb[1], x)) and \
                                        (x.split()[0] != abb[1]) else x)
    
    
    
    # Create a new column to store LC data
    df1['APPLICANT_CCC'] = df1['APPLICANT_NEW']
    df2['BENEFICIARY_CCC'] = df2['BENEFICIARY_NEW']
    df_customers['CUST_NAME_CCC'] = df_customers['CUST_NAME_NEW']
        
    # Find country/capital/city and drop all words after country/capital/city for second-level matching

    
    
    
    for ccc in df_ccc['ENTITIES'].values.tolist():
        df1['APPLICANT_CCC'] = 
        
        df1['APPLICANT_CCC'].apply(lambda x: 
                                          re.split(r'\b%s\b' % ccc, x)[0] + ccc if (re.search(r'\b%s\b' % ccc, x)) and \
                                          (len(re.split(' ', re.split(r'\b%s\b' % ccc, x)[0] + ccc)) > 2)
                                          else x)
        df2['BENEFICIARY_CCC'] = df2['BENEFICIARY_CCC'].apply(lambda x: 
                                          re.split(r'\b%s\b' % ccc, x)[0] + ccc if (re.search(r'\b%s\b' % ccc, x)) and \
                                          (len(re.split(' ', re.split(r'\b%s\b' % ccc, x)[0] + ccc)) > 2) 
                                          else x)
        df_customers['CUST_NAME_CCC'] = df_customers['CUST_NAME_CCC'].apply(lambda x: 
                                       re.split(r'\b%s\b' % ccc, x)[0] + ccc if (re.search(r'\b%s\b' % ccc, x)) and \
                                       (len(re.split(' ', re.split(r'\b%s\b' % ccc, x)[0] + ccc)) > 2)
                                       else x)
    
    


#    
    return df1, df2, df_customers, df_ccc


## Fuzzy matching
def get_all_trics_data(table):
    # Drop duplicates and UPDATE_FLAG = N in df_remit_match
    df_remit_match = LevRatioRemit(df1, df_customers, ratio)
    df_remit_match.drop_duplicates('APPLICANT', inplace = True)
    df_remit_match = df_remit_match[df_remit_match['UPDATE_FLAG'] == 'Y']
    df_remit_match.drop(['ISSUING_BANK', 'ADVISING_BANK', 'APPLICANT_CCIF', 'UPDATE_FLAG'], axis = 1, inplace = True)
    # Drop duplicates and UPDATE_FLAG = N in df_ben_match
    df_ben_match = LevRatioBen(df2, df_customers, ratio)
    df_ben_match.drop_duplicates('BENEFICIARY', inplace = True)
    df_ben_match = df_ben_match[df_ben_match['UPDATE_FLAG'] == 'Y']
    df_ben_match.drop(['ISSUING_BANK', 'ADVISING_BANK', 'BENEFICIARY_CCIF', 'UPDATE_FLAG'], axis = 1, inplace = True)
    # Update SINGAPORE TRICS DataFrame with df_remit_match and df_ben_match information
    df_trics_mod = df_.copy()
    df_trics_mod = pd.merge(df_trics_mod, df_remit_match, how = 'left', on = 'APPLICANT')
    df_trics_mod = pd.merge(df_trics_mod, df_ben_match, how = 'left', on = 'BENEFICIARY')
    df_trics_mod.to_excel('LC_20180730.xlsx')
    
    return df_trics_mod

def LevRatioRemit(df1, df2, fun):
    df1.drop_duplicates('APPLICANT', inplace = True)
    for row in df1.itertuples():
        best_match, highest_ratio = get_closest_match(row, df2, fun)
        if best_match == '':
            ccif = ''
        else:
            ccif = df2[df2['CUST_NAME'] == best_match].iloc[0]['C_CIF_NO']
        app_dict['ISSUING_BANK'].append(row[2])
        app_dict['ADVISING_BANK'].append(row[3])
        app_dict['APPLICANT'].append(row[4])
        app_dict['APPLICANT_CCIF'].append(row[5])
        app_dict['APPLICANT_COMPANY_BEST_MATCH'].append(best_match)
        app_dict['APPLICANT_CCIF_BEST_MATCH'].append(ccif)
        app_dict['APPLICANT_HIGHEST_RATIO'].append(highest_ratio)
    
    # Create DataFrame to store matched results and flag 
    df_remit_match = pd.DataFrame(app_dict)
    df_remit_match['UPDATE_FLAG'] = ['Y' if ratio >= 0.9 else 'N' for ratio in df_remit_match['APPLICANT_HIGHEST_RATIO']]
    df_remit_match.to_excel('Applicant_20180730.xlsx')
    
    return df_remit_match
    
def LevRatioBen(df1, df2, fun):
    df1.drop_duplicates('BENEFICIARY', inplace = True)
    for row in df1.itertuples():
        best_match, highest_ratio = get_closest_match(row, df2, fun)
        if best_match == '':
            ccif = ''
        else:
            ccif = df2[df2['CUST_NAME'] == best_match].iloc[0]['C_CIF_NO']
        ben_dict['ISSUING_BANK'].append(row[2])
        ben_dict['ADVISING_BANK'].append(row[3])
        ben_dict['BENEFICIARY'].append(row[4])
        ben_dict['BENEFICIARY_CCIF'].append(row[5])
        ben_dict['BEN_COMPANY_BEST_MATCH'].append(best_match)
        ben_dict['BEN_CCIF_BEST_MATCH'].append(ccif)
        ben_dict['BEN_HIGHEST_RATIO'].append(highest_ratio)
    
    # Create DataFrame to store matched results and flag 
    df_ben_match = pd.DataFrame(ben_dict)
    df_ben_match['UPDATE_FLAG'] = ['Y' if ratio >= 0.9 else 'N' for ratio in df_ben_match['BEN_HIGHEST_RATIO']]
    df_ben_match.to_excel('Ben_20180730.xlsx')
    
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
conn, cursor = start_mySQL()
mySQLtables = return_DB('trics_lc_worldwide')
df_, df_gdwh = return_table_data(mySQLtables[-2])
df1, df2, df_customers = parse_table_data()
#df1, df2, df_customers, df_ccc = parse_table_data()
#df_trics_mod = get_all_trics_data(mySQLtables[-2])  
