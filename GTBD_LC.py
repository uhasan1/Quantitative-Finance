## GTBD project to synchronise data in TRICS and GDWH ## 

## Import Python libraries
import datetime
from Levenshtein import *
import numpy as np
import pandas as pd
import pandas.io.sql as psql
import pyodbc
import time


## Initialize variables
GDWH_columns = ['CUST_NAME', 'C_CIF_NO', 'COUNTRY']
GDWH_combined_columns = ['CUST_NAME', 'CUST_NAME_NEW', 'CUST_NAME_CCC', 'CUST_NAME_CO']
GDWH_ccif_columns = ['REF_NO', 'DP_ACT_NO', 'CUST_NO_CCIF']
TRICS_columns = ['COUNTRY_FROM', 'COUNTRY_TO', 
                 'ISSUING_BANK_JP_BANK_GRP', 'ADVISING_BANK_JP_BANK_GRP', 
                 'APPLICANT', 'APPLICANT_C_CIF', 
                 'BENEFICIARY', 'BENEFICIARY_C_CIF']
TRICS_nayose_columns = ['COUNTRY_FROM', 'COUNTRY_TO', 
                        'ISSUING_BANK_JP_BANK_GRP', 'ADVISING_BANK_JP_BANK_GRP', 
                        'APPLICANT', 'APPLICANT_C_CIF',  
                        'BENEFICIARY', 'BENEFICIARY_C_CIF', 
                        'APPLICANT_ACCOUNT', 'BENEFICIARY_ACCOUNT'
                        'APPLICANT_NAYOSE_FLG', 'BENEFICIARY_NAYOSE_FLG']
TRICS_cust_columns = ['APPLICANT', 'BENEFICIARY']
TRICS_ccif_columns = ['APPLICANT_C_CIF', 'APPLICANT_C_CIF_2', 'BENEFICIARY_C_CIF', 'BENEFICIARY_C_CIF_2']
TRICS_combined_columns = ['COMBINED_CUST', 'COMBINED_CUST_NEW', 'COMBINED_CUST_CCC', 'COMBINED_CUST_CO']
past_appl = ['COUNTRY_FROM', 'APPLICANT', 'APPLICANT_NAYOSE_FLG', 'PYTHON_COMPANY_A_BEST_MATCH', 'PYTHON_CCIF_A_BEST_MATCH',
             'PYTHON_A_HIGHEST_RATIO', 'PYTHON_A_UPDATE_TAG', 'UPDATE_FLAG_APPL']
past_bene = ['COUNTRY_TO', 'BENEFICIARY', 'BENEFICIARY_NAYOSE_FLG', 'PYTHON_CCIF_B_BEST_MATCH', 'PYTHON_COMPANY_B_BEST_MATCH', 
             'PYTHON_B_HIGHEST_RATIO', 'PYTHON_B_UPDATE_TAG', 'UPDATE_FLAG_BENE']


## Establish connection to mySQL server
def start_mySQL():
    conn = pyodbc.connect(r'DRIVER={MySQL ODBC 5.3 UNICODE Driver};'
                            r'SERVER=localhost;'
                            r'PORT=3306;'
                            r'DATABASE=gtbd;'
                            r'UID=root;'
                            r'PWD=root')
    cursor = conn.cursor()
    return conn, cursor


## Run query to return selected trics table from mySQL server
def return_table_data(TRICS_columns, TRICS_file, chunk_size, offset, GDWH_columns):
    # Convert TRICS_columns from list to string
    TRICS_column_list = ','.join(map(str, TRICS_columns))
    # Initialize list for subseuqent appendum of chunked trics table
    dfs = []
    while True:
        # Import selected trics table from mySQL server in chunks 
        sql = 'SELECT %s FROM %s limit %d offset %d;' % (TRICS_column_list, TRICS_file, chunk_size, offset)
        dfs.append(psql.read_sql(sql, conn))
        offset += chunk_size
        if len(dfs[-1]) < chunk_size:
            break
    # Join all chunks
    df_ = pd.concat(dfs)  
    return df_


## Run query to return GTBD_CUSTLIST, ISO_COUNTRY_CODE, DW_REMITTANCE, T_ACC_HOLDER and past update tables from mySQL server and store them in memory
def return_other_tables(past_appl_file, past_bene_file):
    # Import GDWH customer list from mySQL server
    GDWH_column_list = ','.join(map(str, GDWH_columns))
    df_gdwh = pd.read_sql('SELECT %s FROM gtbd_custlist WHERE %s IS NOT NULL;' % (GDWH_column_list, GDWH_columns[0]), con = conn)
    
    # Import ISO_COUNTRY_CODE from mySQL server
    iso_column_list = ','.join(map(str, ['TRICS', '`Mizuho Branch`']))
    df_iso = pd.read_sql('SELECT %s FROM iso_country_code WHERE %s = 1;' % (iso_column_list, '`Mizuho Branch`'), con = conn)
    # Change the word (1) 'VIET NAM' to 'VIETNAM', (2) 'KOREA, REPUBLIC OF' TO 'KOREA' in TRICS column
    df_iso['TRICS'] = df_iso['TRICS'].str.replace('VIET NAM', 'VIETNAM') 
    df_iso['TRICS'] = df_iso['TRICS'].str.replace('KOREA, REPUBLIC OF', 'KOREA')
    # Rename columns
    df_iso.rename(columns = {'TRICS': 'COUNTRY', 'Mizuho Branch': 'MIZUHO'}, inplace = True)
    
    # Import T_ACC_HOLDER from mySQL server
    t_acc_column_list = ','.join(map(str, [GDWH_ccif_columns[1]] + [GDWH_ccif_columns[2]]))
    df_dw = pd.read_sql('SELECT %s FROM t_acc_holder WHERE (%s AND %s IS NOT NULL) and %s NOT LIKE "*";' % (t_acc_column_list, GDWH_ccif_columns[1], GDWH_ccif_columns[2], GDWH_ccif_columns[2]), con = conn)
    
    # Import past APPLICANT updates
    past_appl_column_list = ','.join(map(str, past_appl))
    df_past_appl = pd.read_sql('SELECT %s FROM %s WHERE %s IS NOT NULL;' % (past_appl_column_list, past_appl_file, past_appl[-1]), con = conn)
    # Rename columns
    df_past_appl.rename(columns = {past_appl[0]: 'COUNTRY', 
                                   TRICS_cust_columns[0]: TRICS_combined_columns[0], 
                                   TRICS_nayose_columns[-2]: 'APPLICANT_NAYOSE_FLAG'}, inplace = True)
    
    # Import past BENEFICIARY updates
    past_bene_column_list = ','.join(map(str, past_bene))
    df_past_bene = pd.read_sql('SELECT %s FROM %s WHERE %s IS NOT NULL;' % (past_bene_column_list, past_bene_file, past_bene[-1]), con = conn)
    # Rename columns
    df_past_bene.rename(columns = {past_bene[0]: 'COUNTRY', 
                                   TRICS_cust_columns[1]: TRICS_combined_columns[0],
                                   TRICS_nayose_columns[-1]: 'BENEFICIARY_NAYOSE_FLAG'}, inplace = True)
    return df_gdwh, df_iso, df_dw, df_past_appl, df_past_bene

############################################### PARSE DATA: START ###############################################################

## Match APPLICANT_ACCOUNT/BENEFICIARY_ACCOUNT with DP_ACT_NO to get correct CCIF and Nayose flag
def nayose_ccif_update(df):  
    # Create new fields: APPLICANT_C_CIF_2 and BENEFICIARY_C_CIF_2
    df[TRICS_ccif_columns[1]] = ''
    df[TRICS_ccif_columns[3]] = ''
    
    # Match APPLICANT_ACCOUNT with DP_ACT_NO and get correct CCIF for all matched records
    df = pd.merge(df, df_dw, how = 'left', left_on = TRICS_nayose_columns[-4], right_on = GDWH_ccif_columns[1])
    # Assign CUST_NO_CCIF values to APPLICANT_C_CIF_2
    df[TRICS_ccif_columns[1]] = df[GDWH_ccif_columns[2]][df[GDWH_ccif_columns[2]].notnull()]
    # Remove unnecessary columns 
    del df[GDWH_ccif_columns[1]], df[GDWH_ccif_columns[2]]
    
    # Match BENEFICIARY_ACCOUNT with DP_ACT_NO and get correct CCIF for all matched records
    df = pd.merge(df, df_dw, how = 'left', left_on = TRICS_nayose_columns[-3], right_on = GDWH_ccif_columns[1])
    # Assign CUST_NO_CCIF values to BENEFICIARY_C_CIF_2
    df[TRICS_ccif_columns[3]] = df[GDWH_ccif_columns[2]][df[GDWH_ccif_columns[2]].notnull()]
    # Remove unnecessary columns 
    del df[GDWH_ccif_columns[1]], df[GDWH_ccif_columns[2]]
    
    # Update APPLICANT_NAYOSE_FLAG and BENEFICIARY_NAYOSE_FLAG to 1 for all matched records
    df[TRICS_nayose_columns[-2]][df[TRICS_ccif_columns[1]].notnull()] = 1 
    df[TRICS_nayose_columns[-1]][df[TRICS_ccif_columns[3]].notnull()] = 1 
    
    # Assign original APPLICANT_C_CIF and BENEFICIARY_C_CIF to APPLICANT_C_CIF_2 and BENEFICIARY_C_CIF_2 if the latter columns are null
    df[TRICS_ccif_columns[1]][df[TRICS_ccif_columns[1]].isnull()] = df[TRICS_ccif_columns[0]][df[TRICS_ccif_columns[1]].isnull()]
    df[TRICS_ccif_columns[3]][df[TRICS_ccif_columns[3]].isnull()] = df[TRICS_ccif_columns[2]][df[TRICS_ccif_columns[3]].isnull()]
    return df

