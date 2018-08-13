## GTBD project to synchronise data in TRICS and GDWH - Focus on Singapore ## 

## Import Python libraries
from Levenshtein import *
import numpy as np
import pandas as pd
import pandas.io.sql as psql
import pyodbc
import time


## Initialize variables
rm_dict = {'COMPANY': [], 'COMPANY_BEST_MATCH':[], 'CCIF_BEST_MATCH':[], 'HIGHEST_RATIO': []}
TRICS_combined_columns = ['COMBINED_CUST', 'COMBINED_CUST_NEW', 'COMBINED_CUST_CCC', 'COMBINED_CUST_CO']
GDWH_columns = ['CUST_NAME', 'C_CIF_NO']
GDWH_combined_columns = ['CUST_NAME', 'CUST_NAME_NEW', 'CUST_NAME_CCC', 'CUST_NAME_CO']


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


## Run query to return every relevant table in mySQL server
def return_DB(table):   
    # Execute SQL to list tables
    cursor.execute('SHOW TABLES;')
    response = cursor.fetchall()
    mySQLtables = []
    for row in response:
        if table in row[0]:
            mySQLtables.append(row[0]) 
    return mySQLtables


## Run query to return selected trics table and GDWH customer list from mySQL server
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
    
    # Convert GDWH_columns from list to string
    GDWH_column_list = ','.join(map(str, GDWH_columns))
    # Import GDWH customer list from mySQL server
    df_gdwh = pd.read_sql('SELECT %s FROM t_gtbd_custlist WHERE %s IS NOT NULL;' % (GDWH_column_list, GDWH_columns[0]), con = conn)
    return df_, df_gdwh


############################################### PARSE DATA: START ###############################################################

## Parse data in standardized format
def parse_table_data(TRICS_columns, TRICS_cust_columns, TRICS_combined_columns, GDWH_combined_columns): 
    # Create TRICS customer DataFrames: df1 (RM/Applicant) and df2 (Beneficiary) using df_   
    df1 = df_.copy()
    df1.columns = TRICS_columns
    df1.dropna(subset = [TRICS_cust_columns[0]], inplace = True)
    df1 = df1[TRICS_cust_columns[0]][df1[TRICS_cust_columns[0]] != '']
    df2 = df_.copy()
    df2.columns = TRICS_columns
    df2.dropna(subset = [TRICS_cust_columns[1]], inplace = True)
    df2 = df2[TRICS_cust_columns[1]][df2[TRICS_cust_columns[1]] != '']
    # Combine both customer DataFrames using df1 and df2   
    df_combined = pd.DataFrame(pd.concat([df1, df2], ignore_index = True), columns = [TRICS_combined_columns[0]])
    # Drop duplicates in combined column
    df_combined.drop_duplicates(TRICS_combined_columns[0], inplace = True)
    # Sort remaining companies in ascending order
    df_combined.sort_values(by = TRICS_combined_columns[0], inplace = True)
    # Clean/Standardize customer names
    df_combined = clean_data(df_combined, TRICS_combined_columns[0], TRICS_combined_columns[1])
   
    # Create GDWH customer DataFrame: df_customers using df_gdwh
    df_customers = df_gdwh.copy()
    # Drop all duplicates fromm GDWH customer names
    df_customers.dropna(inplace = True)    
    df_customers.drop_duplicates(GDWH_combined_columns[0], inplace = True)
    # Clean/Standardize customer names
    df_customers = clean_data(df_customers, GDWH_combined_columns[0], GDWH_combined_columns[1])
    
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
 
    # Create a new column to store RM data
    df_combined[TRICS_combined_columns[2]] = df_combined[TRICS_combined_columns[1]]
    df_customers[GDWH_combined_columns[2]] = df_customers[GDWH_combined_columns[1]]
    df_combined[TRICS_combined_columns[3]] = df_combined[TRICS_combined_columns[1]]
    df_customers[GDWH_combined_columns[3]] = df_customers[GDWH_combined_columns[1]]
    
    # Standardize remaining companies' abbreviation and country/capital/city in all 3 DataFrames 
    df_combined = parse_ccc_abb('CompanyAbbreviations.xlsx', 'CountriesCapitalsCities.xlsx', df_combined, TRICS_combined_columns[2], TRICS_combined_columns[3])
    df_customers = parse_ccc_abb('CompanyAbbreviations.xlsx', 'CountriesCapitalsCities.xlsx', df_customers, GDWH_combined_columns[2], GDWH_combined_columns[3])
    return df_combined, df_customers

