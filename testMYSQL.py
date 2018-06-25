import pyodbc
import time 

conn = pyodbc.connect(
    r'DRIVER={MySQL ODBC 5.3 Unicode Driver};'
    r'SERVER=localhost;'
    r'PORT=3306;'
    r'DATABASE=sys;'
    r'UID=root;'
    r'PWD=myowd'
    )

cursor = conn.cursor()

username = 'Python'
tweet = 'man im so cool'

# the last variables are the actual inputs
# can consider extracting first and upload into database
cursor.execute("INSERT INTO taula(time, username, tweet) VALUES (%s,%s,%s)", (time.time(),username,tweet))
conn.commit()

cursor.execute("SELECT * from taula")
rows = cursor.fetchall()

