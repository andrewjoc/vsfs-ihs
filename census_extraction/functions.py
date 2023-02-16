import pandas as pd
import geopandas as gpd
import numpy as np
import re
    

census_subnational = {'angola-adm2': 'https://www2.census.gov/programs-surveys/international-programs/tables/time-series/pepfar/angola.xlsx',
'bangladesh-adm3': 'https://www2.census.gov/programs-surveys/international-programs/tables/time-series/pepfar/bangladesh.xlsx',
 'benin-adm2':'https://www2.census.gov/programs-surveys/international-programs/tables/time-series/pepfar/benin.xlsx',
 'botswana-adm3': 'https://www2.census.gov/programs-surveys/international-programs/tables/time-series/pepfar/botswana.xlsx',
 'brazil-adm2': 'https://www2.census.gov/programs-surveys/international-programs/tables/time-series/pepfar/brazil.xlsx',
 'burma-adm3': 'https://www2.census.gov/programs-surveys/international-programs/tables/time-series/pepfar/burma.xlsx',
 'burundi-adm2':'https://www2.census.gov/programs-surveys/international-programs/tables/time-series/pepfar/burundi.xlsx',
 'cambodia-adm2':'https://www2.census.gov/programs-surveys/international-programs/tables/time-series/pepfar/cambodia.xlsx',
 'dominicanrepublic-adm3':'https://www2.census.gov/programs-surveys/international-programs/tables/time-series/pepfar/dominican-republic.xlsx',
 'ethiopia-adm3':'https://www2.census.gov/programs-surveys/international-programs/tables/time-series/pepfar/ethiopia.xlsx',
 'ghana-adm2':'https://www2.census.gov/programs-surveys/international-programs/tables/time-series/pepfar/ghana.xlsx',
 'guatemala-adm2':'https://www2.census.gov/programs-surveys/international-programs/tables/time-series/pepfar/guatemala.xlsx',
 'guyana-adm2':'https://www2.census.gov/programs-surveys/international-programs/tables/time-series/pepfar/guyana.xlsx',
 'haiti-adm3':'https://www2.census.gov/programs-surveys/international-programs/tables/time-series/pepfar/haiti.xlsx',
 'honduras-adm2':'https://www2.census.gov/programs-surveys/international-programs/tables/time-series/pepfar/honduras.xlsx',
 'india-adm2':'https://www2.census.gov/programs-surveys/international-programs/tables/time-series/pepfar/india.xlsx',
 'indonesia-adm2':'https://www2.census.gov/programs-surveys/international-programs/tables/time-series/pepfar/indonesia.xlsx',
 'kenya-adm2':'https://www2.census.gov/programs-surveys/international-programs/tables/time-series/pepfar/kenya.xlsx',
 'laos-adm2':'https://www2.census.gov/programs-surveys/international-programs/tables/time-series/pepfar/laos.xlsx',
 'lesotho-adm1':'https://www2.census.gov/programs-surveys/international-programs/tables/time-series/pepfar/lesotho.xlsx',
 'malawi-adm2':'https://www2.census.gov/programs-surveys/international-programs/tables/time-series/pepfar/malawi.xlsx',
 'mozambique-adm3':'https://www2.census.gov/programs-surveys/international-programs/tables/time-series/pepfar/mozambique.xlsx',
 'namibia-adm2':'https://www2.census.gov/programs-surveys/international-programs/tables/time-series/pepfar/namibia.xlsx',
 'nepal-adm2':'https://www2.census.gov/programs-surveys/international-programs/tables/time-series/pepfar/nepal.xlsx',
 'nigeria-adm2':'https://www2.census.gov/programs-surveys/international-programs/tables/time-series/pepfar/nigeria.xlsx',
 'pakistan-adm4':'https://www2.census.gov/programs-surveys/international-programs/tables/time-series/pepfar/pakistan.xlsx',
 'panama-adm3':'https://www2.census.gov/programs-surveys/international-programs/tables/time-series/pepfar/panama.xlsx',
 'papuanewguinea-adm3':'https://www2.census.gov/programs-surveys/international-programs/tables/time-series/pepfar/papua-new-guinea.xlsx',
 'philippines-adm3':'https://www2.census.gov/programs-surveys/international-programs/tables/time-series/pepfar/philippines.xlsx',
 'russia-adm1':'https://www2.census.gov/programs-surveys/international-programs/tables/time-series/pepfar/russia.xlsx',
 'rwanda-adm3':'https://www2.census.gov/programs-surveys/international-programs/tables/time-series/pepfar/rwanda.xlsx',
 'senegal-adm1':'https://www2.census.gov/programs-surveys/international-programs/tables/time-series/pepfar/senegal.xlsx',
 'sierraleone-adm2':'https://www2.census.gov/programs-surveys/international-programs/tables/time-series/pepfar/sierra-leone.xlsx',
 'southafrica-adm3':'https://www2.census.gov/programs-surveys/international-programs/tables/time-series/pepfar/south-africa.xlsx',
 'tanzania-adm2':'https://www2.census.gov/programs-surveys/international-programs/tables/time-series/pepfar/tanzania.xlsx',
 'thailand-adm2':'https://www2.census.gov/programs-surveys/international-programs/tables/time-series/pepfar/thailand.xlsx',
 'uganda-adm1':'https://www2.census.gov/programs-surveys/international-programs/tables/time-series/pepfar/uganda.xlsx',
 'vietnam-adm1':'https://www2.census.gov/programs-surveys/international-programs/tables/time-series/pepfar/vietnam.xlsx',
 'zambia-adm4':'https://www2.census.gov/programs-surveys/international-programs/tables/time-series/pepfar/zambia.xlsx',
 'zimbabwe-adm2':'https://www2.census.gov/programs-surveys/international-programs/tables/time-series/pepfar/zimbabwe.xlsx',
 'kenya-adm1':'https://www2.census.gov/programs-surveys/international-programs/tables/time-series/pepfar/kenya.xlsx',
 'rwanda-adm1':'https://www2.census.gov/programs-surveys/international-programs/tables/time-series/pepfar/zimbabwe.xlsx',
 'zambia-adm1':'https://www2.census.gov/programs-surveys/international-programs/tables/time-series/pepfar/zambia.xlsx'
}


