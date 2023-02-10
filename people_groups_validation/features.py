import pandas as pd
import geopandas as gpd
import folium
from shapely import *
from shapely.validation import make_valid
import gdown
import numpy as np
from pathlib import Path
import warnings
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
        

    adm1_pop_data_url = 'https://drive.google.com/uc?id=1Ae60lcYPcaCIw2vwY62ZLMfmmbUwJ6F5'
    pop_data_path = './data/global_adm1_populations.xlsx'
    gdown.download(adm1_pop_data_url, pop_data_output, quiet=False)
    
    world_populations = pd.concat(pd.read_excel(pop_data_path, sheet_name=None), ignore_index=True)
    cgaz_geometries = pd.read_csv('./data/cgaz_geometries.csv', index_col=[0])
    full_subnational_data = world_populations.merge(cgaz_geometries, left_on='CGAZ shape ID', right_on='shapeID')
    full_subnational_data.geometry = full_subnational_data.geometry.apply(wkt.loads)
    full_subnational_data = gpd.GeoDataFrame(full_subnational_data, geometry = 'geometry', crs = 'EPSG:4326')
    
    return people_areas, full_subnational_data




def find_all_adm1(ppg_gdf, pop_data, generate_report):
    '''
    input: ppg_gdf (geodataframe), pop_data (dataframe), generate_report (boolean)
    output: people_areas (dataframe)
    description: Helper function for validate_country. Finds all the ADM1 boundaries that a people group intersects.
    '''
    
    ppl_areas = ppg_gdf.copy()
    
    # set both Coordinate Reference Systems (CRS) to be EPSG:4326
    ppl_areas.crs = 'EPSG:4326'
    pop_data.crs = 'EPSG:4326'
    
    
    # Finding all overlapping boundaries
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
    
    # add the valid column -- total boundary population >= people group population
    ppl_areas['Valid People Group'] = ppl_areas['Total Boundary Population'] >= ppl_areas['People Group Population']
    
    # generate_report - add print statements to tell you which people groups are invalid and why
    if generate_report:
        invalid_people_groups = ppl_areas[ppl_areas['Valid People Group'] == False]
        if invalid_people_groups.shape[0] == 0:
            print(f'All people groups in {ppl_areas.Country.iloc[0]} are valid.')
        
        for ppl_group in invalid_people_groups['People Group']:
            if invalid_people_groups[invalid_people_groups['People Group'] == ppl_group]['ADM1 Boundaries Present'].iloc[0] == 'NONE':
                print(f'The {ppl_group} people group did not intersect with a CGAZ ADM1 boundary. They may be valid.')
            elif invalid_people_groups[invalid_people_groups['People Group'] == ppl_group]['ADM1 Boundaries Present'].iloc[0] == 'NONE':
                print(f'The {ppl_group} people group had a population greater than all ADM1 boundaries they intersected. They are invalid.')            
        
    ppl_areas
    
    
    return ppl_areas




def find_total_boundary_pop(lst, subnational_data):
    '''
    input: lst (list), subnational_data (dataframe)
    description: Helper function for find_all_adm1
    '''
    if lst == 'NONE':
        return np.nan
    
    pop_sum = 0
    for item in lst:
        pop_sum += subnational_data[subnational_data['ADM1 Name'] == item]['ADM1 Population'].iloc[0]
    return pop_sum




def validate_country(country, generate_report=False):
    '''
    input: country (str), generate_report (boolean)
    output: dataframe 
    description: Returns a Pandas dataframe validating all the people groups within a certain country. If generate_report=True, it prints out why some groups did not pass the validation
    '''
    
    ppg_gdf, subnational_data = process_input_data()
    
    # select subnational population data for a specific country
    country_pop = subnational_data[subnational_data['Country'] == country].copy()
    
    # if geometry isn't already valid, make it valid using shapely function
    country_pop.geometry = country_pop.apply(lambda row: make_valid(row.geometry) if not row.geometry.is_valid else row.geometry, axis=1)
    
    
    # select people groups data for a specific country
    country_ppg = ppg_gdf[ppg_gdf['Country'] == country]
    
    return find_all_adm1(country_ppg, country_pop, generate_report)



def validate_all(ppg_gdf, subnational_data, generate_report=False):
    '''
    description: Returns a Pandas dataframe validating all people groups
    '''
    raise NotImplementedError('Function not implemented yet.')


def countries_with_data():
    '''
    output: list
    description: Returns a list of countries that currently have subnational data
    '''
    
    adm1_pop_data_url = 'https://drive.google.com/uc?id=1Ae60lcYPcaCIw2vwY62ZLMfmmbUwJ6F5'
    pop_data_path = './data/global_adm1_populations.xlsx'
    gdown.download(adm1_pop_data_url, pop_data_path, quiet=True)
    
    adm1_populations = pd.concat(pd.read_excel('./data/global_adm1_populations.xlsx', sheet_name=None), ignore_index=True)
    return sorted(adm1_populations.dropna(subset=['ADM1 Population']).Country.unique())


def map_results(df, query=None):
    '''
    output: folium map
    description: 
    '''
    
    results_map = df.query('`ADM1 Boundaries Present` == "NONE"')
    return results_map.explore(color='red')


def update_population_data():
    adm1_pop_data_url = 'https://drive.google.com/uc?id=1Ae60lcYPcaCIw2vwY62ZLMfmmbUwJ6F5'
    pop_data_path = './data/global_adm1_populations.xlsx'
    gdown.download(adm1_pop_data_url, pop_data_path, quiet=False)