## Parse data in standardized format
def parse_table_data(TRICS_columns, TRICS_cust_columns, TRICS_combined_columns, GDWH_combined_columns): 
    # Create TRICS customer DataFrames: df1 (RM/Applicant) and df2 (Beneficiary) using df_   
    df1 = df_[[TRICS_columns[0], TRICS_columns[4]]]
    df1.columns = ['COUNTRY', TRICS_combined_columns[0]]
    df2 = df_[[TRICS_columns[1], TRICS_columns[6]]]
    df2.columns = ['COUNTRY', TRICS_combined_columns[0]]
    # Combine both customer DataFrames: df1 and df2
    df_combined = df1.append(df2, ignore_index = True)
    # Change the word (1) 'VIET NAM' to 'VIETNAM', (2) 'KOREA, REPUBLIC OF' TO 'KOREA' ...
    # (3) 'NETHERLANDS' to 'NETHERLAND' and (4) 'LAO PEOPLES' to "LAO PEOPLE'S" in COUNTRY column
    df_combined['COUNTRY'] = df_combined['COUNTRY'].str.replace('VIET NAM', 'VIETNAM') 
    df_combined['COUNTRY'] = df_combined['COUNTRY'].str.replace('KOREA, REPUBLIC OF', 'KOREA')
    df_combined['COUNTRY'] = df_combined['COUNTRY'].str.replace('NETHERLANDS', 'NETHERLAND')
    df_combined['COUNTRY'] = df_combined['COUNTRY'].str.replace("LAO PEOPLES", "LAO PEOPLE'S")
    # Drop NaNs and duplicates in combined column
    df_combined[TRICS_combined_columns[0]].replace('', np.nan, inplace = True)
    df_combined.dropna(subset = [TRICS_combined_columns[0]], inplace = True)
    df_combined.drop_duplicates(subset = ['COUNTRY', TRICS_combined_columns[0]], inplace = True)
    # Sort remaining companies in ascending order
    df_combined.sort_values(by = TRICS_combined_columns[0], inplace = True)
    # Clean/Standardize customer names
    df_combined = clean_data(df_combined, TRICS_combined_columns[0], TRICS_combined_columns[1])

    # Create GDWH customer DataFrame: df_customers using df_gdwh
    df_customers = df_gdwh.copy()
    # Drop all duplicates fromm GDWH customer names
    df_customers.dropna(subset = [GDWH_columns[0], GDWH_columns[1]], inplace = True)
    df_customers.drop_duplicates(subset = [GDWH_columns[0], GDWH_columns[2]], inplace = True)
    # Drop all invalid customer names, e.g. DUMMY, DELETED, DORMANT etc.
    drop_list = ['DUMMY', 'DELETED', 'DORMANT', 'ABOLISH', 'REQUIRED FOR LONDON', 'TO BE USED', 'DUPLICATE', 'ITRAXX', 'DO NOT USE', 'LIMITED A C', 'LIMITED PURPOSE']
    df_customers = df_customers[~df_customers[GDWH_columns[0]].str.contains('|'.join(drop_list))]
    # Re-adjust column order
    df_customers = df_customers[[GDWH_columns[2], GDWH_columns[1], GDWH_columns[0]]]
    # Change the word 'VIET NAM' to 'VIETNAM', (2) 'NETHERLANDS' to 'NETHERLAND' and (3) 'LAO PEOPLES' to "LAO PEOPLE'S" in COUNTRY column
    df_customers['COUNTRY'] = df_customers['COUNTRY'].str.replace('VIET NAM', 'VIETNAM') 
    df_customers['COUNTRY'] = df_customers['COUNTRY'].str.replace('NETHERLANDS', 'NETHERLAND')
    df_customers['COUNTRY'] = df_customers['COUNTRY'].str.replace("LAO PEOPLES", "LAO PEOPLE'S")
    # Clean/Standardize customer names
    df_customers = clean_data(df_customers, GDWH_combined_columns[0], GDWH_combined_columns[1])
    # Drop all duplicates fromm GDWH customer names
    df_customers.drop_duplicates(subset = [GDWH_columns[2], GDWH_combined_columns[1]], inplace = True)

    # Standardize each country's abbreviation in both DataFrames
    df_combined = parse_abb('CountryAbbreviations.xlsx', df_combined, TRICS_combined_columns[1])
    df_customers = parse_abb('CountryAbbreviations.xlsx', df_customers, GDWH_combined_columns[1])
    
    # Standardize each sector's abbreviation in both DataFrames
    df_combined = parse_abb('SectorAbbreviations.xlsx', df_combined, TRICS_combined_columns[1])
    df_customers = parse_abb('SectorAbbreviations.xlsx', df_customers, GDWH_combined_columns[1])
    
    # Remove specific company's abbreviation if it is found in the company string
    # Based on user's naming preference,the positions of these specific abbreviations are inconsistent across datasets (i.e. sometimes front, sometimes end)...
    # Thus, we need to remove them from the company names so that they would not influence our subsequent matching 
    df_combined = remove_abb('CompanyAbbRemove.xlsx', df_combined, TRICS_combined_columns[1])
    df_customers = remove_abb('CompanyAbbRemove.xlsx', df_customers, GDWH_combined_columns[1])
 
    # Create a new column to store RM/LC data
    df_combined[TRICS_combined_columns[2]] = df_combined[TRICS_combined_columns[1]]
    df_customers[GDWH_combined_columns[2]] = df_customers[GDWH_combined_columns[1]]
    df_combined[TRICS_combined_columns[3]] = df_combined[TRICS_combined_columns[1]]
    df_customers[GDWH_combined_columns[3]] = df_customers[GDWH_combined_columns[1]]
    
    # Standardize remaining companies' abbreviation and country/capital/city in both DataFrames 
    df_combined = parse_ccc_abb('CompanyAbbreviations.xlsx', 'CountriesCapitalsCities.xlsx', df_combined, TRICS_combined_columns[2], TRICS_combined_columns[3])
    df_customers = parse_ccc_abb('CompanyAbbreviations.xlsx', 'CountriesCapitalsCities.xlsx', df_customers, GDWH_combined_columns[2], GDWH_combined_columns[3])      
    return df_combined, df_customers

def clean_data(df, dseries_old, dseries):
    # Drop all non-alphanumeric characters from selected DataFrame customer names
    df[dseries] = df[dseries_old].str.replace(r'[^\w\s]', ' ')
    # Drop all leading (supsicious) numbers from selected DataFrame customer names
    df[dseries] = df[dseries][df[dseries].str[0:5].replace(' ', '').str.isdigit()].str.replace(r'^\d+', '')
    df[dseries].fillna(df[dseries_old][df[dseries].isnull()], inplace = True)
    df[dseries] = df[dseries].str.replace(r'[^\w\s]', ' ')
    # Drop all supsicious characters from selected DataFrame customer names   
    df[dseries][df[dseries].str.find('AND ') > 0] = df[dseries][df[dseries].str.find('AND ') > 0].str.replace(r'\b%s\b' % 'AND', '')   
    df[dseries] = df[dseries].str.replace(r'\b%s\b' % 'OF', '')
    df[dseries][df[dseries].str.find('THE ') == 0] = df[dseries][df[dseries].str.find('THE ') == 0].str.replace(r'\b%s\b' % 'THE', '')
    df[dseries] = df[dseries].str.replace(r'^\d+\s\d+', '')
    # Drop all potential addresses from selected DataFrame customer names
    df[dseries] = df[dseries].str.split(r'\b%s\b' % 'PLS').str[0]
    df[dseries] = df[dseries].str.split(r'\b%s\b' % 'BLDG').str[0]
    df[dseries] = df[dseries].str.split(r'\b%s\b' % 'NO').str[0]
    df[dseries] = df[dseries].str.split(r'\b%s\b' % 'SEE').str[0]
    df[dseries] = df[dseries].str.split(r'\b%s\b' % 'UNIT').str[0]
    df[dseries][~df[dseries].str.contains('TRANS PACIFIC SHIPPING')] = df[dseries][~df[dseries].str.contains('TRANS PACIFIC SHIPPING')].str.split(r'\s\d+').str[0]
    df[dseries][(~df[dseries].str.split().str[0].str.contains(r'\D\d+', na = False)) & (~df[dseries].str.contains('TRANS PACIFIC SHIPPING'))] = (df[dseries]
    [(~df[dseries].str.split().str[0].str.contains(r'\D\d+', na = False)) & (~df[dseries].str.contains('TRANS PACIFIC SHIPPING'))].str.split(r'\D\d+').str[0])
    # Drop empty cells and strip redundant spaces
    df = df[df[dseries] != '']
    df[dseries] = df[dseries].str.replace('[\s]{2,}', ' ').str.strip()      
    return df