def clean_data(df, dseries_old, dseries):
    # Drop all non-alphanumeric characters from selected DataFrame customer names
    df[dseries] = df[dseries_old].str.replace(r'[^\w\s]', ' ')
    df[dseries] = df[dseries].str.replace(r'\b%s\b' % 'AND', '')  
    # Drop all leading (supsicious) numbers from selected DataFrame customer names
    df[dseries] = df[dseries][df[dseries].str[0:5].replace(' ', '').str.isdigit()].str.replace(r'^\d+', '')
    df[dseries].fillna(df[dseries_old][df[dseries].isnull()], inplace = True)
    df[dseries] = df[dseries].str.replace(r'[^\w\s]', ' ')
    df[dseries] = df[dseries].str.replace(r'\b%s\b' % 'AND', '')  
    df[dseries] = df[dseries].str.replace(r'^\d+\s\d+', '')
    # Drop all potential addresses from selected DataFrame customer names
    df[dseries] = df[dseries].str.split(r'\b%s\b' % 'PLS').str[0]
    df[dseries] = df[dseries].str.split(r'\b%s\b' % 'BLDG').str[0]
    df[dseries] = df[dseries].str.split(r'\b%s\b' % 'NO').str[0]
    df[dseries] = df[dseries].str.split(r'\b%s\b' % 'SEE').str[0]
    df[dseries] = df[dseries].str.split(r'\s\d+').str[0]
    df[dseries] = df[dseries].str.split(r'\D\d+').str[0]
    # Drop empty cells and strip redundant spaces
    df = df[df[dseries] != '']
    df[dseries] = df[dseries].str.replace('[\s]{2,}', ' ')
    df[dseries] = df[dseries].str.strip()      
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
    df[dseries] = df[dseries].str.replace('[\s]{2,}', ' ')
    df[dseries] = df[dseries].str.strip()
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
    df[dseries] = df[dseries].str.replace('[\s]{2,}', ' ')
    df[dseries] = df[dseries].str.strip()
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
    df['SHORT'] = df[dseries2].str.extract('(' + r'\b%s\b' % pattern_std + ')', expand = False)
    df['TEMP'] = df['SHORT']
    df['TEMP'].fillna(df[dseries2][df['SHORT'].isnull()], inplace = True)
    df = pd.merge(df, df_std, how = 'left', on = 'SHORT')
    # Replace abbreviated DataFrame rows with full name in 'LONG' column
    df[dseries2] = df.dropna(subset = ['SHORT']).apply(lambda x: x[dseries2].replace(x['SHORT'],x['LONG']), axis=1)
    df[dseries2].fillna(df['TEMP'][df[dseries2].isnull()], inplace = True)
    # Drop empty cells and strip redundant spaces
    df = df[df[dseries2] != '']
    df[dseries2] = df[dseries2].str.replace('[\s]{2,}', ' ')
    df[dseries2] = df[dseries2].str.strip()
    # Remove redundant columns
    del df['SHORT'], df['LONG'], df['TEMP']
    
    # List DataFrame rows with country/capital/city abbreviations
    df[dseries] = df[dseries2]
    df['CCC'] = df[dseries].str.extract('(' + r'\b%s\b' % pattern_ccc + ')', expand = False)
    df['TEMP_CCC'] = df['CCC']
    df['TEMP_CCC_NO1'] = df['CCC']
    df['TEMP_CCC_NO2'] = df['CCC']
    df['TEMP_CCC'].fillna(df[dseries][df['CCC'].isnull()], inplace = True)
    df['TEMP_CCC_NO1'] = df.dropna(subset = ['CCC'])[dseries].str.split(r'\s').str[0]
    df['TEMP_CCC_NO2'] = df.dropna(subset = ['CCC'])[dseries].str.split(r'\s').str[1]
    # List DataFrame rows that do not begin with country/capital/city (i.e. first 2 words must not contain country/capital/city)
    df['TEMP_CCC'] = df['TEMP_CCC'][((df['TEMP_CCC_NO1'] != df['TEMP_CCC']) & (df['TEMP_CCC_NO2'] != df['TEMP_CCC'])) & 
                    (df['TEMP_CCC_NO1'] + df['TEMP_CCC_NO2'] != df['TEMP_CCC'].str.replace(' ', ''))]
    # Remove any text after country/capital/city abbreviations for DataFrame rows that do not begin with country/capital/city
    df['TEMP_CCC'] = df.dropna(subset = ['TEMP_CCC'])[dseries].str.split('(' + r'\b%s\b' % pattern_ccc + ')').str[0] + df.dropna(subset = ['TEMP_CCC'])['CCC'] 
    df['TEMP_CCC'].fillna(df[dseries][df['TEMP_CCC'].isnull()], inplace = True)
    df[dseries] = df['TEMP_CCC']
    # Drop empty cells and strip redundant spaces
    df = df[df[dseries] != '']
    df[dseries] = df[dseries].str.replace('[\s]{2,}', ' ')
    df[dseries] = df[dseries].str.strip()
    # Remove redundant columns and free up memory
    del df['CCC'], df['TEMP_CCC'], df['TEMP_CCC_NO1'], df['TEMP_CCC_NO2']
    return df

