import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
from shapely import wkt
import numpy as np


def prettylist(lst, remove_br=False):
    '''
    Parameter(s): List
    Parameter(s): Boolean (Default=False, returns whether the final string is to contain the breaks, coded as <br>)
    Description: This function concatenates a list of strings in order to be viewed nicely when making an interactive Folium map. 
    It ensures that the field does not run off the page when viewing points on an interactive Folium map.
    '''
    people_string = ''
    char_count = 0
    index = 0
    while index < len(lst):
        item = lst[index]
        if index == (len(lst) - 1):
            people_string += item
            char_count += len(item)
        elif char_count >= 40:
            people_string += "<br>" + item + ', '
            char_count = 0
        else:
            people_string += item + ', '
            char_count += len(item)
        index += 1
    if remove_br:
        people_string = people_string.replace('<br>', '')
    return people_string


def adm1(ppg_df, shapes, adm1_name):
    '''
    Parameter(s): DataFrame (People groups data frame. Should be the cleaned result of the find_ppg_data function.
    Parameter(s): GeoDataFrame (GeoDataFrame from adm1 shapefile)
    Parameter(s): String (Name of the administrative level 1 subdivision name - e.g. Province)
    Note: PeopleGroups points that fall outside of an administrative region have their ADM1 subdivision encoded as "MISSING".
    These groups need to have their information manually filled in.
    '''

    subdivisions = []
    for i in np.arange(len(ppg_df.index)):
        # Create a coordinate based on a People Group's latitude and longitude
        coordinate = Point(map(float, (ppg_df['Longitude'].iloc[i], ppg_df['Latitude'].iloc[i])))
        grouped_subdivisions = shapes[shapes['geometry'].contains(coordinate) == True].index.values
        if len(grouped_subdivisions) == 0:
            grouped_subdivisions = ['MISSING']
        subdivisions.append(grouped_subdivisions[0])
    
    matches = [shapes['shapeName'].iloc[i] for i in subdivisions]
    ppg_df[adm1_name] = matches
    print(f"Please check the generated {adm1_name} column for missing values, encoded as 'MISSING'")
    print(f"There are {sum(ppg_df[adm1_name] == 'MISSING')} unassigned people groups.")
    return ppg_df



def find_ppg_data(ppg_df, country):
    '''
    Parameter(s): DataFrame (People groups data frame. MUST be cleaned according to other functions)
    Parameter(s): String (Name of a Country, e.g. 'Papua New Guinea')
    Descriptions: Finds PeopleGroups data for a specific country. 
    Based off of 2 filters: People groups with Country column = country and People groups without a Country of Origin ('NONE or Without Homeland')
    Note: This function takes into consideration that there are PeopleGroups within a country that are not indigenous to the area. It removes
    People Groups that have a country of origin and Deaf peoples. However, it is not 100% accurate so further cleaning may be needed to remove non-indigenous groups.
    This function also reformats the language variable to remove the 3 letter language code.
    '''
    country_data = ppg_df[ppg_df['Country'] == country]
    country_data = country_data.replace({np.nan:'NONE', 'Without Homeland': 'NONE'})
    only_indigenous = country_data[(country_data['Country of Origin'] == 'NONE')]
    only_indigenous = only_indigenous[only_indigenous['IMB Affinity Group'] != 'Deaf Peoples']
    clean_df = only_indigenous[['IMB Affinity Group', 'Country', 'People Group', 'People Name', 'Population', 'Language', 'Religion', 'Population', 'Latitude', 'Longitude']]
    rename_language = clean_df.copy()
    rename_language['Language'] = rename_language['Language'].str.extract('(^\w+(?:\s\w+)*)')[0]
    print('This dataset may still need cleaning. Please review the returned dataset.')
    return rename_language
    


def convert_to_geodataframe(df):
    """
    Parameter(s): DataFrame (clean PeopleGroups dataset)
    Output: GeoDataFrame
    Description: This function converts a people groups dataframe to a geodataframe by using the Latitude and Longitude columns.
    given from the PeopleGroups spreadsheet.
    Note: This method is best used with the resulting DataFrame of the find_ppg_data() function.
    """
    if not ('Latitude' in df.columns and 'Longitude' in df.columns):
        raise ValueError('Latitude or Latitude columns not found in DataFrame.')
    df = df[['IMB Affinity Group', 'Country', 'People Group', 'People Name', 'Population', 'Language', 'Religion', 'Latitude', 'Longitude']]
    df_copy = df.copy()
    df_copy['geometry'] = gpd.points_from_xy(df.Longitude, df.Latitude)
    df_copy = gpd.GeoDataFrame(df_copy, geometry = 'geometry', crs='epsg:4326')
    return df_copy