def parse_abb(file, df, dseries):
    # Load relevant file
    df_std = pd.read_excel(file)
    # Create a string to join all abbreviations in 'SHORT' column 
    pattern = (r'\b%s\b' % '|').join(df_std['SHORT'])
    # List all DataFrame rows with abbreviations in 'SHORT' column, regardless of their position
    df['SHORT'] = df[dseries].str.extract('(' + r'\b%s\b' % pattern + ')', expand = False)
    df['TEMP'] = df['SHORT']
    df['TEMP'].fillna(df[dseries][df['SHORT'].isnull()], inplace = True)
    # Do a left join with the full name
    df = pd.merge(df, df_std, how = 'left', on = 'SHORT')
    # Replace abbreviated DataFrame rows with full name in 'LONG' column
    df[dseries] = df.dropna(subset = ['SHORT']).apply(lambda x: x[dseries].replace(x['SHORT'],x['LONG']), axis=1)
    df[dseries].fillna(df['TEMP'][df[dseries].isnull()], inplace = True)
    # Drop empty cells and strip redundant spaces
    df = df[df[dseries] != '']
    df[dseries] = df[dseries].str.replace('[\s]{2,}', ' ').str.strip()
    # Remove redundant columns and free up memory
    del df['SHORT'], df['LONG'], df['TEMP']
    return df

def remove_abb(file, df, dseries):
    # Load relevant file
    df_std = pd.read_excel(file)
    # Create a string to join all abbreviations in 'SHORT' column
    pattern = (r'\b%s\b' % '|').join(df_std['SHORT'])
    # List DataFrame rows with abbreviations
    df['SHORT'] = df[dseries].str.extract('(' + r'\b%s\b' % pattern + ')', expand = False)
    df['TEMP'] = df['SHORT']
    df['TEMP'].fillna(df[dseries][df['SHORT'].isnull()], inplace = True)
    # Create a string to join all abbreviations in 'SHORT' column
    pattern = (r'\b%s\b' % '|').join(df_std['SHORT'].dropna())
    # Remove abbreviations from relevant DataFrame rows 
    df[dseries] = df.dropna(subset = ['SHORT'])[dseries].str.replace('(' + r'\b%s\b' % pattern + ')', '').str.strip()
    df[dseries].fillna(df['TEMP'][df[dseries].isnull()], inplace = True)
    # Drop any duplicate words within same company name, e.g. FORD VIETNAM FORD VIETNAM 
    df[dseries] = df[dseries].apply(lambda x: ' '.join(sorted(set(x.split()), key=x.split().index)))
    # Drop empty cells and strip redundant spaces
    df = df[df[dseries] != '']
    df[dseries] = df[dseries].str.replace('[\s]{2,}', ' ').str.strip()
    # Remove redundant columns and free up memory
    del df['SHORT'], df['TEMP']
    return df

def parse_ccc_abb(file_std, file_ccc, df, dseries, dseries2):
    # Load relevant files - country/capital/city and company abbreviations
    df_std = pd.read_excel(file_std) 
    df_ccc = pd.read_excel(file_ccc)
    # Create a string to join all abbreviations for each file
    pattern_std = (r'\b%s\b' % '|').join(df_std['SHORT'])
    pattern_ccc = (r'\b%s\b' % '|').join(df_ccc['ENTITIES'])
    
    # List DataFrame rows with company abbreviations in 'SHORT' column, regardless of their position
    df['SHORT'] = df[dseries2][df[dseries2].str.split('(' + r'\b%s\b' % pattern_std + ')').str[0] != ''].str.extract('(' + r'\b%s\b' % pattern_std + ')', expand = False)
    df['TEMP'] = df['SHORT']
    df['TEMP'].fillna(df[dseries2][df['SHORT'].isnull()], inplace = True)
    df = pd.merge(df, df_std, how = 'left', on = 'SHORT')
    # Replace abbreviated DataFrame rows with full name in 'LONG' column
    df[dseries2] = df.dropna(subset = ['SHORT']).apply(lambda x: x[dseries2].replace(x['SHORT'],x['LONG']), axis=1)
    df[dseries2].fillna(df['TEMP'][df[dseries2].isnull()], inplace = True)
    # Drop empty cells 
    df = df[df[dseries2] != '']
    # If the word 'INTERNATIONAL' appears from 4th word onwards, drop all subsequent words 
    df[dseries2][df[dseries2].str.split().str[3:].str.join(' ').str.contains('INTERNATIONAL')] = (df[dseries2]
    [df[dseries2].str.split().str[3:].str.join(' ').str.contains('INTERNATIONAL')].str.split('INTERNATIONAL').str[0] + 'INTERNATIONAL')
    # If the company does not end with the word 'HOLDINGS', remove 'HOLDINGS' 
#    df[dseries2][df[dseries2].str.split().str[:-1].str.join(' ').str.contains('HOLDINGS')] = (df[dseries2]
#    [df[dseries2].str.split().str[:-1].str.join(' ').str.contains('HOLDINGS')].str.replace(r'\b%s\b' % 'HOLDINGS', ''))
#    # If the company ends with the word 'COMPANY LIMITED', remove 'LIMITED' 
#    df[dseries2][df[dseries2].str.split().str[-2:].str.join(' ').str.contains('COMPANY LIMITED')] = (df[dseries2]
#    [df[dseries2].str.split().str[-2:].str.join(' ').str.contains('COMPANY LIMITED')].str.replace(r'\b%s\b' % 'COMPANY LIMITED', 'COMPANY'))
    # Strip redundant spaces
    df[dseries2] = df[dseries2].str.replace('[\s]{2,}', ' ').str.strip()
    # Remove redundant columns
    del df['SHORT'], df['LONG'], df['TEMP']
    
    # List DataFrame rows with country/capital/city abbreviations
    df[dseries] = df[dseries2]
    df['CCC'] = df[dseries2]
    df['TEMP_CCC'] = df[dseries].str.extract('(' + r'\b%s\b' % pattern_ccc + ')', expand = False)
    # List DataFrame rows that do not begin with country/capital/city (i.e. first 3 words must not contain country/capital/city)
    df[dseries] = df[dseries][~df[dseries].str.split().str[0:3].str.join(' ').str.contains('(' + r'\b%s\b' % pattern_ccc + ')')]
    # Remove any text after country/capital/city abbreviations for DataFrame rows that do not begin with country/capital/city
    df[dseries] = df.dropna(subset = [dseries])['CCC'].str.split('(' + r'\b%s\b' % pattern_ccc + ')').str[0] + df.dropna(subset = [dseries])['TEMP_CCC'] 
    df[dseries].fillna(df['CCC'][df[dseries].isnull()], inplace = True)
    # Drop empty cells and strip redundant spaces
    df = df[df[dseries] != '']
    df[dseries] = df[dseries].str.replace('[\s]{2,}', ' ').str.strip()
    # Remove redundant columns and free up memory
    del df['CCC'], df['TEMP_CCC']
    return df

############################################### PARSE DATA: END #################################################################  
    

############################################### FUZZY MATCH: START ###############################################################    

