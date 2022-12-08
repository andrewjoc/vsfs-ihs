# Indian Health Service: Data Collection
### Objective
The mission of IHS is to raise the physical, mental, social and spiritual health of American Indians and Alaska natives (AI/AN) to the highest level. To be responsive to the second goal of its 2019-2023
strategic plan "to promote excellence and quality through innovation of the Indian health system into an optimally performing organization," the Division of Program Statistics in the Office of Public Health
needs to continue its work in discovering new information concerning native peoples throughout the world. International studies of the health of native (or indigenous) peoples provide essential public
health insights. Reliable data are required for the development of policy and health services. A landmark 2016 paper in which IHS participated, "Indigenous and tribal peoples' health (The Lancet–Lowitja
Institute Global Collaboration): a population study" studied 23 states and 28 indigenous peoples within those states. The methods used for that paper overturned the idea that such groups always fare more poorly than benchmark populations. 
The coverage of nations or the range of health indicators had been limited in earlier work. Our objective is to expand upon the work already done to describe the health and social status of native or indigenous peoples in new areas of the world by acquiring and compiling more data on these populations.
* Indian Health Service DPS website: https://www.ihs.gov/dps/
* Link to Paper: https://www.lowitja.org.au/page/services/resources/health-policy-and-systems/data/Lancet-Lowitja-Institute-Collaboration



***
### Current Project
* *Validate People Groups data based on population estimates by national census bureaus.*

[11/10] 
* Finished method 1, referencing People Groups points to administrative level 1 (ADM1) boundaries. Compared population of people group to official subnational population estimates.
Another method is needed to account for the often large areas that indigenous groups span (across ADM1 boundaries).

[11/15]
* Currently experiencing issues with method 2
  * Pushing large shapefile to GitHub (> 100 MB)
  * Inconsistent naming of ADM1 boundaries between datasets. Difficult to merge and compare population numbers.

[12/7]
* Created MongoDB cluster and uploaded subnational population data & subnational boundaries (CGAZ - geoBoundaries).  
* Subnational boundaries have 2 countries that do not have labels for any ADM1  
    * Afghanistan, Angola
* After filling in boundaries for Afghanistan and Angola, will need to begin matching the names of each ADM1 between the 2 datasets to make sure they can be merged later on.
    * reminder to make sure the datasets are utf-8 encoded
* Need to upload PeopleAreas GeoJSON to a database in MongoDB, kept crashing (?)  
  
  
 ***
 ### Datasets
 * People Groups Data: https://www.peoplegroups.org/258.aspx
 * People Groups Area Data: https://go-imb.opendata.arcgis.com/datasets/imb::apg-people-group-areas/explore?location=43.783411%2C70.948650%2C4.70  
 * Subnational Boundaries (CGAZ): https://www.geoboundaries.org/downloadCGAZ.html  
 * Subnational Population Data (Oxford MPI, sheet 1): https://ophi.org.uk/multidimensional-poverty-index/
