import pandas as pd
import geopandas as gpd
import folium
import numpy
import os
import dask.dataframe as dd
import dask_geopandas
import collections
from country_rename import country_dict
from country_tests import country_tests
import ipywidgets as widgets
from ipywidgets import interactive






########################################
######## processing functions ##########
########################################


def read_adm_data(adm_level):
    '''
    input: adm_level (int)
    output: dask geodataframe 
    description: reads in the specific subnational boundary polygons for a specified adm_level
    '''
    if adm_level not in [0,1,2,3,4]:
        raise ValueError('Data is only available for levels 1, 2, 3, 4') 
        
    adm_df = dask_geopandas.read_file(f'./data/boundaries/adm{adm_level}_polygons/adm{adm_level}_polygons.shp', chunksize=500_000)
    return adm_df


def read_people_areas_data():
    '''
    input: -
    output: dask geodataframe 
    description: reads in the people areas dataset (people polygons)
    '''
    people_areas = dask_geopandas.read_file('./data/people_groups/people_areas.geojson', chunksize=500_000)
    
    return people_areas
    
    
def read_population_data(adm_level):
    '''
    input: adm_level (int)
    output: dask dataframe 
    description: reads in the subnational population dataset for a specified adm_level
    '''
    if adm_level not in [0,1,2,3,4]:
        raise ValueError('Data is only available for levels 1, 2, 3, 4')
        
    data_types = {f'adm0_name': 'str',
                  f'adm{adm_level}_src': 'str',
                  f'adm{adm_level}_id': 'str',
                  f'adm{adm_level}_name': 'str',
                 't': 'float64'}
    
    pop_df = dd.read_csv(f'./data/populations/adm{adm_level}_population.csv', dtype = data_types, usecols=['adm0_name', 
                                                                                                           f'adm{adm_level}_src',
                                                                                                           f'adm{adm_level}_id',
                                                                                                           f'adm{adm_level}_name', 
                                                                                                           't'])
    return pop_df






########################################
######## validation functions ##########
########################################
        
    
def calculate_total_boundary_pop(lst, subnational_data, adm_level):
    '''
    input: lst (list), subnational_data (pandas dataframe), adm_level (int)
    output: pop_sum (float)
    description: helper function to be applied to the list of boundary polygons found after the spatial join method
    '''
    pop_sum = 0
    for item in lst:
        pop_sum += subnational_data[subnational_data[f'adm{adm_level}_id'] == item]['population_total'].iloc[0]
        
    return pop_sum


def validate_country(country, adm_level):
    '''
    input: country (str), adm_level (int)
    output: pandas dataframe 
    description: validates all people groups in the specified country at the specified adm_level.
    '''
    
    if adm_level not in [0,1,2,3,4]:
        raise ValueError('Data is only available for levels 1, 2, 3, 4')
        
    if adm_level not in list(country_tests[country]):
        raise ValueError(f'This test is not available for {country}. Please choose from the following: {list(country_tests[country])}')
    
    print('started initial loading of subnational data')
    adm_boundaries = read_adm_data(adm_level)
    adm_populations = read_population_data(adm_level)
    country_boundaries = adm_boundaries[adm_boundaries['adm0_name'] == country].compute()
    
    if country_boundaries[f'adm{adm_level}_src'].isnull().sum() > 0:
        if country_boundaries[f'adm{adm_level}_id'].isnull().sum() > 0:
            raise Exception(f'This country does not have adm{adm_level} level boundary data. Please input an adm level less than the current input')
    
    print('loading people areas data')
    people_areas = read_people_areas_data()
    
    # df with boundary AND subnational population data
    adm_complete = country_boundaries.merge(adm_populations[[f'adm{adm_level}_id', 't']].compute(), on=f'adm{adm_level}_id')
    
    if adm_complete.shape[0] == 0:
        raise Exception('Error merging subnational population data with subnational boundary data.')
    
    print('merged subnational data')
    
    people_areas = people_areas.compute().replace(country_dict)
        
    sjoin_result = dask_geopandas.sjoin(people_areas[people_areas['Ctry'] == country], 
                                 adm_complete[[f'adm{adm_level}_id', f'adm{adm_level}_src', f'adm{adm_level}_name', 'geometry']]).compute()
    print('first spatial join complete')
        
    sjoin_result = sjoin_result.rename(columns={'Name': 'People Group',
                                                    'Pop': 'People Group Population', 
                                                    'GENC0': 'Alpha-3 Code',
                                                    'Ctry': 'Country'})
            
    sjoin_aggregated = sjoin_result.groupby('People Group').agg({'Alpha-3 Code': 'first',
                                                             'Country': 'first',
                                                             'People Group Population': 'first',
                                                             'geometry': 'first',
                                                             f'adm{adm_level}_id': list,
                                                             }).rename({f'adm{adm_level}_id':'boundaries_present'}, axis=1).reset_index()
    print('cleaned spatial join result')
   
    country_pop_table = adm_populations[adm_populations['adm0_name'] == country].compute().rename({'t':'population_total'}, axis=1)

    sjoin_aggregated['total_boundary_population'] = sjoin_aggregated['boundaries_present'].apply(lambda x: calculate_total_boundary_pop(x, country_pop_table, adm_level))

    # 5% error
    sjoin_aggregated['valid'] = (sjoin_aggregated['total_boundary_population'] * 1.05) >= sjoin_aggregated['People Group Population']

    sjoin_aggregated['percent_total_boundary'] = (sjoin_aggregated['People Group Population'] / sjoin_aggregated['total_boundary_population']) * 100
    
    sjoin_aggregated['test_type'] = adm_level
    
    sjoin_aggregated.sort_values(by='percent_total_boundary', ascending=False, inplace=True)
    
    return sjoin_aggregated






