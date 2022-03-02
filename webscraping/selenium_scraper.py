# -*- coding: utf-8 -*-
"""
Created on Tue Jul 13 10:55:31 2021

@author: joe.cavarretta
"""
import time
from bs4 import BeautifulSoup as soup
from selenium import webdriver
import os
import pandas as pd
import numpy as np
import pyodbc

cwd = os.getcwd()

chromedriver_path = cwd + '/chromedriver.exe'

driver = webdriver.Chrome(chromedriver_path)
url = ""
driver.get(url)
time.sleep(3) #if you want to wait 3 seconds for the page to load
page_source = driver.page_source
page_soup = soup(page_source, 'lxml')

driver.close()

res = page_soup.find_all('div', {'class': 'location-item'})

lst = []
for r in res:
    if 'USA' in r.text or 'Canada' in r.text:
        lst.append(r.text.split('  '))

df = pd.DataFrame(lst)

## Strip leading spaces
cols = df.select_dtypes(['object']).columns
df[cols] = df[cols].apply(lambda x: x.str.lstrip())
df[cols] = df[cols].apply(lambda x: x.str.rstrip())

## Parse column 3 to country
df['country'] = np.where(df[3].str.contains('USA'), 'USA',
                    np.where(df[4].str.contains('USA'), 'USA',
                        np.where(df[3].str.contains('Canada'), 'Canada',
                            np.where(df[4].str.contains('Canada'), 'Canada', np.nan))))

## Fix addresses that went to wrong column
df[2] = np.where(df[2] == '', df[3], df[2])

## Drop column 3 from df
df = df.drop(columns=3)

## create column for postal code based on last digits of column 3 and country
df['postal code'] = np.where(df['country'].eq('USA'), df[2].str[-5:], df[2].str[-7:])

## create column for state based on country + postal code digit count
df['state'] = np.where(df['country'].eq('USA'), df[2].str[-8:-6], df[2].str[-10:-8])

## create column for city based on country + postal code digit count
df['city'] = np.where(df['country'].eq('USA'), df[2].str[:-9], df[2].str[:-11])

## reorder columns
df = df[[0, 1, 'city', 'state', 'postal code', 'country', 4]]

## rename columns
df.columns = ['name', 'street_address', 'city', 'state', 'postal_code', 'country', '100g_enablement']

## some addresses have the city at the end, run code below to fix
df["needs_modified"] = [x.endswith(y) for x, y in df[["street_address","city"]].values]
df["street_address"] = [x[:-len(y)] if x.endswith(y) else x for x, y in df[["street_address","city"]].values]

## restructure address to match Z conventions
repl_dict = {
    r'\bStreet\b': 'St',
    r'\bAvenue\b': 'Ave',
    r'\bParkway\b': 'Pkwy',
    r'\bFreeway\b': 'Fwy',
    r'\bCircle\b': 'Cir',
    r'\bBoulevard\b': 'Blvd',
    r'\bCourt\b': 'Ct',
    r'\bPlace\b': 'Pl',
    r'\bPlaza\b': 'Plz',
    r'\bLane\b': 'Ln',
    r'\bRoad\b': 'Rd',
    r'\bDrive\b': 'Dr',
    r'\bNorth\b': 'N',
    r'\bSouth\b': 'S',
    r'\bEast\b': 'E',
    r'\bWest\b': 'W',
    r'\bNortheast\b': 'NE',
    r'\bSoutheast\b': 'SE',
    r'\bNorthwest\b': 'NW',
    r'\bSouthwest\b': 'SW'
        }

df['street_address'] = df['street_address'].replace(repl_dict, regex = True)

## save m buildings to csv
df.to_csv('file.csv', index = False)

print('Saved to CSV.')

############### CONNECT TO DB ###############                                   # Connect to VPN
conn = pyodbc.connect('DRIVER={SQL Server};'
                      'SERVER=;'
                      'DATABASE=;'
                      'Trusted_Connection=yes;')

print(conn)

############### DEFINE READSQL CODE ###############
def readSQL(file_path):
    fd = open(file_path)
    sql = fd.read()
    fd.close()
    return pd.read_sql(sql,conn)

############## RUN SQL QUERY ###############
df_z = readSQL('all_buildings.sql')

# create new df with inner merge of buildings and see how many match

merged_df = df_z.merge(df[['street_address', 'postal_code']],
                          how = 'inner',
                          left_on=('street_address', 'postal_code'),
                          right_on=('street_address', 'postal_code'))

merged_df = merged_df.drop_duplicates(subset = 'Id')


print(f'Number of Z Buildings = {df_z.shape[0]}\n')
print(f'Number of M Buildings = {df.shape[0]}\n')
print(f'Number of Matches = {merged_df.shape[0]}\n')

merged_df.to_csv('m_z_match.csv', index = False)

print('Matched Buildings Saved')