import pandas as pd
import geopandas as gpd
import folium
from shapely import *
from shapely.validation import make_valid
import numpy as np





def prettylist(lst, remove_br=False):
    '''
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
    requires people_areas.geojosn, global_adm1_populations.xlsx, and cgaz_geometries to be downloaded and stored in the data directory.
    """
    people_areas = gpd.read_file('./data/people_areas.geojson')
    people_areas = people_areas[['Name', 'GENC0', 'Pop', 'Ctry', 'geometry']].rename(columns={'Name': 'People Group', 'Pop': 'People Group Population', 'GENC0': 'Alpha-3 Code', 'Ctry': 'Country'})
    
    world_populations = pd.concat(pd.read_excel('./data/global_adm1_populations.xlsx', sheet_name=None), ignore_index=True)
    cgaz_geometries = pd.read_csv('./data/cgaz_geometries.csv', index_col=[0])
    full_subnational_data = world_populations.merge(cgaz_geometries, left_on='CGAZ shape ID', right_on='shapeID')
    full_subnational_data.geometry = full_subnational_data.geometry.apply(wkt.loads)
    full_subnational_data = gpd.GeoDataFrame(full_subnational_data, geometry = 'geometry', crs = 'EPSG:4326')
    
    return people_areas, full_subnational_data




def find_all_adm1(ppg_gdf, pop_data, generate_report):
    '''
    Finds all the ADM1 boundaries that a people group intersects. 
    ppg_gdf -> people areas dataframe
    pop_data -> subnational data 
    generate_report -> prints people groups that are any invalid and explains why
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
    # ppl_areas['Total Boundary Population'] = ppl_areas['ADM1 Boundaries Present'].apply(find_total_boundary_pop)
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

    return ppl_areas




def find_total_boundary_pop(lst, subnational_data):
    '''
    Helper function for find_all_adm1
    '''
    if lst == 'NONE':
        return np.nan
    
    pop_sum = 0
    for item in lst:
        pop_sum += subnational_data[subnational_data['ADM1 Name'] == item]['ADM1 Population'].iloc[0]
    return pop_sum




def validate_country(ppg_gdf, subnational_data, country, generate_report=False):
    '''
    Returns a Pandas dataframe validating all the people groups within a certain country
    ppg_gdf -> full people areas dataframe
    pop_data -> subnational data 
    generate_report -> prints people groups that are any invalid and explains why
    '''
    # select subnational population data for a specific country
    country_pop = subnational_data[subnational_data['Country'] == country].copy()
    
    # if geometry isn't already valid, make it valid using shapely function
    country_pop.geometry = country_pop.apply(lambda row: make_valid(row.geometry) if not row.geometry.is_valid else row.geometry, axis=1)
    
    
    # select people groups data for a specific country
    country_ppg = ppg_gdf[ppg_gdf['Country'] == country]
    
    return find_all_adm1(country_ppg, country_pop, generate_report)





def validate_all(ppg_gdf, subnational_data, generate_report=False):
    '''
    Returns a Pandas dataframe validating all people groups
    ppg_gdf -> full people areas dataframe
    pop_data -> subnational data 
    generate_report -> prints people groups that are any invalid and explains why
    '''
    
    return find_all_adm1(ppg_gdf, subnational_data, generate_report)

