# Import Python libraries
import numpy as np
import pandas as pd
import quandl
import matplotlib.pyplot as plt
from matplotlib import style
style.use('ggplot')

# Using quandl API to download data
fiddy_states = pd.read_html('https://simple.wikipedia.org/wiki/List_of_U.S._states')

def grab_HPI_data():
    df_main = pd.DataFrame()
    for abbv in fiddy_states[0][1][1:]:
        query = 'FMAC/HPI_' + str(abbv)
        df=quandl.get(query, authtoken = 'Y62q2v-nynJs-95LsYTS')
        
        # First DataFrame
        if df_main.empty:
            df.columns = ['HPI_' + str(abbv)]
            df_main=df
        
        # Subsequent DataFrame
        else:
            df.columns = ['HPI_' + str(abbv)]
            df_main = df_main.join(df)

    df_main.to_csv('HPI_data.csv')

# Resample the monthly data into yearly and plot graphs
df_main = pd.read_csv('HPI_data.csv', index_col = 0, parse_dates = ['Date'])
print(df_main.head())
TX1year = df_main['HPI_TX'].resample('A', how = 'mean')
df_main['HPI_TX'].plot()
TX1year.plot()
plt.legend().remove()
plt.show()

# Calculate correlations
HPI_corr = df_main.corr()

#df1 = pd.DataFrame({'HPI':[80,85,88,85],
#                    'Int_rate':[2, 3, 2, 2],
#                    'US_GDP_Thousands':[50, 55, 65, 55]},
#                   index = [2001, 2002, 2003, 2004])
#
#df2 = pd.DataFrame({'HPI':[80,85,88,85],
#                    'Int_rate':[2, 3, 2, 2],
#                    'US_GDP_Thousands':[50, 55, 65, 55]},
#                   index = [2005, 2006, 2007, 2008])
#
#df3 = pd.DataFrame({'HPI':[80,85,88,85],
#                    'Unemployment':[7, 8, 9, 6],
#                    'Low_tier_HPI':[50, 52, 50, 53]},
#                   index = [2001, 2002, 2003, 2004])

## Set common index for df1 and df3
#df1.set_index('HPI', inplace=True)
#df3.set_index('HPI', inplace=True)
#df1.join(df3) # join method uses the index field to join
#df1.merge(df3) # merge method uses specified column field to join

## Import csv and set first column as index, second column as Austin_HPI
#df = pd.read_csv('ZILLOW-Z77006_MRP2B.csv', index_col = 0)
#df.columns = ['Austin_HPI']


## Reference Visitors and/or Bounce_Rate columns
#print(df[['Visitors','Bounce_Rate']])
#http://www.cs.toronto.edu/~rgrosse/courses/csc321_2018/