## Perform exact and fuzzy matching
def total_match():        
    # Initialize Dataframes
    df_exact_match = df_combined.copy()
    df_cust_simple = pd.DataFrame({})
    # Perform exact matching between modified and original columns in both TRICS and GDWH
    df_exact_match = exact_match_modified_ccc(df_exact_match, TRICS_combined_columns[2], 'BEST_CCC', 'BEST_CCC_CCIF', 
                                         'BEST_CCC_RATIO', 'BEST_CCC_TAG', df_cust_simple)
    df_exact_match = exact_match_modified_co(df_exact_match, TRICS_combined_columns[3], 'BEST_CO', 'BEST_CO_CCIF', 
                                         'BEST_CO_RATIO', 'BEST_CO_TAG', df_cust_simple)
    df_exact_match = exact_match_modified_new(df_exact_match, TRICS_combined_columns[1], 'BEST_NEW', 'BEST_NEW_CCIF', 
                                         'BEST_NEW_RATIO', 'BEST_NEW_TAG', df_cust_simple)
    df_exact_match = exact_match_original(df_exact_match, TRICS_combined_columns[0], 'BEST_ORIGIN_CCIF', 
                                      'BEST_ORIGIN_RATIO', 'BEST_ORIGIN_TAG', df_cust_simple)
    
    # Combine all individual results into consolidated columns   
    df_exact_match['COMPANY_BEST_MATCH'] = df_exact_match[df_exact_match['BEST_CCC'].notnull()]['BEST_CCC']
    df_exact_match['COMPANY_BEST_MATCH'][df_exact_match['BEST_CO'].notnull()] = df_exact_match[df_exact_match['BEST_CO'].notnull()]['BEST_CO']
    df_exact_match['COMPANY_BEST_MATCH'][df_exact_match['BEST_NEW'].notnull()] = df_exact_match[df_exact_match['BEST_NEW'].notnull()]['BEST_NEW']
    df_exact_match['COMPANY_BEST_MATCH'][df_exact_match['BEST_ORIGIN'].notnull()] = df_exact_match[df_exact_match['BEST_ORIGIN'].notnull()]['BEST_ORIGIN']
    
    df_exact_match['CCIF_BEST_MATCH'] = df_exact_match[df_exact_match['BEST_CCC_CCIF'].notnull()]['BEST_CCC_CCIF']
    df_exact_match['CCIF_BEST_MATCH'][df_exact_match['BEST_CO_CCIF'].notnull()] = df_exact_match[df_exact_match['BEST_CO_CCIF'].notnull()]['BEST_CO_CCIF']
    df_exact_match['CCIF_BEST_MATCH'][df_exact_match['BEST_NEW_CCIF'].notnull()] = df_exact_match[df_exact_match['BEST_NEW_CCIF'].notnull()]['BEST_NEW_CCIF']
    df_exact_match['CCIF_BEST_MATCH'][df_exact_match['BEST_ORIGIN_CCIF'].notnull()] = df_exact_match[df_exact_match['BEST_ORIGIN_CCIF'].notnull()]['BEST_ORIGIN_CCIF']
    
    df_exact_match['HIGHEST_RATIO'] = df_exact_match[df_exact_match['BEST_CCC_RATIO'].notnull()]['BEST_CCC_RATIO']
    df_exact_match['HIGHEST_RATIO'][df_exact_match['BEST_CO_RATIO'].notnull()] = df_exact_match[df_exact_match['BEST_CO_RATIO'].notnull()]['BEST_CO_RATIO']
    df_exact_match['HIGHEST_RATIO'][df_exact_match['BEST_NEW_RATIO'].notnull()] = df_exact_match[df_exact_match['BEST_NEW_RATIO'].notnull()]['BEST_NEW_RATIO']
    df_exact_match['HIGHEST_RATIO'][df_exact_match['BEST_ORIGIN_RATIO'].notnull()] = df_exact_match[df_exact_match['BEST_ORIGIN_RATIO'].notnull()]['BEST_ORIGIN_RATIO']
    
    df_exact_match['UPDATE_TAG'] = df_exact_match[df_exact_match['BEST_CCC_TAG'].notnull()]['BEST_CCC_TAG']
    df_exact_match['UPDATE_TAG'][df_exact_match['BEST_CO_TAG'].notnull()] = df_exact_match[df_exact_match['BEST_CO_TAG'].notnull()]['BEST_CO_TAG']
    df_exact_match['UPDATE_TAG'][df_exact_match['BEST_NEW_TAG'].notnull()] = df_exact_match[df_exact_match['BEST_NEW_TAG'].notnull()]['BEST_NEW_TAG']
    df_exact_match['UPDATE_TAG'][df_exact_match['BEST_ORIGIN_TAG'].notnull()] = df_exact_match[df_exact_match['BEST_ORIGIN_TAG'].notnull()]['BEST_ORIGIN_TAG']
    
    # Perform join and change UPDATE_TAG to 'NO COUNTRY BRANCH' if Mizuho does not have a branch in specific country 
    df_exact_match = pd.merge(df_exact_match, df_iso, how = 'left', on = 'COUNTRY')
    df_exact_match['UPDATE_TAG'][df_exact_match['MIZUHO'].isnull()] = 'NO COUNTRY BRANCH'
    
    # Update past APPLICANT and BENEFICIARY results against current dataset
    df_exact_match = pd.merge(df_exact_match, df_past_appl, how = 'left', on = ['COUNTRY', 'COMBINED_CUST'])
    df_exact_match = pd.merge(df_exact_match, df_past_bene, how = 'left', on = ['COUNTRY', 'COMBINED_CUST'])
    df_exact_match['COMPANY_BEST_MATCH'][df_exact_match['UPDATE_FLAG_APPL'] == 'Y'] = df_exact_match[df_exact_match['UPDATE_FLAG_APPL'] == 'Y']['PYTHON_COMPANY_A_BEST_MATCH']
    df_exact_match['COMPANY_BEST_MATCH'][df_exact_match['UPDATE_FLAG_BENE'] == 'Y'] = df_exact_match[df_exact_match['UPDATE_FLAG_BENE'] == 'Y']['PYTHON_COMPANY_B_BEST_MATCH']
    df_exact_match['CCIF_BEST_MATCH'][df_exact_match['UPDATE_FLAG_APPL'] == 'Y'] = df_exact_match[df_exact_match['UPDATE_FLAG_APPL'] == 'Y']['PYTHON_CCIF_A_BEST_MATCH']
    df_exact_match['CCIF_BEST_MATCH'][df_exact_match['UPDATE_FLAG_BENE'] == 'Y'] = df_exact_match[df_exact_match['UPDATE_FLAG_BENE'] == 'Y']['PYTHON_CCIF_B_BEST_MATCH']
    df_exact_match['HIGHEST_RATIO'][df_exact_match['UPDATE_FLAG_APPL'] == 'Y'] = df_exact_match[df_exact_match['UPDATE_FLAG_APPL'] == 'Y']['PYTHON_A_HIGHEST_RATIO']
    df_exact_match['HIGHEST_RATIO'][df_exact_match['UPDATE_FLAG_BENE'] == 'Y'] = df_exact_match[df_exact_match['UPDATE_FLAG_BENE'] == 'Y']['PYTHON_B_HIGHEST_RATIO']
    df_exact_match['UPDATE_TAG'][df_exact_match['UPDATE_FLAG_APPL'] == 'Y'] = 'PAST MANUAL CHECKING'
    df_exact_match['UPDATE_TAG'][df_exact_match['UPDATE_FLAG_BENE'] == 'Y'] = 'PAST MANUAL CHECKING'
    
    # Remove redundant columns
    del df_exact_match[TRICS_combined_columns[1]], df_exact_match[TRICS_combined_columns[2]], df_exact_match['MIZUHO']
    del df_exact_match['BEST_CCC'], df_exact_match['BEST_CO'], df_exact_match['BEST_NEW'], df_exact_match['BEST_ORIGIN']
    del df_exact_match['BEST_CCC_CCIF'], df_exact_match['BEST_CO_CCIF'], df_exact_match['BEST_NEW_CCIF'], df_exact_match['BEST_ORIGIN_CCIF']
    del df_exact_match['BEST_CCC_RATIO'], df_exact_match['BEST_CO_RATIO'], df_exact_match['BEST_NEW_RATIO'], df_exact_match['BEST_ORIGIN_RATIO']
    del df_exact_match['BEST_CCC_TAG'], df_exact_match['BEST_CO_TAG'], df_exact_match['BEST_NEW_TAG'], df_exact_match['BEST_ORIGIN_TAG']
    del df_exact_match['APPLICANT_NAYOSE_FLAG'], df_exact_match['PYTHON_COMPANY_A_BEST_MATCH'], df_exact_match['PYTHON_CCIF_A_BEST_MATCH']
    del df_exact_match['PYTHON_A_HIGHEST_RATIO'], df_exact_match['PYTHON_A_UPDATE_TAG'], df_exact_match['UPDATE_FLAG_APPL']
    del df_exact_match['BENEFICIARY_NAYOSE_FLAG'], df_exact_match['PYTHON_COMPANY_B_BEST_MATCH'], df_exact_match['PYTHON_CCIF_B_BEST_MATCH']
    del df_exact_match['PYTHON_B_HIGHEST_RATIO'], df_exact_match['PYTHON_B_UPDATE_TAG'], df_exact_match['UPDATE_FLAG_BENE']
    
    # Query out the list of NaN cases in df_exact_match for complex fuzzy matching
    df_fuzzy_match = df_exact_match[(df_exact_match['HIGHEST_RATIO'].isnull()) & (df_exact_match['UPDATE_TAG'].isnull())]  
    # Drop all duplicates in df_fuzzy_match
    df_fuzzy_match.drop_duplicates(subset = [TRICS_combined_columns[0], 'COUNTRY'], inplace = True)
    # Remove remaining redundant columns from df_exact_match
    df_exact_match.drop_duplicates(subset = [TRICS_combined_columns[0], 'COUNTRY'], inplace = True)
    del df_exact_match[TRICS_combined_columns[3]]
    df_exact_match = df_exact_match[df_exact_match['UPDATE_TAG'].notnull()]
    # Print status
    print('Exact matching completed!')