def canonicalize_text(text):
    '''
    description: text cleaning function to be applied on a pandas series
    '''
    text = text.lower()
    text = re.sub('\[.*?\]', '', text)
    text = re.sub('<.*?>+', '', text)
    text = re.sub('\.?', '', text)
    return text


def view_filenames():
    names = [i for i, j in census_subnational.items()]
    return sorted(names)


def extract_census_data(country):
    '''
    input: key from census_subnational dictionary (str)
    output: pandas dataframe
    description: extracts relevant subnational population data from the census website
    '''
    adm_level = int(country[-1])
    
    most_recent_cols = ['BTOTL_2020', 'BTOTL_2019', 'BTOTL_2018', 'BTOTL_2017', 'BTOTL_2016']
    country_url = census_subnational[country]
    data = pd.read_excel(country_url, sheet_name=2, header=3)
    
    recent_pop_estimate = ''
    counter = 0
    while counter < 4:
        if most_recent_cols[counter] not in most_recent_cols:
            counter += 1
        else:
            recent_pop_estimate += most_recent_cols[counter]
            break
            
    data = data.dropna(subset=f'ADM{adm_level}_NAME')
    
    pop_col_name = f'ADM{str(adm_level)} Population {recent_pop_estimate[-4:]}'
    if adm_level == 4:
        
        data = data[['CNTRY_NAME', 'GEO_MATCH', 'ADM1_NAME', 'ADM2_NAME', 'ADM3_NAME', 'ADM4_NAME', recent_pop_estimate]].copy()
        data.columns = ['Country', 'GEO_MATCH', 'ADM1 Name', 'ADM2 Name', 'ADM3 Name', 'ADM4 Name', pop_col_name]
    elif adm_level == 3:
        data = data[['CNTRY_NAME', 'GEO_MATCH', 'ADM1_NAME', 'ADM2_NAME', 'ADM3_NAME', recent_pop_estimate]].copy()
        data.columns = ['Country', 'GEO_MATCH', 'ADM1 Name', 'ADM2 Name', 'ADM3 Name', pop_col_name]
    elif adm_level == 2:
        data = data[['CNTRY_NAME', 'GEO_MATCH', 'ADM1_NAME', 'ADM2_NAME', recent_pop_estimate]].copy()
        data.columns = ['Country', 'GEO_MATCH', 'ADM1 Name', 'ADM2 Name', pop_col_name]
    else:
        data = data[['CNTRY_NAME', 'GEO_MATCH', 'ADM1_NAME', recent_pop_estimate]].copy()
        data.columns = ['Country', 'GEO_MATCH', 'ADM1 Name', pop_col_name]
        
    return data
