## GTBD project to synchronise data in TRICS and Hyperion ## 

## Import Python libraries
import difflib as dl
import numpy as np
import os
import pandas as pd
import pyodbc

## Initialize variables
filepath = ''
fullFileAdd = ''
access_Col_Name = []
question_Marks = []
quests = ''

## Refresh mySQL table's column names 
def get_mySQL_ColumnNames(filepath):
    
    '''
    Function Parameters:
    filepath: Common path where Microsoft Access files are stored
    (1) Need to enclose filepath in inverted commas
    (2) Include 'r' in front of filepath when using function
    e.g. r'C:\path_to_files'
    '''    
    
    # Establish connection to MySQL database
    conn_mySQL = pyodbc.connect(r'DRIVER={MySQL ODBC 5.3 ANSI Driver};'
                                r'SERVER=203.24.43.91;'
                                r'PORT=3306;'
                                r'DATABASE=gtbd;'
                                r'UID=root;'
                                r'PWD=root')
    cursor_mySQL = conn_mySQL.cursor()

    # If trics_remittance_beneficiary table exists, delete table 
    cursor_mySQL.execute("DROP TABLE IF EXISTS trics_rm_worldwide")            
    
    # Establish connection to one Microsoft Access file in specified filepath
    for each_Access_File in os.listdir(filepath):
        if each_Access_File.endswith('.accdb'):
            fullFileAdd = filepath + '\\' + each_Access_File
            break
    
    if fullFileAdd == '':
        print('There are no Microsoft Access files in specified filepath. Please check!')
    else:
        conn_Access = pyodbc.connect(r'Driver={Microsoft Access Driver (*.mdb, *.accdb)};'
                                    'DBQ=' + fullFileAdd + ';')
        cursor_Access = conn_Access.cursor()
    
        # Store table column names and data types
        res = cursor_Access.execute('SELECT * FROM TRICS_RM_WORLDWIDE')
        for tuple in res.description:               
            if tuple[1] == float:
                access_Col_Name.append(tuple[0] + ' DOUBLE')
                question_Marks.append('?')
            elif tuple[1] == str:
                access_Col_Name.append(tuple[0] + ' VARCHAR(255)')
                question_Marks.append('?')
            elif tuple[1] == int:
                access_Col_Name.append(tuple[0] + ' INT(11)')
                question_Marks.append('?')
            else:
                print('Data type is not created. Please update MRDD!')
            
        # Create mySQL table with column names and data types
        sql = 'CREATE TABLE gtbd.trics_rm_worldwide (' + ', '.join(access_Col_Name) + ');'
        cursor_mySQL.execute(sql)

    conn_Access.close()
    conn_mySQL.close()
    quests = ','.join(question_Marks)
    return quests
    
## Download related information from Microsoft Access files
def get_lists_from_access(filepath):
    
    '''
    Function Parameters:
    filepath: Common path where Microsoft Access files are stored
    (1) Need to enclose filepath in inverted commas
    (2) Include 'r' in front of filepath when using function
    e.g. r'C:\path_to_files'
    '''
    quests = get_mySQL_ColumnNames(filepath)

    # Get all Microsoft Access filenames from specified filepath
    ''' Note: Please store all related Microsoft Access files in the designated filepath '''
    for each_Access_File in os.listdir(filepath):
        if each_Access_File.endswith('.accdb'):
            fullFileAdd = filepath + '\\' + each_Access_File

            # Establish connection to Microsoft Access files in specified filepath
            conn_Access = pyodbc.connect(r'Driver={Microsoft Access Driver (*.mdb, *.accdb)};'
                                         r'DBQ=' + fullFileAdd + ';')
            cursor_Access = conn_Access.cursor()
            cursor_Access.execute('SELECT * FROM TRICS_RM_WORLDWIDE')
            
            # Upload Microsoft Access file content into MySQL database
            count = 0
            row = cursor_Access.fetchone()
            while row is not None:
                row = cursor_Access.fetchone()    
                
                # Establish connection to MySQL database
                conn_mySQL = pyodbc.connect(r'DRIVER={MySQL ODBC 5.3 ANSI Driver};'
                                r'SERVER=203.24.43.91;'
                                r'PORT=3306;'
                                r'DATABASE=gtbd;'
                                r'UID=root;'
                                r'PWD=root')
                cursor_mySQL = conn_mySQL.cursor()
                
                # Update MySQL database
                cursor_mySQL.execute('INSERT INTO trics_remittance_beneficiary VALUES ({0})'.format(quests), row)
                conn_mySQL.commit()     
                count += 1
            
                print('Data for ' + each_Access_File + ' has been uploaded successfully! ' + 
                  'Total records: ' + str(count))
                 
            # Close Microsoft Access file connection
            conn_Access.close()
    
    # Close mySQL connection    
    conn_mySQL.close()


