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


############################################### START ###############################################################

## Parse data in standardized format
def parse_table_data(): 
    # Create df1 containing LC Applicant details using df_
    df1 = df_.copy()
    df1.drop(['BENEFICIARY', 'BENEFICIARY_C_CIF'], axis = 1, inplace = True)  
    df1.sort_values(by = 'APPLICANT', inplace = True)
    df1 = clean_data(df1, 'APPLICANT', 'APPLICANT_NEW')

    # Create df2 containing LC Beneficiary details using df_
    df2 = df_.copy()
    df2.drop(['APPLICANT', 'APPLICANT_C_CIF'], axis = 1, inplace= True)  
    df2.sort_values(by = 'BENEFICIARY', inplace = True)
    df2 = clean_data(df2, 'BENEFICIARY', 'BENEFICIARY_NEW')

    # Create df_customers using df_gdwh
    df_customers = df_gdwh.copy()
    # Drop all duplicates fromm GDWH customer names
    df_customers.dropna(inplace = True)    
    df_customers.drop_duplicates('CUST_NAME', inplace = True)
    df_customers = clean_data(df_customers, 'CUST_NAME', 'CUST_NAME_NEW')
    
    # Standardize each country's abbreviation in all 3 DataFrames
    df1 = parse_abb('CountryAbbreviations.xlsx', df1, 'APPLICANT_NEW')
    df2 = parse_abb('CountryAbbreviations.xlsx', df2, 'BENEFICIARY_NEW')
    df_customers = parse_abb('CountryAbbreviations.xlsx', df_customers, 'CUST_NAME_NEW')
    
    # Standardize each sector's abbreviation in all 3 DataFrames
    df1 = parse_abb('SectorAbbreviations.xlsx', df1, 'APPLICANT_NEW')
    df2 = parse_abb('SectorAbbreviations.xlsx', df2, 'BENEFICIARY_NEW')
    df_customers = parse_abb('SectorAbbreviations.xlsx', df_customers, 'CUST_NAME_NEW')
    
    # Remove company's abbreviation if it is found at the beginning of string
    df1 = del_begin_abb('CompanyAbbreviations.xlsx', df1, 'APPLICANT_NEW')
    df2 = del_begin_abb('CompanyAbbreviations.xlsx', df2, 'BENEFICIARY_NEW')
    df_customers = del_begin_abb('CompanyAbbreviations.xlsx', df_customers, 'CUST_NAME_NEW')
  
    # Create a new column to store LC data
    df1['APPLICANT_CCC'] = df1['APPLICANT_NEW']
    df2['BENEFICIARY_CCC'] = df2['BENEFICIARY_NEW']
    df_customers['CUST_NAME_CCC'] = df_customers['CUST_NAME_NEW']
    df1['APPLICANT_CO'] = df1['APPLICANT_NEW']
    df2['BENEFICIARY_CO'] = df2['BENEFICIARY_NEW']
    df_customers['CUST_NAME_CO'] = df_customers['CUST_NAME_NEW']
    
    # Standardize remaining companies' abbreviation and country/capital/city in all 3 DataFrames 
    df1 = parse_ccc_abb('CompanyAbbreviations.xlsx', 'CountriesCapitalsCities.xlsx', df1, 'APPLICANT_CCC', 'APPLICANT_CO')
    df2 = parse_ccc_abb('CompanyAbbreviations.xlsx', 'CountriesCapitalsCities.xlsx', df2, 'BENEFICIARY_CCC', 'BENEFICIARY_CO')
    df_customers = parse_ccc_abb('CompanyAbbreviations.xlsx', 'CountriesCapitalsCities.xlsx', df_customers, 'CUST_NAME_CCC', 'CUST_NAME_CO')
    return df1, df2, df_customers

def clean_data(df, dseries_old, dseries_new):
    # Drop all non-alphanumeric characters from selected DataFrame customer names
    df[dseries_new] = df[dseries_old].str.replace(r'[^\w\s]', ' ')
    df[dseries_new] = df[dseries_new].str.replace(r'\b%s\b' % 'AND', '')  
    # Drop all leading (supsicious) numbers from selected DataFrame customer names
    df[dseries_new] = df[dseries_new][df[dseries_new].str[0:5].replace(' ', '').str.isdigit()].str.replace(r'^\d+', '')
    df[dseries_new].fillna(df[dseries_old][df[dseries_new].isnull()], inplace = True)
    df[dseries_new] = df[dseries_new].str.replace(r'[^\w\s]', ' ')
    df[dseries_new] = df[dseries_new].str.replace(r'\b%s\b' % 'AND', '')  
    df[dseries_new] = df[dseries_new].str.replace(r'^\d+\s\d+', '')
    # Drop all potential addresses from selected DataFrame customer names
    df[dseries_new] = df[dseries_new].str.split(r'\b%s\b' % 'NO').str[0]
    df[dseries_new] = df[dseries_new].str.split(r'\b%s\b' % 'SEE').str[0]
    df[dseries_new] = df[dseries_new].str.split(r'\s\d+').str[0]
    df[dseries_new] = df[dseries_new].str.split(r'\D\d+').str[0]
    # Strip redundant spaces
    df[dseries_new] = df[dseries_new].str.replace('[\s]{2,}', ' ')
    df[dseries_new] = df[dseries_new].str.strip()      
    return df
    