########################################
######### mapping functions ############
########################################


def save_map(results_df):
    '''
    input: results_df (pandas dataframe)
    output: - 
    description: saves all the invalid people groups within a specific country at a specific level as an html map in the output directory
    '''
    if os.path.isdir('output'):
        pass
    else:
        os.mkdir('output')
        
    country = results_df['Country'].iloc[0]
    invalid_df = results_df[results_df['valid'] == False]
    invalid_df = invalid_df.drop('boundaries_present', axis=1)
    invalid_df = gpd.GeoDataFrame(invalid_df, crs='EPSG:4326')
    
    if invalid_df.shape[0] == 0:
        return print(f'All people groups in {country} are valid. There is no map to be saved.')
    
    invalid_df = invalid_df[~invalid_df['People Group'].str.contains('Deaf') & ~invalid_df['People Group'].str.contains(r'Han Chinese')]
    
    invalid_df.explore(color='red').save(f'./output/{country}_invalid_adm{invalid_df["test_type"].iloc[0]}.html')

    
def view_map(df, color='red', people_group='all'):
    '''
    input: df (dataframe), color (str), people_group (str)
    output: folium map
    description: displays a folium map of a specific country that has been validated. if people_group = all, then
    all people groups will be displayed. make sure that the people group is spelled correctly and located
    in the specific country that was validated.
    '''
    
    if df.shape[0] == 0:
        raise Exception('The results dataframe has no data')
    
    gdf = gpd.GeoDataFrame(df, crs='EPSG:4326')
    gdf = gdf[~gdf['People Group'].str.contains('Deaf') & ~gdf['People Group'].str.contains('Han Chinese')]

    if people_group != 'all':
        assert people_group in gdf['People Group'].tolist()
        gdf = gdf[gdf['People Group'] == people_group]
    
    return gdf.explore(color=color)
    
 
    
    
    
########################################
########## notebook widget #############
########################################   


def view_available_tests(country):
    print(f'Available tests for {country:10}: {country_tests[country]}' )   


def available_tests_widget():
    return widgets.interact(view_available_tests, country=list(country_tests.keys()));    
   



    
    
########################################
########## other functions #############
########################################
    
    
def view_project_structure():
    '''
    input: -
    output: - 
    description: prints out the directory structure of the current people groups validation project
    '''
    struct = """
        validation/
        ├── validation.ipynb
        ├── functions.py
        ├── country_tests.py
        ├── country_rename.py
        ├── country_inputs.py
        └── data/
            ├── boundaries/
            │   ├── adm0_polygons/
            │   │   ├── adm0_polygons.shp
            │   │   ├── adm0_polygons.cpg
            │   │   ├── adm0_polygons.dbf
            │   │   ├── adm0_polygons.prj
            │   │   └── adm0_polygons.shx
            │   ├── adm1_polygons/
            │   │   ├── adm1_polygons.shp
            │   │   ├── adm1_polygons.cpg
            │   │   ├── adm1_polygons.dbf
            │   │   ├── adm1_polygons.prj
            │   │   └── adm1_polygons.shx
            │   ├── adm2_polygons/
            │   │   ├── adm2_polygons.shp
            │   │   └── ...
            │   ├── adm3_polygons/
            │   │   ├── adm3_polygons.shp
            │   │   └── ...
            │   └── adm4_polygons/
            │       ├── adm4_polygons.shp
            │       └── ...
            ├── populations/
            │   ├── adm0_populations.csv
            │   ├── adm1_populations.csv
            │   ├── adm2_populations.csv
            │   ├── adm3_populations.csv
            │   └── adm4_populations.csv
            ├── people_groups/
            │   └── people_areas.geojson
            └── images/
                └── ihs-logo.png
        """;
    
    print(struct)