############################################### PARSE DATA: END #################################################################  
    

############################################### FUZZY MATCH: START ###############################################################    

## Fuzzy matching
def fuzzy_match():        
    # Perform exact matching between modified and original columns in both TRICS and GDWH
    df_exact_match = df_combined.copy()
    df_cust_simple = pd.DataFrame({})
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
    
    # Remove redundant columns
    del df_exact_match[TRICS_combined_columns[1]], df_exact_match[TRICS_combined_columns[2]]
    del df_exact_match['BEST_CCC'], df_exact_match['BEST_CO'], df_exact_match['BEST_NEW'], df_exact_match['BEST_ORIGIN']
    del df_exact_match['BEST_CCC_CCIF'], df_exact_match['BEST_CO_CCIF'], df_exact_match['BEST_NEW_CCIF'], df_exact_match['BEST_ORIGIN_CCIF']
    del df_exact_match['BEST_CCC_RATIO'], df_exact_match['BEST_CO_RATIO'], df_exact_match['BEST_NEW_RATIO'], df_exact_match['BEST_ORIGIN_RATIO']
    del df_exact_match['BEST_CCC_TAG'], df_exact_match['BEST_CO_TAG'], df_exact_match['BEST_NEW_TAG'], df_exact_match['BEST_ORIGIN_TAG']
    print('Exact matching completed!')
    
    # Query out the list of NaN cases in df_exact_match for complex fuzzy matching
    df_fuzzy_match = df_exact_match[df_exact_match['HIGHEST_RATIO'].isnull()]  
    # Drop all duplicates in df_fuzzy_match
    df_fuzzy_match.drop_duplicates(TRICS_combined_columns[0], inplace = True)
    # Remove remaining redundant columns from df_exact_match
    del df_exact_match[TRICS_combined_columns[3]]

    # Initialize DataFrame for complex fuzzy matching
    count = 0
    df_match = pd.DataFrame({'TRICS_COMPANY_CO': [], 'GDWH_COMPANY_CO': [], 'GDWH_COMPANY': [], 'GDWH_CCIF': [], 'RATIO': []})
    df_match['GDWH_COMPANY_CO'] = df_customers[GDWH_combined_columns[3]]
    df_match['GDWH_COMPANY'] = df_customers[GDWH_combined_columns[0]]
    df_match['GDWH_CCIF'] = df_customers[GDWH_columns[1]]
    # Start complex fuzzy matching
    for row in df_fuzzy_match.itertuples():
        df_match['TRICS_COMPANY_CO'] = np.tile(row[2], (len(df_customers),1)) 
        df_match['RATIO'] = df_match.apply(lambda x: get_closest_match(x['TRICS_COMPANY_CO'], x['GDWH_COMPANY_CO'], ratio), axis = 1)
        if max(df_match['RATIO']) == 0:
            df_fuzzy_match['COMPANY_BEST_MATCH'][df_fuzzy_match[TRICS_combined_columns[3]] == row[2]] = ''
            df_fuzzy_match['CCIF_BEST_MATCH'][df_fuzzy_match[TRICS_combined_columns[3]] == row[2]] = ''
            df_fuzzy_match['HIGHEST_RATIO'][df_fuzzy_match[TRICS_combined_columns[3]] == row[2]] = 0
            df_fuzzy_match['UPDATE_TAG'][df_fuzzy_match[TRICS_combined_columns[3]] == row[2]] = 'N'
        else:
            df_fuzzy_match['COMPANY_BEST_MATCH'][df_fuzzy_match[TRICS_combined_columns[3]] == row[2]] = df_match['GDWH_COMPANY'][df_match['RATIO'] == max(df_match['RATIO'])].iloc[0]
            df_fuzzy_match['CCIF_BEST_MATCH'][df_fuzzy_match[TRICS_combined_columns[3]] == row[2]] = df_match['GDWH_CCIF'][df_match['RATIO'] == max(df_match['RATIO'])].iloc[0]
            df_fuzzy_match['HIGHEST_RATIO'][df_fuzzy_match[TRICS_combined_columns[3]] == row[2]] = max(df_match['RATIO'])
            df_fuzzy_match['UPDATE_TAG'][df_fuzzy_match[TRICS_combined_columns[3]] == row[2]] = 'Y'
        # Track progress of fuzzy matching
        count += 1
        if count % 1000:
            print('Progress: %d out of %d' % (count % 1000, len(df_fuzzy_match)))
    print('Complex fuzzy matching completed!')   
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
    df_cust = df_cust[[GDWH_combined_columns[2], GDWH_combined_columns[0], 'C_CIF_NO']]
    df_cust.columns = [dseries, dseries_co, dseries_ccif]
    # Perform join
    df_match = df_cust.loc[df_cust[dseries].str.replace(' ', '').isin(df[dseries].str.replace(' ', '')), [dseries, dseries_co, dseries_ccif]]
    df = pd.merge(df, df_match, how = 'left', on = dseries)
    # Update ratio and tag for matching records
    df[dseries_ratio] = df.dropna(subset = [dseries_ccif])[dseries_ratio].str.replace('', '0.997')
    df[dseries_tag] = df.dropna(subset = [dseries_ccif])[dseries_tag].str.replace('', 'Y') 
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
    df_cust = df_cust[[GDWH_combined_columns[3], GDWH_combined_columns[0], 'C_CIF_NO']]
    df_cust.columns = [dseries, dseries_co, dseries_ccif]
    # Perform join
    df_match = df_cust.loc[df_cust[dseries].str.replace(' ', '').isin(df[dseries].str.replace(' ', '')), [dseries, dseries_co, dseries_ccif]]
    df = pd.merge(df, df_match, how = 'left', on = dseries)
    # Update ratio and tag for matching records
    df[dseries_ratio] = df.dropna(subset = [dseries_ccif])[dseries_ratio].str.replace('', '0.998')
    df[dseries_tag] = df.dropna(subset = [dseries_ccif])[dseries_tag].str.replace('', 'Y') 
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
    df_cust = df_cust[[GDWH_combined_columns[1], GDWH_combined_columns[0], 'C_CIF_NO']]
    df_cust.columns = [dseries, dseries_co, dseries_ccif]
    # Perform join
    df_match = df_cust.loc[df_cust[dseries].str.replace(' ', '').isin(df[dseries].str.replace(' ', '')), [dseries, dseries_co, dseries_ccif]]
    df = pd.merge(df, df_match, how = 'left', on = dseries)
    # Update ratio and tag for matching records
    df[dseries_ratio] = df.dropna(subset = [dseries_ccif])[dseries_ratio].str.replace('', '0.999')
    df[dseries_tag] = df.dropna(subset = [dseries_ccif])[dseries_tag].str.replace('', 'Y') 
    return df