def parse_abb(file, df, dseries):
    # Load relevant files
    df_std = pd.read_excel(file)
    # Create a string to join all abbreviations
    pattern = (r'\b%s\b' % '|').join(df_std['SHORT'])
    # List DataFrame rows with abbreviations, regardless of their position
    df['SHORT'] = df[dseries].str.extract('(' + r'\b%s\b' % pattern + ')', expand = False)
    df['TEMP'] = df['SHORT']
    df['TEMP'].fillna(df[dseries][df['SHORT'].isnull()], inplace = True)
    # Do a left join with the full name
    df = pd.merge(df, df_std, how = 'left', on = 'SHORT')
    # Replace abbreviated DataFrame rows with full name
    df[dseries] = df.dropna(subset = ['SHORT']).apply(lambda x: x[dseries].replace(x['SHORT'],x['LONG']), axis=1)
    df[dseries].fillna(df['TEMP'][df[dseries].isnull()], inplace = True)
    # Remove redundant columns
    del df['SHORT'], df['LONG'], df['TEMP']
    return df

def del_begin_abb(file, df, dseries):
    # Load relevant files
    df_std = pd.read_excel(file)
    # Create a string to join all abbreviations
    pattern = (r'\b%s\b' % '|').join(df_std['SHORT'])
    # List DataFrame rows with abbreviations
    df['SHORT'] = df[dseries].str.extract('(' + r'\b%s\b' % pattern + ')', expand = False)
    df['TEMP'] = df['SHORT']
    df['TEMP'].fillna(df[dseries][df['SHORT'].isnull()], inplace = True)
    # Create a string to join all abbreviations
    pattern = (r'\b%s^\b' % '|').join(df_std['SHORT'].dropna())
    # Remove abbreviations from relevant DataFrame rows that begin with same abbreviation
    df[dseries] = df.dropna(subset = ['SHORT'])[dseries].str.replace('(' + r'^\b%s\b' % pattern + ')', '').str.strip()
    df[dseries].fillna(df['TEMP'][df[dseries].isnull()], inplace = True)
    # Remove redundant columns
    del df['SHORT'], df['TEMP']
    return df

def parse_ccc_abb(file_std, file_ccc, df, dseries, dseries2):
    # Load relevant files - country/capital/city and company abbreviations
    df_std = pd.read_excel(file_std) 
    df_ccc = pd.read_excel(file_ccc)
    # Create a string to join all abbreviations for each file
    pattern_std = (r'\b%s\b' % '|').join(df_std['SHORT'])
    pattern_ccc = (r'\b%s\b' % '|').join(df_ccc['ENTITIES'])
    # List DataFrame rows with country/capital/city abbreviations
    df['CCC'] = df[dseries].str.extract('(' + r'\b%s\b' % pattern_ccc + ')', expand = False)
    df['TEMP_CCC'] = df['CCC']
    df['TEMP_CCC_NO1'] = df['CCC']
    df['TEMP_CCC_NO2'] = df['CCC']
    df['TEMP_CCC'].fillna(df[dseries][df['CCC'].isnull()], inplace = True)
    df['TEMP_CCC_NO1'] = df.dropna(subset = ['CCC'])[dseries].str.split(r'\s').str[0]
    df['TEMP_CCC_NO2'] = df.dropna(subset = ['CCC'])[dseries].str.split(r'\s').str[1]
    # List DataFrame rows that do not begin with country (i.e. first 2 words must not contain country)
    df['TEMP_CCC'] = df['TEMP_CCC'][(df['TEMP_CCC_NO1'] != df['TEMP_CCC']) & (df['TEMP_CCC_NO2'] != df['TEMP_CCC'])]
    # Remove any text after country/capital/city abbreviations
    df['TEMP_CCC'] = df.dropna(subset = ['TEMP_CCC'])[dseries].str.split('(' + r'\b%s\b' % pattern_ccc + ')').str[0] + df.dropna(subset = ['TEMP_CCC'])['CCC'] 
    df['TEMP_CCC'].fillna(df[dseries][df['TEMP_CCC'].isnull()], inplace = True)
    df[dseries] = df['TEMP_CCC']
    # Remove company abbreviation
    df['TEMP_CCC'] = df['TEMP_CCC'].str.split('(' + r'\b%s\b' % pattern_std + ')').str[0].str.strip()
    df[dseries2] = df['TEMP_CCC']
    # Remove redundant columns
    del df['CCC'], df['TEMP_CCC'], df['TEMP_CCC_NO1'], df['TEMP_CCC_NO2']
    return df

############################################### END #################################################################  
    

############################################### START ###############################################################    

## Simple Fuzzy matching
def simple_fuzzy_match():    
    # Create df_simple containing LC details using df_
    df_simple = df_.copy()
    # Create additional empty columns in df_simple to store simple fuzzy matches
