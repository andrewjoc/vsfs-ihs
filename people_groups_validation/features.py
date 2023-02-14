import pandas as pd
import geopandas as gpd
import folium
from shapely import *
from shapely.validation import make_valid
import gdown
import numpy as np
from pathlib import Path
import warnings
import collections
from shapely.errors import ShapelyDeprecationWarning
warnings.filterwarnings("ignore", category=ShapelyDeprecationWarning) 





def prettylist(lst, remove_br=False):
    '''
    input: lst (list), remove_br (boolean)
    output: people_string (str)
    Concatenates a list of strings in order to be viewed nicely when making an interactive Folium map. 
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




def process_input_data():
    """
    output: people_areas (dataframe), full_subnational_data (dataframe)
    description: cleans the dataframes to be used in analysis
    """
    
    # load data from google drive
    people_areas_file = Path("./data/people_areas.geojson")
    
    if people_areas_file.is_file():
        pass
    else:
        people_areas_drive_url = 'https://drive.google.com/uc?id=1xKdfjp2B23VHqo_o4u3kyunioxxFNgSO'
        output = './data/people_areas.geojson'
        gdown.download(people_areas_drive_url, output, quiet=False)
    
    cgaz_geometries_file = Path("./data/cgaz_geometries.csv")
    
    if cgaz_geometries_file.is_file():
        pass
    else: 
        cgaz_geometries_drive_url = 'https://drive.google.com/uc?id=1OxWZpEKy-Gpp6EsT9OBbTYBoz9BULam8'
        output = './data/cgaz_geometries.csv'
        gdown.download(cgaz_geometries_drive_url, output, quiet=False)
    
    # read files as dataframes
    people_areas = gpd.read_file('./data/people_areas.geojson')
    people_areas = people_areas[['Name', 'GENC0', 'Pop', 'Ctry', 'geometry']].rename(columns={'Name': 'People Group', 'Pop': 'People Group Population', 'GENC0': 'Alpha-3 Code', 'Ctry': 'Country'})
        

    # each time a validation is run, adm1 population data is read from google drive 
    adm1_pop_data_url = 'https://drive.google.com/uc?id=1Ae60lcYPcaCIw2vwY62ZLMfmmbUwJ6F5'
    pop_data_path = './data/global_adm1_populations.xlsx'
    gdown.download(adm1_pop_data_url, pop_data_path, quiet=True)
    
    world_populations = pd.concat(pd.read_excel(pop_data_path, sheet_name=None), ignore_index=True)
    cgaz_geometries = pd.read_csv('./data/cgaz_geometries.csv', index_col=[0])
    full_subnational_data = world_populations.merge(cgaz_geometries, left_on='CGAZ shape ID', right_on='shapeID')
    full_subnational_data.geometry = full_subnational_data.geometry.apply(wkt.loads)
    full_subnational_data = gpd.GeoDataFrame(full_subnational_data, geometry = 'geometry', crs = 'EPSG:4326')
    
    return people_areas, full_subnational_data




def find_all_adm1(ppg_gdf, pop_data, verbose):
    '''
    input: ppg_gdf (geodataframe), pop_data (dataframe), verbose (boolean)
    output: people_areas (dataframe)
    description: Helper function for validate_country. Finds all the ADM1 boundaries that a people group intersects.
    '''
    
    ppl_areas = ppg_gdf.copy()
    
    # set both Coordinate Reference Systems (CRS) to be EPSG:4326
    ppl_areas.crs = 'EPSG:4326'
    pop_data.crs = 'EPSG:4326'
    
    
    # Finding all overlapping people polygons and ADM1 boundaries
    if verbose:
        print('Finding overlapping polygons')
        
    boundaries = []
    for people_polygon in ppl_areas.geometry:
        name = ppl_areas[ppl_areas.geometry == people_polygon]['People Group'].iloc[0]
        
        # true false series
        overlapping_polygons = pop_data.geometry.intersects(people_polygon)        
    
        # from stack overflow - select series indices based on True values
        indices = overlapping_polygons[overlapping_polygons].index.values        
        
        # select the names of the boundaries
        all_boundaries_found = pop_data.query('index in @indices')['ADM1 Name'].to_list()
        
        if len(all_boundaries_found) == 0:
            boundaries.append('NONE')
        else:
            boundaries.append(all_boundaries_found)
            
    # create new series that is the list of all boundaries present
    ppl_areas['ADM1 Boundaries Present'] = boundaries     
    
    # add the total boundary population column
    ppl_areas['Total Boundary Population'] = ppl_areas['ADM1 Boundaries Present'].apply(lambda x: find_total_boundary_pop(x, pop_data))
    
    # add the valid column -- (total boundary population * 1.05) >= people group population 
    ppl_areas['Valid People Group'] = (ppl_areas['Total Boundary Population'] * 1.05) >= ppl_areas['People Group Population']
    
    # verbose - add print statements to tell you which people groups are invalid and why
    if verbose:
        invalid_people_groups = ppl_areas[ppl_areas['Valid People Group'] == False]
        if invalid_people_groups.shape[0] == 0:
            print(f'All people groups in {ppl_areas.Country.iloc[0]} are valid.')
        
        for ppl_group in invalid_people_groups['People Group']:
            if invalid_people_groups[invalid_people_groups['People Group'] == ppl_group]['ADM1 Boundaries Present'].iloc[0] == 'NONE':
                print(f'The {ppl_group} people group did not intersect with a CGAZ ADM1 boundary. They may be valid.')
            elif invalid_people_groups[invalid_people_groups['People Group'] == ppl_group]['People Group Population'].iloc[0] >= invalid_people_groups[invalid_people_groups['People Group'] == ppl_group]['Total Boundary Population'].iloc[0] * 1.05: # error of 5%
                print(f'The {ppl_group} people group had a population greater than all ADM1 boundaries they intersected. They are invalid.')            
        
    ppl_areas
  
    return ppl_areas




def find_total_boundary_pop(lst, subnational_data):
    '''
    input: lst (list), subnational_data (dataframe)
    output: pop_sum (float)
    description: Helper function for find_all_adm1
    '''
    if lst == 'NONE':
        return np.nan
    
    pop_sum = 0
    for item in lst:
        pop_sum += subnational_data[subnational_data['ADM1 Name'] == item]['ADM1 Population'].iloc[0]
    return pop_sum




def validate_country(country, verbose=True):
    '''
    input: country (str), verbose (boolean)
    output: dataframe
    description: Returns a Pandas dataframe validating all the people groups within a certain country. If verbose=True, it prints out current status of the function and why some groups did not pass the validation
    '''
    
    adm1_populations = pd.concat(pd.read_excel('./data/global_adm1_populations.xlsx', sheet_name=None), ignore_index=True)
    countries_list = adm1_populations.dropna(subset=['ADM1 Population']).Country.unique()
    
    assert country in countries_list, "The country you\'ve attempted to validate either has no ADM1 population data or it is misspelled."
        
    if verbose:    
        print('Processing input data')
        
    ppg_gdf, subnational_data = process_input_data()
    
    
    # select subnational population data for a specific country
    country_pop = subnational_data[subnational_data['Country'] == country].copy()
    
    # if geometry isn't already valid, make it valid using shapely function
    country_pop.geometry = country_pop.apply(lambda row: make_valid(row.geometry) if not row.geometry.is_valid else row.geometry, axis=1)
    
    
    # select people groups data for a specific country
    country_ppg = ppg_gdf[ppg_gdf['Country'] == country]
    
    adm1_populations = pd.concat(pd.read_excel('./data/global_adm1_populations.xlsx', sheet_name=None), ignore_index=True)    
    
    return find_all_adm1(country_ppg, country_pop, verbose)


def countries_with_data():
    '''
    output: list of tuples
    description: Returns a list of countries that currently have subnational population data
    '''
    
    countries = collections.defaultdict(list)
    adm1_pop_data_url = 'https://drive.google.com/uc?id=1Ae60lcYPcaCIw2vwY62ZLMfmmbUwJ6F5'
    pop_data_path = './data/global_adm1_populations.xlsx'
    gdown.download(adm1_pop_data_url, pop_data_path, quiet=True)
    
    adm1_populations = pd.concat(pd.read_excel('./data/global_adm1_populations.xlsx', sheet_name=None), ignore_index=True)
    countries_lst = sorted(adm1_populations.dropna(subset=['ADM1 Population']).Country.unique())
    
    for country in countries_lst:
        countries[country[0]].append(f'"{country}"')
    for letter, country in countries.items():
        print(letter + ":", ", ".join(country))


def map_results(df, query=None):
    '''
    output: folium map
    description: outputs an interactive map of people groups that did not intersect any ADM1 boundaries.
    '''
    
    results_map = df.query('`ADM1 Boundaries Present` == "NONE"')
    
    if results_map.query('`ADM1 Boundaries Present` == "NONE"').shape[0] == 0:
        print('This country has no people groups that did not intersect with ADM1 boundaries.')
        return
    
    return results_map.explore(color='red')