#    # Download exact matching results
#    df_exact_match.to_excel(r'Y:\MRDD_Temp\%s_LC_ExactMatch.xlsx' % datetime.datetime.now().strftime('%Y%m%d'))
    
    # Initialize counter for complex fuzzy matching
    count = 0
    # Query GDWH rows that have first 2 identical words as df_fuzzy_match
    df_fuzzy_match['TEMP'] = df_fuzzy_match['COMBINED_CUST_CO'].str.split().str[0:2].str.join(' ') #+ ' ' + df_fuzzy_match['COUNTRY']
    # Create a copy of df_customers
    df_cust = df_customers.copy()
    # Query the first 2 words for all GDWH company names in df_cust
    df_cust[GDWH_combined_columns[3]] = df_cust[GDWH_combined_columns[3]].str.split().str[0:2].str.join(' ') #+ ' ' + df_cust[GDWH_columns[2]] 
    # Remove redundant columns and rearrange/rename the remaining columns
    del df_cust[GDWH_combined_columns[0]], df_cust[GDWH_combined_columns[1]], df_cust[GDWH_combined_columns[2]], df_cust[GDWH_columns[2]] 
    df_cust = df_cust[[GDWH_columns[1], GDWH_combined_columns[3]]]
    df_cust.columns = [GDWH_columns[1], 'TEMP']
    df_cust.drop_duplicates('TEMP', inplace = True)
    # Query GDWH rows that have first 2 identical words as df_fuzzy_match
    df_fuzzy_match = pd.merge(df_fuzzy_match, df_cust, how = 'left', on = 'TEMP')
    # Remove any rows that do not have first 2 identical words, i.e. NaN, in C_CIF_NO column only 
    df_fuzzy_match.dropna(subset  = ['C_CIF_NO'], inplace = True)
    # Remove unnecessary columns 
    del df_fuzzy_match['TEMP'], df_fuzzy_match['C_CIF_NO']
    # Start complex fuzzy matching
    for row in df_fuzzy_match.itertuples():
        # Query GDWH rows that have first 2 identical words as df_fuzzy_match
        condition1 = (df_customers[GDWH_combined_columns[3]].str.split().str[0:2].str.join(' ') == (r'%s' % ' '.join(row[3].split()[0:2])))
        condition2 = (df_customers[GDWH_combined_columns[3]].str.find(r'%s' % ' '.join(row[3].split()[0:2])) >= 0)
        orig_company_match = df_customers[GDWH_combined_columns[0]][condition1 & condition2]
        if len(orig_company_match) != 0:
            # Initialize temporary DataFrame: df_match
            df_match = pd.DataFrame({'TRICS_COMPANY_CO': [], 'TRICS_COUNTRY': [], 'GDWH_COMPANY_CO': [], 'GDWH_COMPANY': [], 'GDWH_CCIF': [], 'GDWH_COUNTRY': [], 'RATIO': []})
            # Assign column in df_match to list variable
            df_match['GDWH_COMPANY_CO'] = df_customers[GDWH_combined_columns[3]][condition1 & condition2]
            df_match['GDWH_COMPANY'] = df_customers[GDWH_combined_columns[0]][condition1 & condition2]
            df_match['GDWH_CCIF'] = df_customers[GDWH_columns[1]][condition1 & condition2]
            df_match['GDWH_COUNTRY'] = df_customers[GDWH_columns[2]][condition1 & condition2]
            df_match['TRICS_COMPANY_CO'] = np.tile(row[3], (len(orig_company_match),1))
            df_match['TRICS_COUNTRY'] = np.tile(row[1], (len(orig_company_match),1))
            # Compute string similarity ratios 
            df_match['RATIO'] = df_match.apply(lambda x: get_closest_match(x['TRICS_COMPANY_CO'], x['TRICS_COUNTRY'], x['GDWH_COMPANY_CO'], x['GDWH_COUNTRY'], ratio), axis = 1)
            # Perform 1st level fuzzy matching: Similar name matching for unique GDWH companies
            if max(df_match['RATIO']) != 0: 
                df_fuzzy_match['COMPANY_BEST_MATCH'][(df_fuzzy_match[TRICS_combined_columns[3]] == row[3]) & (df_fuzzy_match[GDWH_columns[2]] == row[1])] = df_match['GDWH_COMPANY'][df_match['RATIO'] == max(df_match['RATIO'])].iloc[0]
                df_fuzzy_match['CCIF_BEST_MATCH'][(df_fuzzy_match[TRICS_combined_columns[3]] == row[3]) & (df_fuzzy_match[GDWH_columns[2]] == row[1])] = df_match['GDWH_CCIF'][df_match['RATIO'] == max(df_match['RATIO'])].iloc[0]
                df_fuzzy_match['HIGHEST_RATIO'][(df_fuzzy_match[TRICS_combined_columns[3]] == row[3]) & (df_fuzzy_match[GDWH_columns[2]] == row[1])] = max(df_match['RATIO'])
                df_match = df_match[df_match['TRICS_COUNTRY'] == df_match['GDWH_COUNTRY']]
                # Perform 2nd level fuzzy matching: Combine country data for similar name matching of multiple GDWH companies
                if len(df_match) >= 1 and df_fuzzy_match['COMPANY_BEST_MATCH'][(df_fuzzy_match[TRICS_combined_columns[3]] == row[3]) & (df_fuzzy_match[GDWH_columns[2]] == row[1])].iloc[0] == df_match['GDWH_COMPANY'][df_match['RATIO'] == max(df_match['RATIO'])].iloc[0]:   
                    df_fuzzy_match['COMPANY_BEST_MATCH'][(df_fuzzy_match[TRICS_combined_columns[3]] == row[3]) & (df_fuzzy_match[GDWH_columns[2]] == row[1])] = df_match['GDWH_COMPANY'][df_match['RATIO'] == max(df_match['RATIO'])].iloc[0]
                    df_fuzzy_match['CCIF_BEST_MATCH'][(df_fuzzy_match[TRICS_combined_columns[3]] == row[3]) & (df_fuzzy_match[GDWH_columns[2]] == row[1])] = df_match['GDWH_CCIF'][df_match['RATIO'] == max(df_match['RATIO'])].iloc[0]
                    df_fuzzy_match['HIGHEST_RATIO'][(df_fuzzy_match[TRICS_combined_columns[3]] == row[3]) & (df_fuzzy_match[GDWH_columns[2]] == row[1])] = max(df_match['RATIO'])
        # Track progress of fuzzy matching
        count += 1
        if count % 500 == 0:
            print('Progress: %d out of %d' % (count, len(df_fuzzy_match)))
    # Assign null values in df_fuzzy_match
    df_fuzzy_match['COMPANY_BEST_MATCH'].fillna('', inplace = True)
    df_fuzzy_match['CCIF_BEST_MATCH'].fillna('', inplace = True)
    df_fuzzy_match['HIGHEST_RATIO'].fillna(0, inplace = True)
    # Assign UPDATE_TAG if it HIGHEST_RATIO meets the following criterion:
    # (1) 'EXACT NAME' if HIGHEST_RATIO is 0.99 and above
    # (2) 'SIMILAR NAME' if HIGHEST_RATIO is between 0 and 0.99 (both numbers are exclusive)
    # (3) 'N' if otherwise 
    df_fuzzy_match['UPDATE_TAG'][df_fuzzy_match['HIGHEST_RATIO'] >= 0.99] = 'EXACT NAME'
    df_fuzzy_match['UPDATE_TAG'][(df_fuzzy_match['HIGHEST_RATIO'] > 0) & (df_fuzzy_match['HIGHEST_RATIO'] < 0.99)] = 'SIMILAR NAME'
    df_fuzzy_match['UPDATE_TAG'].fillna('N', inplace = True)
    # Reformat the CCIF_BEST_MATCH and HIGHEST RATIO fields 
    df_fuzzy_match['CCIF_BEST_MATCH'] = df_fuzzy_match['CCIF_BEST_MATCH'].astype(str)
    df_fuzzy_match['HIGHEST_RATIO'] = df_fuzzy_match['HIGHEST_RATIO'].astype(str)
    # Print status
    print('Complex fuzzy matching completed!')
    # Remove redundant columns from df_fuzzy_match
    del df_fuzzy_match[TRICS_combined_columns[3]]
#    # Download fuzzy matching results
#    df_fuzzy_match.to_excel(r'Y:\MRDD_Temp\%s_LC_FuzzyMatch.xlsx' % datetime.datetime.now().strftime('%Y%m%d'))
    return df_exact_match, df_fuzzy_match
    
def exact_match_modified_ccc(df, dseries, dseries_co, dseries_ccif, dseries_ratio, dseries_tag, df_cust):
    # Drop all blanks in df
    df[dseries].replace('', np.nan, inplace = True)
    df.dropna(subset = [dseries], inplace = True)
    df[dseries_ratio] = ''
    df[dseries_tag] = ''   
    # Create df_cust copy using df_customers
    df_cust = df_customers.copy()
    # Remove redundant columns
    del df_cust[GDWH_combined_columns[1]], df_cust[GDWH_combined_columns[3]]
    # Reorder/Rename remaining columns
    df_cust = df_cust[[GDWH_combined_columns[2], GDWH_combined_columns[0], GDWH_columns[1], GDWH_columns[2]]]
    df_cust.columns = [dseries, dseries_co, dseries_ccif, GDWH_columns[2]]
    # Create df_match copy using df_cust
    df_match = df_cust.copy()