#    df_simple['APPLICANT_COMPANY_BEST_MATCH'] = ''
#    df_simple['APPLICANT_CCIF_BEST_MATCH'] = ''
#    df_simple['APPLICANT_HIGHEST_RATIO'] = ''
#    df_simple['APPLICANT_UPDATE_TAG'] = ''
#    df_simple['BENEFICIARY_COMPANY_BEST_MATCH'] = ''
#    df_simple['BENEFICIARY_CCIF_BEST_MATCH'] = ''
#    df_simple['BENEFICIARY_HIGHEST_RATIO'] = ''
#    df_simple['BENEFICIARY_UPDATE_TAG'] = ''
    
    # Lower level matching: Perform exact matching between modified columns in both source files
    df1_simple = df1.copy()
    df1_simple = exact_match_modified_co(df1_simple, 'APPLICANT_CO', 'APPLICANT_COMPANY_BEST_MATCH', 'APPLICANT_CCIF_BEST_MATCH', 
                                         'APPLICANT_HIGHEST_RATIO', 'APPLICANT_UPDATE_TAG', df_cust_simple)
    df2_simple = df2.copy()
    df2_simple = exact_match_modified_co(df2_simple, 'BENEFICIARY_CO', 'BENEFICIARY_COMPANY_BEST_MATCH', 'BENEFICIARY_CCIF_BEST_MATCH', 
                                         'BENEFICIARY_HIGHEST_RATIO', 'BENEFICIARY_UPDATE_TAG', df_cust_simple)
    
    
    # Highest level matching: Perform exact matching between original columns in both source files
#    df1_simple = df1.copy()
#    df1_simple = exact_match_original(df1_simple, 'APPLICANT', 'APPLICANT_COMPANY_BEST_MATCH', 'APPLICANT_CCIF_BEST_MATCH', 
#                                      'APPLICANT_HIGHEST_RATIO', 'APPLICANT_UPDATE_TAG', df_cust_simple)
#    df2_simple = df2.copy()
#    df2_simple = exact_match_original(df2_simple, 'BENEFICIARY', 'BENEFICIARY_COMPANY_BEST_MATCH', 'BENEFICIARY_CCIF_BEST_MATCH', 
#                                      'BENEFICIARY_HIGHEST_RATIO', 'BENEFICIARY_UPDATE_TAG', df_cust_simple)
    
    return df1_simple, df2_simple, df_cust_simple
    
def exact_match_modified_co(df, dseries, dseries_co, dseries_ccif, dseries_ratio, dseries_tag, df_cust):
    # Drop all duplicates 
    # Note: GDWH duplicates have been treated in parse_table_data()
    df.drop_duplicates(dseries, inplace = True)
    # Create additional column in df to store simple fuzzy matches
    df[dseries_co] = df[dseries]
    # Create df_cust using df_customers
    df_cust = df_customers.copy()
    # Remove redundant columns
    del df_cust['CUST_NAME'], df_cust['CUST_NAME_NEW'], df_cust['CUST_NAME_CCC']
    # Reorder/Rename remaining columns
    df_cust = df_cust[['CUST_NAME_CO', 'C_CIF_NO']]
    df_cust.columns = [dseries_co, dseries_ccif]
    # Perform left join
    df = pd.merge(df, df_cust, how = 'left', on = dseries_co)
    df.dropna(subset = [dseries_ccif], inplace = True)
    df[dseries_ratio] = 0.997
    df[dseries_tag] = 'Y'
    return df

def exact_match_original(df, dseries, dseries_co, dseries_ccif, dseries_ratio, dseries_tag, df_cust):
    # Drop all duplicates 
    # Note: GDWH duplicates have been treated in parse_table_data()
    df.drop_duplicates(dseries, inplace = True)
    # Create additional column in df to store simple fuzzy matches
    df[dseries_co] = df[dseries]
    # Create df_cust using df_customers
    df_cust = df_customers.copy()
    # Remove redundant columns
    del df_cust['CUST_NAME_NEW'], df_cust['CUST_NAME_CCC'], df_cust['CUST_NAME_CO']
    # Reorder/Rename remaining columns
    df_cust.columns = [dseries_co, dseries_ccif]
    # Perform left join
    df = pd.merge(df, df_cust, how = 'left', on = dseries_co)
    df.dropna(subset = [dseries_ccif], inplace = True)
    df[dseries_ratio] = 1
    df[dseries_tag] = 'Y'
    return df

## Complicated Fuzzy matching
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

############################################### END #################################################################  
    

## Execute conditions
#conn, cursor = start_mySQL()
#mySQLtables = return_DB('trics_lc_worldwide')
#df_, df_gdwh = return_table_data(mySQLtables[-2])
#df1, df2, df_customers = parse_table_data()
#df1_simple, df2_simple = simple_fuzzy_match()
df1_simple, df2_simple, df_cust_simple = simple_fuzzy_match()
#df_trics_mod = get_all_trics_data(mySQLtables[-2])  