def exact_match_original(df, dseries, dseries_ccif, dseries_ratio, dseries_tag, df_cust):
    # Drop all blanks in df
    df[dseries].replace('', np.nan, inplace = True)
    df.dropna(subset = [dseries], inplace = True)
    df[dseries_ratio] = ''
    df[dseries_tag] = ''
    df['TEMP'] = df[dseries].str.replace(' ', '')
    # Create df_cust copy using df_customers
    df_cust = df_customers.copy()
    # Remove redundant columns
    del df_cust[GDWH_combined_columns[1]], df_cust[GDWH_combined_columns[2]], df_cust[GDWH_combined_columns[3]]
    # Reorder/Rename remaining columns
    df_cust['TEMP'] = df_cust[GDWH_combined_columns[0]].str.replace(' ', '')
    df_cust = df_cust[['TEMP', GDWH_combined_columns[0], 'C_CIF_NO']]
    df_cust.columns = ['TEMP', 'BEST_ORIGIN', dseries_ccif]
    # Perform join
    df = pd.merge(df, df_cust, how = 'left', on = 'TEMP')
    # Update ratio and tag for matching records
    df[dseries_ratio] = df.dropna(subset = [dseries_ccif])[dseries_ratio].str.replace('', '1')
    df[dseries_tag] = df.dropna(subset = [dseries_ccif])[dseries_tag].str.replace('', 'Y') 
    # Remove redundant columns
    del df['TEMP']
    return df