#    df_match = df_cust.loc[df_cust[dseries].str.replace(' ', '').isin(df[dseries].str.replace(' ', '')), [dseries, dseries_co, dseries_ccif]]
    # Remove common company abbreviations from company name in df_match
    df_match['TEMP'] = df_match[dseries].str.split(r'\b%s\b' % 'COMPANY LIMITED').str[0]
    df_match['TEMP'] = df_match['TEMP'].str.split(r'\b%s\b' % 'LIMITED').str[0]
    df_match['TEMP'] = df_match['TEMP'].str.split(r'\b%s\b' % 'INCORPORATED').str[0]
     # Create a string with remaining company name and country details for standardization between TRICS and GDWH
    df_match['TEMP'] = df_match['TEMP'] + ' ' + df_match['COUNTRY']
    # Remove any country duplicates if present in company name string
    df_match['TEMP'] = df_match['TEMP'].apply(lambda x: ' '.join(sorted(set(x.split()[::-1]), key=x.split()[::-1].index)[::-1]))
    df_match['TEMP'] = df_match['TEMP'].str.replace(' ', '')
    del df_match[dseries], df_match['COUNTRY']
    # Remove common company abbreviations from company name in df
    df['TEMP'] = df[dseries].str.split(r'\b%s\b' % 'COMPANY LIMITED').str[0]
    df['TEMP'] = df['TEMP'].str.split(r'\b%s\b' % 'LIMITED').str[0]
    df['TEMP'] = df['TEMP'].str.split(r'\b%s\b' % 'INCORPORATED').str[0]
    # Create a string with remaining company name and country details for standardization between TRICS and GDWH
    df['TEMP'] = df['TEMP'] + ' ' + df['COUNTRY']
    # Remove any country duplicates if present in company name string
    df['TEMP'] = df['TEMP'].apply(lambda x: ' '.join(sorted(set(x.split()[::-1]), key=x.split()[::-1].index)[::-1]))
    df['TEMP'] = df['TEMP'].str.replace(' ', '')
    # Perform join
    df = pd.merge(df, df_match, how = 'left', on = 'TEMP')
    # Remove redundant columns
    del df['TEMP']
    # Update ratio and tag for matching records
    df[dseries_ratio] = df.dropna(subset = [dseries_ccif])[dseries_ratio].str.replace('', '0.997')
    df[dseries_tag] = df.dropna(subset = [dseries_ccif])[dseries_tag].str.replace('', 'EXACT NAME') 
    return df

def exact_match_modified_co(df, dseries, dseries_co, dseries_ccif, dseries_ratio, dseries_tag, df_cust):
    # Drop all blanks in df
    df[dseries].replace('', np.nan, inplace = True)
    df.dropna(subset = [dseries], inplace = True)
    df[dseries_ratio] = ''
    df[dseries_tag] = ''
    # Create df_cust copy using df_customers
    df_cust = df_customers.copy()
    # Remove redundant columns
    del df_cust[GDWH_combined_columns[1]], df_cust[GDWH_combined_columns[2]]
    # Reorder/Rename remaining columns
    df_cust = df_cust[[GDWH_combined_columns[3], GDWH_combined_columns[0], GDWH_columns[1], GDWH_columns[2]]]
    df_cust.columns = [dseries, dseries_co, dseries_ccif, GDWH_columns[2]]
    df_match = df_cust.loc[df_cust[dseries].str.replace(' ', '').isin(df[dseries].str.replace(' ', '')), [dseries, dseries_co, dseries_ccif, GDWH_columns[2]]]
    # Create a string with remaining company name and country details for standardization between TRICS and GDWH
    df_match['TEMP'] = df_match[dseries] + ' ' + df_match['COUNTRY']
    # Remove any country duplicates if present in company name string
    df_match['TEMP'] = df_match['TEMP'].apply(lambda x: ' '.join(sorted(set(x.split()[::-1]), key=x.split()[::-1].index)[::-1]))
    df_match['TEMP'] = df_match['TEMP'].str.replace(' ', '')
    del df_match[dseries], df_match['COUNTRY']
    # Create a string with remaining company name and country details for standardization between TRICS and GDWH
    df['TEMP'] = df[dseries] + ' ' + df['COUNTRY']
    # Remove any country duplicates if present in company name string
    df['TEMP'] = df['TEMP'].apply(lambda x: ' '.join(sorted(set(x.split()[::-1]), key=x.split()[::-1].index)[::-1]))
    df['TEMP'] = df['TEMP'].str.replace(' ', '')
    # Perform join
    df = pd.merge(df, df_match, how = 'left', on = 'TEMP')
    # Remove redundant columns
    del df['TEMP']
    # Update ratio and tag for matching records
    df[dseries_ratio] = df.dropna(subset = [dseries_ccif])[dseries_ratio].str.replace('', '0.998')
    df[dseries_tag] = df.dropna(subset = [dseries_ccif])[dseries_tag].str.replace('', 'EXACT NAME') 
    return df

def exact_match_modified_new(df, dseries, dseries_co, dseries_ccif, dseries_ratio, dseries_tag, df_cust):
    # Drop all blanks in df
    df[dseries].replace('', np.nan, inplace = True)
    df.dropna(subset = [dseries], inplace = True)
    df[dseries_ratio] = ''
    df[dseries_tag] = ''
    # Create df_cust copy using df_customers
    df_cust = df_customers.copy()
    # Remove redundant columns
    del df_cust[GDWH_combined_columns[2]], df_cust[GDWH_combined_columns[3]]
    # Reorder/Rename remaining columns
    df_cust = df_cust[[GDWH_combined_columns[1], GDWH_combined_columns[0], GDWH_columns[1], GDWH_columns[2]]]
    df_cust.columns = [dseries, dseries_co, dseries_ccif, GDWH_columns[2]]
    df_match = df_cust.loc[df_cust[dseries].str.replace(' ', '').isin(df[dseries].str.replace(' ', '')), [dseries, dseries_co, dseries_ccif, GDWH_columns[2]]]
    # Create a string with remaining company name and country details for standardization between TRICS and GDWH
    df_match['TEMP'] = df_match[dseries] + ' ' + df_match['COUNTRY']
    # Remove any country duplicates if present in company name string
    df_match['TEMP'] = df_match['TEMP'].apply(lambda x: ' '.join(sorted(set(x.split()[::-1]), key=x.split()[::-1].index)[::-1]))
    df_match['TEMP'] = df_match['TEMP'].str.replace(' ', '')
    del df_match[dseries], df_match['COUNTRY']
    # Create a string with remaining company name and country details for standardization between TRICS and GDWH
    df['TEMP'] = df[dseries] + ' ' + df['COUNTRY']
    # Remove any country duplicates if present in company name string
    df['TEMP'] = df['TEMP'].apply(lambda x: ' '.join(sorted(set(x.split()[::-1]), key=x.split()[::-1].index)[::-1]))
    df['TEMP'] = df['TEMP'].str.replace(' ', '')
    # Perform join
    df = pd.merge(df, df_match, how = 'left', on = 'TEMP')
    # Remove redundant columns
    del df['TEMP']
    # Update ratio and tag for matching records
    df[dseries_ratio] = df.dropna(subset = [dseries_ccif])[dseries_ratio].str.replace('', '0.999')
    df[dseries_tag] = df.dropna(subset = [dseries_ccif])[dseries_tag].str.replace('', 'EXACT NAME') 
    return df

def exact_match_original(df, dseries, dseries_ccif, dseries_ratio, dseries_tag, df_cust):
    # Drop all blanks in df
    df[dseries].replace('', np.nan, inplace = True)
    df.dropna(subset = [dseries], inplace = True)
    df[dseries_ratio] = ''
    df[dseries_tag] = ''
    df['TEMP'] = df[dseries] + ' ' + df['COUNTRY']
    df['TEMP'] = df['TEMP'].apply(lambda x: ' '.join(sorted(set(x.split()[::-1]), key=x.split()[::-1].index)[::-1]))
    df['TEMP'] = df['TEMP'].str.replace(r'[^\w\s]', '')
    df['TEMP'] = df['TEMP'].str.replace(' ', '')  
    # Create df_cust copy using df_customers
    df_cust = df_customers.copy()
    # Remove redundant columns
    del df_cust[GDWH_combined_columns[1]], df_cust[GDWH_combined_columns[2]], df_cust[GDWH_combined_columns[3]]
    # Reorder/Rename remaining columns
    df_cust = df_cust[[GDWH_combined_columns[0], GDWH_columns[1], GDWH_columns[2]]]
    # Create a string with remaining company name and country details for standardization between TRICS and GDWH
    df_cust['TEMP'] = df_cust[GDWH_combined_columns[0]] + ' ' + df_cust[GDWH_columns[2]]
    # Remove any country duplicates if present in company name string
    df_cust['TEMP'] = df_cust['TEMP'].apply(lambda x: ' '.join(sorted(set(x.split()[::-1]), key=x.split()[::-1].index)[::-1]))
    df_cust['TEMP'] = df_cust['TEMP'].str.replace(r'[^\w\s]', '')
    df_cust['TEMP'] = df_cust['TEMP'].str.replace(' ', '')
    del df_cust[GDWH_columns[2]]
    df_cust = df_cust[['TEMP', GDWH_combined_columns[0], GDWH_columns[1]]]
    df_cust.columns = ['TEMP', 'BEST_ORIGIN', dseries_ccif]
    # Perform join
    df = pd.merge(df, df_cust, how = 'left', on = 'TEMP')
    # Update ratio and tag for matching records
    df[dseries_ratio] = df.dropna(subset = [dseries_ccif])[dseries_ratio].str.replace('', '1')
    df[dseries_tag] = df.dropna(subset = [dseries_ccif])[dseries_tag].str.replace('', 'EXACT NAME') 
    # Remove redundant columns
    del df['TEMP']
    return df

def get_closest_match(sample_string, sample_country, current_string, current_country, fun):
    # Initialize variables
    current_score = 0
    # Compute score
    current_score = fun(str(sample_string), str(current_string)) 
    return current_score

############################################### FUZZY MATCH: END #################################################################  


############################################# CLASSIFY RESULTS: START ############################################################# 
    
## Consolidate results from all DataFrames
def consol():
    # Create df_main containing LC details using df_
    df_main = df_.copy()
    # Remove redundant columns in df_main
    del df_main['APPLICANT_ACCOUNT'], df_main['BENEFICIARY_ACCOUNT']
    # Create a combined DataFrame for df_exact_match and df_fuzzy_match 
    df_total_match = df_exact_match.append(df_fuzzy_match, ignore_index = True)
    # Convert back to original countries
    df_total_match['COUNTRY'] = df_total_match['COUNTRY'].str.replace('VIETNAM', 'VIET NAM') 
    df_total_match['COUNTRY'] = df_total_match['COUNTRY'].str.replace('KOREA', 'KOREA, REPUBLIC OF')
    # Change the word (1) 'NETHERLANDS' to 'NETHERLAND' and (2) 'LAO PEOPLES' to "LAO PEOPLE'S" in COUNTRY columns
    df_main[TRICS_columns[0]] = df_main[TRICS_columns[0]].str.replace('NETHERLANDS', 'NETHERLAND')
    df_main[TRICS_columns[0]] = df_main[TRICS_columns[0]].str.replace("LAO PEOPLES", "LAO PEOPLE'S")   
    df_main[TRICS_columns[1]] = df_main[TRICS_columns[1]].str.replace('NETHERLANDS', 'NETHERLAND')
    df_main[TRICS_columns[1]] = df_main[TRICS_columns[1]].str.replace("LAO PEOPLES", "LAO PEOPLE'S")   
    # Rename columns of combined DataFrame and consolidate results under one main DataFrame
    df_total_match.rename(columns = 
                          {'COUNTRY': TRICS_columns[0],
                           'COMBINED_CUST': TRICS_cust_columns[0], 
                           'COMPANY_BEST_MATCH': 'PYTHON_COMPANY_A_BEST_MATCH',
                           'CCIF_BEST_MATCH': 'PYTHON_CCIF_A_BEST_MATCH',
                           'HIGHEST_RATIO': 'PYTHON_A_HIGHEST_RATIO',
                           'UPDATE_TAG': 'PYTHON_A_UPDATE_TAG'}, inplace = True)
    df_main = pd.merge(df_main, df_total_match, how = 'left', on = [TRICS_columns[0], TRICS_cust_columns[0]])
    df_total_match.rename(columns = 
                          {TRICS_columns[0]: TRICS_columns[1],
                           TRICS_cust_columns[0]: TRICS_cust_columns[1], 
                           'PYTHON_COMPANY_A_BEST_MATCH': 'PYTHON_COMPANY_B_BEST_MATCH',
                           'PYTHON_CCIF_A_BEST_MATCH': 'PYTHON_CCIF_B_BEST_MATCH',
                           'PYTHON_A_HIGHEST_RATIO': 'PYTHON_B_HIGHEST_RATIO',
                           'PYTHON_A_UPDATE_TAG': 'PYTHON_B_UPDATE_TAG'}, inplace = True)
    df_main = pd.merge(df_main, df_total_match, how = 'left', on = [TRICS_columns[1], TRICS_cust_columns[1]])
    # Fill NaN values for Highest Ratio and Update Tag columns
    df_main['PYTHON_A_HIGHEST_RATIO'].fillna('0', inplace = True)
    df_main['PYTHON_B_HIGHEST_RATIO'].fillna('0', inplace = True)
    df_main['PYTHON_A_UPDATE_TAG'].fillna('N', inplace = True)
    df_main['PYTHON_B_UPDATE_TAG'].fillna('N', inplace = True)
    # Rearrange all the columns in df_main for readability
    df_main = df_main[[TRICS_columns[0], TRICS_columns[1], TRICS_columns[2], TRICS_columns[3], TRICS_columns[4], TRICS_columns[5], 
                       TRICS_ccif_columns[1], TRICS_nayose_columns[-2],
                       'PYTHON_COMPANY_A_BEST_MATCH', 'PYTHON_CCIF_A_BEST_MATCH', 'PYTHON_A_HIGHEST_RATIO', 'PYTHON_A_UPDATE_TAG',
                       TRICS_columns[6], TRICS_columns[7], TRICS_ccif_columns[-1], TRICS_nayose_columns[-1],
                       'PYTHON_COMPANY_B_BEST_MATCH', 'PYTHON_CCIF_B_BEST_MATCH', 'PYTHON_B_HIGHEST_RATIO', 'PYTHON_B_UPDATE_TAG']]
    # Update starting index from 0 to 1  
    df_main.index = np.arange(1, len(df_main) + 1)
    
    # Present results separately based on REMITTER/APPLICANT and BENEFICIARY
    # Create df_main_1 containing LC Applicant details using df_main
    df_main_1 = df_main.copy()
    # Remove redundant columns
    del df_main_1[TRICS_columns[3]], df_main_1[TRICS_columns[6]], df_main_1[TRICS_columns[7]], df_main_1[TRICS_ccif_columns[-1]], df_main_1[TRICS_nayose_columns[-1]]
    del df_main_1['PYTHON_COMPANY_B_BEST_MATCH'], df_main_1['PYTHON_CCIF_B_BEST_MATCH'], df_main_1['PYTHON_B_HIGHEST_RATIO'], df_main_1['PYTHON_B_UPDATE_TAG']
    # Change UPDATE_TAG if it meets the following criterion: 
    # (1) 'TO INVESTIGATE' if ISSUING BANK is MIZUHO
    # (2) 'FUTURE CUSTOMER TARGETING' if ISSUING BANK is not MIZUHO  
    df_main_1['PYTHON_A_UPDATE_TAG'][(df_main_1[TRICS_columns[2]] == 'MIZUHO') & (df_main_1['PYTHON_A_HIGHEST_RATIO'] == '0') & (df_main_1['PYTHON_A_UPDATE_TAG'] == 'N')] = 'TO INVESTIGATE'
    df_main_1['PYTHON_A_UPDATE_TAG'][(df_main_1[TRICS_columns[2]] != 'MIZUHO') & (df_main_1['PYTHON_A_HIGHEST_RATIO'] == '0') & (df_main_1['PYTHON_A_UPDATE_TAG'] == 'N')] = 'FUTURE CUSTOMER TARGETING'
    # Create an additional flag for UPDATE_FLAG_APPL and update based on different status
    df_main_1['UPDATE_FLAG_APPL'] = ''
    df_main_1['UPDATE_FLAG_APPL'][df_main_1['PYTHON_A_UPDATE_TAG'] == 'EXACT NAME'] = 'Y'
    df_main_1['UPDATE_FLAG_APPL'][df_main_1['PYTHON_A_UPDATE_TAG'] == 'PAST MANUAL CHECKING'] = 'Y'
    df_main_1['UPDATE_FLAG_APPL'][df_main_1['PYTHON_A_UPDATE_TAG'] == 'NO COUNTRY BRANCH'] = 'N'
    df_main_1['UPDATE_FLAG_APPL'][df_main_1['PYTHON_A_UPDATE_TAG'] == 'FUTURE CUSTOMER TARGETING'] = 'N'    
    # Rename/Remove columns and update past manual checking results in df_main_1
    df_temp = df_past_appl.copy()
    df_temp.rename(columns = {'COUNTRY': TRICS_columns[0], 
                              TRICS_combined_columns[0]: TRICS_cust_columns[0], 
                              TRICS_nayose_columns[-2]: 'APPLICANT_NAYOSE_FLAG',
                              'UPDATE_FLAG_APPL': 'UPDATE_FLAG'}, inplace = True)
    del df_temp['APPLICANT_NAYOSE_FLAG'], df_temp['PYTHON_CCIF_A_BEST_MATCH'], df_temp['PYTHON_A_HIGHEST_RATIO'], df_temp['PYTHON_A_UPDATE_TAG']
    df_main_1 = pd.merge(df_main_1, df_temp, how = 'left', on = [TRICS_columns[0], TRICS_cust_columns[0], 'PYTHON_COMPANY_A_BEST_MATCH'])
    df_main_1['PYTHON_A_UPDATE_TAG'][df_main_1['UPDATE_FLAG'] == 'N'] = 'PAST MANUAL CHECKING' 
    df_main_1['UPDATE_FLAG_APPL'][df_main_1['UPDATE_FLAG'] == 'N'] = 'N' 
    del df_main_1['UPDATE_FLAG']
    # Check whether countries/capitals/cities in APPLICANT match with PYTHON_COMPANY_A_BEST_MATCH  
    # If it does not match, update UPDATE_FLAG_APPL with a 'N' flag
    df_std = pd.read_excel('CountriesCapitalsCities.xlsx')
    pattern = (r'\b%s\b' % '|').join(df_std['ENTITIES'])
    df_main_1['CCC1'] = df_main_1[TRICS_cust_columns[0]].str.extract('(' + r'\b%s\b' % pattern + ')', expand = False)
    df_main_1['CCC1'][df_main_1['CCC1'] == 'BRASIL'] = 'BRAZIL'
    df_main_1['CCC2'] = df_main_1['PYTHON_COMPANY_A_BEST_MATCH'].str.extract('(' + r'\b%s\b' % pattern + ')', expand = False)
    df_main_1['CCC2'][df_main_1['CCC2'] == 'BRASIL'] = 'BRAZIL'
    df_main_1['UPDATE_FLAG_REMIT'][df_main_1['UPDATE_FLAG_APPL'] == ''] = np.where((df_main_1['CCC1'][df_main_1['UPDATE_FLAG_APPL'] == ''] != 
                                                                                    df_main_1['CCC2'][df_main_1['UPDATE_FLAG_APPL'] == '']) & 
                                                                                    (df_main_1['CCC1'].notnull()) & (df_main_1['CCC2'].notnull()), 'N', '')
    del df_main_1['CCC1'], df_main_1['CCC2'] 
    # Modify ratio data type and sort them in descending order
    df_main_1['PYTHON_A_HIGHEST_RATIO'] = df_main_1['PYTHON_A_HIGHEST_RATIO'].astype(float)
    df_main_1.sort_values(by = 'PYTHON_A_HIGHEST_RATIO', ascending = False, inplace = True)
    # Drop duplicates
    df_main_1.drop_duplicates(subset = [TRICS_columns[0], TRICS_columns[1], TRICS_columns[4]], inplace = True)
    # Update starting index from 0 to 1  
    df_main_1.index = np.arange(1, len(df_main_1) + 1)
    
    # Create df_main_2 containing LC Beneficiary details using df_main
    df_main_2 = df_main.copy()
    # Remove redundant columns
    del df_main_2[TRICS_columns[2]], df_main_2[TRICS_columns[4]], df_main_2[TRICS_columns[5]], df_main_2[TRICS_ccif_columns[1]], df_main_2[TRICS_nayose_columns[-2]]
    del df_main_2['PYTHON_COMPANY_A_BEST_MATCH'], df_main_2['PYTHON_CCIF_A_BEST_MATCH'], df_main_2['PYTHON_A_HIGHEST_RATIO'], df_main_2['PYTHON_A_UPDATE_TAG']
    # Change UPDATE_TAG if it meets the following criterion: 
    # (1) 'TO INVESTIGATE' if ADVISING BANK is MIZUHO
    # (2) 'FUTURE CUSTOMER TARGETING' if ADVISING BANK is not MIZUHO  
    df_main_2['PYTHON_B_UPDATE_TAG'][(df_main_2[TRICS_columns[3]] == 'MIZUHO') & (df_main_2['PYTHON_B_HIGHEST_RATIO'] == '0') & (df_main_2['PYTHON_B_UPDATE_TAG'] == 'N')] = 'TO INVESTIGATE'
    df_main_2['PYTHON_B_UPDATE_TAG'][(df_main_2[TRICS_columns[3]] != 'MIZUHO') & (df_main_2['PYTHON_B_HIGHEST_RATIO'] == '0') & (df_main_2['PYTHON_B_UPDATE_TAG'] == 'N')] = 'FUTURE CUSTOMER TARGETING'
     # Create an additional flag for UPDATE_FLAG_BENE and update based on different status
    df_main_2['UPDATE_FLAG_BENE'] = ''
    df_main_2['UPDATE_FLAG_BENE'][df_main_2['PYTHON_B_UPDATE_TAG'] == 'EXACT NAME'] = 'Y'
    df_main_2['UPDATE_FLAG_BENE'][df_main_2['PYTHON_B_UPDATE_TAG'] == 'PAST MANUAL CHECKING'] = 'Y'
    df_main_2['UPDATE_FLAG_BENE'][df_main_2['PYTHON_B_UPDATE_TAG'] == 'NO COUNTRY BRANCH'] = 'N'
    df_main_2['UPDATE_FLAG_BENE'][df_main_2['PYTHON_B_UPDATE_TAG'] == 'FUTURE CUSTOMER TARGETING'] = 'N'
    # Rename/Remove columns and update past manual checking results in df_main_2
    df_temp = df_past_bene.copy()
    df_temp.rename(columns = {'COUNTRY': TRICS_columns[1], 
                              TRICS_combined_columns[0]: TRICS_cust_columns[1], 
                              TRICS_nayose_columns[-1]: 'BENEFICIARY_NAYOSE_FLAG',
                              'UPDATE_FLAG_BENE': 'UPDATE_FLAG'}, inplace = True)
    del df_temp['BENEFICIARY_NAYOSE_FLAG'], df_temp['PYTHON_CCIF_B_BEST_MATCH'], df_temp['PYTHON_B_HIGHEST_RATIO'], df_temp['PYTHON_B_UPDATE_TAG']
    df_main_2 = pd.merge(df_main_2, df_temp, how = 'left', on = [TRICS_columns[1], TRICS_cust_columns[1], 'PYTHON_COMPANY_B_BEST_MATCH'])
    df_main_2['PYTHON_B_UPDATE_TAG'][df_main_2['UPDATE_FLAG'] == 'N'] = 'PAST MANUAL CHECKING' 
    df_main_2['UPDATE_FLAG_BENE'][df_main_2['UPDATE_FLAG'] == 'N'] = 'N' 
    del df_main_2['UPDATE_FLAG']
    # Check whether countries/capitals/cities in BENEFICIARY match with PYTHON_COMPANY_B_BEST_MATCH  
    # If it does not match, update UPDATE_FLAG_BENE with a 'N' flag
    df_main_2['CCC1'] = df_main_2[TRICS_cust_columns[1]].str.extract('(' + r'\b%s\b' % pattern + ')', expand = False)
    df_main_2['CCC1'][df_main_2['CCC1'] == 'BRASIL'] = 'BRAZIL'
    df_main_2['CCC2'] = df_main_2['PYTHON_COMPANY_B_BEST_MATCH'].str.extract('(' + r'\b%s\b' % pattern + ')', expand = False)
    df_main_2['CCC2'][df_main_2['CCC2'] == 'BRASIL'] = 'BRAZIL'
    df_main_2['UPDATE_FLAG_BENE'][df_main_2['UPDATE_FLAG_BENE'] == ''] = np.where((df_main_2['CCC1'][df_main_2['UPDATE_FLAG_BENE'] == ''] != 
                                                                                  df_main_2['CCC2'][df_main_2['UPDATE_FLAG_BENE'] == '']) & 
                                                                                  (df_main_2['CCC1'].notnull()) & (df_main_2['CCC2'].notnull()), 'N', '')
    del df_main_2['CCC1'], df_main_2['CCC2']
    # Modify ratio data type and sort them in descending order
    df_main_2['PYTHON_B_HIGHEST_RATIO'] = df_main_2['PYTHON_B_HIGHEST_RATIO'].astype(float)
    df_main_2.sort_values(by = 'PYTHON_B_HIGHEST_RATIO', ascending = False, inplace = True)
    # Drop duplicates
    df_main_2.drop_duplicates(subset = [TRICS_columns[0], TRICS_columns[1], TRICS_columns[6]], inplace = True)
    # Update starting index from 0 to 1  
    df_main_2.index = np.arange(1, len(df_main_2) + 1)
    return df_main, df_main_1, df_main_2