def get_closest_match(sample_string, current_string, fun):
    # Initialize variables
    current_score = 0
    # Compare sample_string with current_string in actual customer list
    if (sample_string.split(' ')[0:2] == current_string.split(' ')[0:2]) and \
        ([ccc for ccc in df_ccc['ENTITIES'] if ccc in sample_string] \
         == [ccc for ccc in df_ccc['ENTITIES'] if ccc in current_string]) and \
         len([ccc for ccc in df_ccc['ENTITIES'] if ccc in sample_string]) >= 1 and \
         len([ccc for ccc in df_ccc['ENTITIES'] if ccc in current_string]) >= 1:
        current_score = fun(sample_string, current_string)
                    
    elif (sample_string.split()[0:2] == current_string.split()[0:2]) and \
        len([ccc for ccc in df_ccc['ENTITIES'] if ccc in sample_string]) == 0 and \
        len([ccc for ccc in df_ccc['ENTITIES'] if ccc in current_string]) == 0:
        current_score = fun(sample_string, current_string)   
    return current_score

############################################### FUZZY MATCH: END #################################################################  


# Consolidate results from all DataFrames
def consol():
    # Create df_main containing RM details using df_
    df_main = df_.copy()
    # Create a combined DataFrame for df_exact_match and df_fuzzy_match 
    del df_fuzzy_match['COMBINED_CUST_CO']
    df_total_match = df_exact_match.append(df_fuzzy_match, ignore_index = True)
    # Rename columns of combined DataFrame and consolidate results under one main DataFrame
    df_total_match.rename(columns = 
                          {'COMBINED_CUST': TRICS_cust_columns[0], 
                           'COMPANY_BEST_MATCH': 'PYTHON_COMPANY_A_BEST_MATCH',
                           'CCIF_BEST_MATCH': 'PYTHON_CCIF_A_BEST_MATCH',
                           'HIGHEST_RATIO': 'PYTHON_A_HIGHEST_RATIO',
                           'UPDATE_TAG': 'PYTHON_A_UPDATE_TAG'}, inplace = True)
    df_main = pd.merge(df_main, df_total_match, how = 'left', on = TRICS_cust_columns[0])
    df_total_match.rename(columns = 
                          {TRICS_cust_columns[0]: TRICS_cust_columns[1], 
                           'PYTHON_COMPANY_A_BEST_MATCH': 'PYTHON_COMPANY_B_BEST_MATCH',
                           'PYTHON_CCIF_A_BEST_MATCH': 'PYTHON_CCIF_B_BEST_MATCH',
                           'PYTHON_A_HIGHEST_RATIO': 'PYTHON_B_HIGHEST_RATIO',
                           'PYTHON_A_UPDATE_TAG': 'PYTHON_B_UPDATE_TAG'}, inplace = True)
    df_main = pd.merge(df_main, df_total_match, how = 'left', on = TRICS_cust_columns[1])
    return df_main
    

## Execute conditions
start_time = time.time()
conn, cursor = start_mySQL()
TRICS_columns = ['COUNTRY_FROM_2', 'REMITTING_BANK_JP_BANK_GRP_2', 'BENEFICIARY_BANK_JP_BANK_GRP_2', 
                'REMITTER_ENGLISH', 'REMITTER_C_CIF_2', 'BENEFICIARY_ENGLISH', 'BENEFICIARY_C_CIF_2']
TRICS_cust_columns = ['REMITTER_ENGLISH', 'BENEFICIARY_ENGLISH']
df_, df_gdwh = return_table_data(TRICS_columns, 'trics_rm_worldwide_updated', 1000, 0, GDWH_columns)
download_time = time.time() - start_time
print ('The downloading of data took: %s seconds' % str(download_time))
df_combined, df_customers = parse_table_data(TRICS_columns, TRICS_cust_columns, TRICS_combined_columns, GDWH_combined_columns)
parse_time = time.time() - start_time - download_time
print ('The parsing of data took: %s seconds' % str(parse_time))
df_ccc = pd.read_excel('CountriesCapitalsCities.xlsx')
df_exact_match, df_fuzzy_match = fuzzy_match()
match_time = time.time() - start_time - download_time - parse_time
print ('The matching of data took: %s seconds' % str(match_time))
df_main = consol()
df_main.to_excel(r'Y:\MRDD_Temp\20180803_RM.xlsx')