############################################## CLASSIFY RESULTS: END #############################################################      


# Execute conditions
start_time = time.time()
conn, cursor = start_mySQL()
df_1, df_gdwh = return_table_data(TRICS_columns, 'trics_lc_worldwide_201807', 1000, 0, GDWH_columns) # Update filename accordingly
df_2, df_gdwh = return_table_data(TRICS_nayose_columns, 'trics_lc_worldwide_201808', 1000, 0, GDWH_columns) # Update filename accordingly
df_3, df_gdwh = return_table_data(TRICS_nayose_columns, 'trics_lc_worldwide_201809', 1000, 0, GDWH_columns) # Update filename accordingly
df_ = df_1.append([df_2, df_3], ignore_index = True) # Combine all files
df_gdwh, df_iso, df_dw, df_past_appl, df_past_bene = return_other_tables('lc_applicant_past_updates', 'lc_beneficiary_past_updates')
df_gdwh.dropna(subset = ['COUNTRY'], inplace = True)
download_time = time.time() - start_time
print ('The downloading of data took: %s seconds' % str(download_time))
df_ = nayose_ccif_update(df_)
df_combined, df_customers = parse_table_data(TRICS_columns, TRICS_cust_columns, TRICS_combined_columns, GDWH_combined_columns)
parse_time = time.time() - start_time - download_time
print ('The parsing of data took: %s seconds' % str(parse_time))
df_exact_match, df_fuzzy_match = total_match()
match_time = time.time() - start_time - download_time - parse_time
print ('The matching of data took: %s seconds' % str(match_time))
df_main, df_main_1, df_main_2 = consol()
#df_main.to_excel(r'Y:\MRDD_Temp\%s_LC.xlsx' % datetime.datetime.now().strftime('%Y%m%d'))
df_main_1.to_excel(r'Y:\MRDD_Temp\%s_LC_APPLICANT.xlsx' % datetime.datetime.now().strftime('%Y%m%d'))
df_main_2.to_excel(r'Y:\MRDD_Temp\%s_LC_BENEFICIARY.xlsx' % datetime.datetime.now().strftime('%Y%m%d'))