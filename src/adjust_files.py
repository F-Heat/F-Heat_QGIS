import geopandas as gpd
import pandas as pd
from shapely.geometry import LineString,MultiLineString
import re
from collections import Counter
import numpy as np
from datetime import datetime, date
 
#change: automatisch Verzeichnis erstellen und Dateien (streets, parcels und buildings) anlegen + möglicher Expertenmodus
#change: Vorauswahl Spalten "RW_WW" usw.

class Streets_adj():
    '''
    A class used to represent and manipulate street geometries.

    This class provides methods to round the coordinates of street geometries and to add a boolean column
    indicating possible routes.

    Attributes
    ----------
    gdf : GeoDataFrame
        A GeoDataFrame containing the street geometries.

    Methods
    -------
    round_streets():
        Rounds the coordinates of street geometries to 3 decimal places.
        
    add_bool_column():
        Adds a boolean column indicating possible routes.
    '''

    def __init__(self, path):
        '''
        Initializes the Streets_adj class with a GeoDataFrame of street geometries.

        Parameters
        ----------
        path : str
            The file path to the shapefile containing the street geometries.
        '''
        self.gdf = gpd.read_file(path)
        
    def round_streets(self):
        '''
        Rounds the coordinates of street geometries to 3 decimal places.

        This method processes the geometries in the GeoDataFrame, converting any MultiLineString geometries
        to LineString geometries, and then rounds their coordinates to 3 decimal places.

        Notes
        -----
        - If any MultiLineString geometries are found, they are converted to LineString geometries by taking
          the first component of the MultiLineString.
        - A warning is printed if any MultiLineString geometries are found and processed.
        '''
        # Helper functions
        def convert_multilinestring_to_linestring(geometry, x):
            '''
            Converts a MultiLineString geometry to a LineString geometry.

            Parameters
            ----------
            geometry : shapely.geometry.MultiLineString or shapely.geometry.LineString
                The geometry to be converted.
            x : int
                A counter for tracking the number of MultiLineString geometries found.

            Returns
            -------
            shapely.geometry.LineString
                The converted LineString geometry.
            int
                The updated counter.
            '''
            if isinstance(geometry, MultiLineString):
                x += 1
                return LineString(list(geometry.geoms)[0].coords), x
            else:
                return geometry, x

        def round_coordinates(line):
            '''
            Rounds the coordinates of a LineString geometry to 3 decimal places.

            Parameters
            ----------
            line : shapely.geometry.LineString
                The LineString geometry to be rounded.

            Returns
            -------
            shapely.geometry.LineString
                The rounded LineString geometry.
            '''
            rounded_coords = [(round(x, 3), round(y, 3)) for x, y in line.coords]
            return LineString(rounded_coords)

        streets = self.gdf
        x = 0
        streets['geometry'], x = zip(*streets['geometry'].apply(lambda geom: convert_multilinestring_to_linestring(geom, x)))
        streets['geometry'] = streets['geometry'].apply(round_coordinates)
        
        if max(x) > 0:
            print('At least one street geometry is a MultiLineString! Continuing with the first LineString as the street. Check the street geometry if necessary.')
        self.gdf = streets 
    
    def add_bool_column(self):
        '''
        Adds a boolean column to the GeoDataFrame indicating possible routes.

        This method adds a new column 'Moegliche_Route' (= possible route) to the GeoDataFrame, initialized with the value 1 for all rows.
        '''
        self.gdf['Moegliche_Route'] = 1

class Buildings_adj():
    '''
    A class to represent and manipulate building geometries and attributes.

    This class provides methods for adding load profiles, filtering buildings, adding power attributes,
    classifying buildings by age, and merging building data with custom aggregations. It also allows for 
    the integration of custom heat demand data based on building characteristics.

    Attributes
    ----------
    gdf : GeoDataFrame
        A GeoDataFrame containing building geometries and associated attributes.
    heat_att : str
        The attribute name for heat data in the GeoDataFrame.

    Methods
    -------
    add_Vlh_Loadprofile(excel_data):
        Adds full load hours (Vlh) and load profiles to the buildings based on external Excel data.
        
    drop_unwanted():
        Removes buildings that do not have a load profile.
        
    add_power():
        Adds a power attribute to the buildings based on the heat attribute and full load hours.
        
    extract_year(date_str):
        Extracts the year from a date string.
        
    add_BAK(bins, labels):
        Classifies buildings into age groups based on the provided bins and labels.
        
    add_LANUV_age_and_type():
        Extracts building age and type from the 'GEBAEUDETY' attribute and adds them as new columns.
        
    merge_buildings():
        Merges building geometries and attributes, performing custom aggregations.
        
    add_custom_heat_demand(building_data):
        Adds custom heat demand data to the existing GeoDataFrame based on building characteristics.
    '''
    def __init__(self, path, heat_att):
        '''
         Initializes the Buildings_adj class with a GeoDataFrame of building geometries and attributes.

        Parameters
        ----------
        path : str
            The file path to the shapefile containing the building geometries.
        heat_att : str
            The attribute name for heat data.
        '''
        self.gdf = gpd.read_file(path)
        self.heat_att = heat_att

    def add_Vlh_Loadprofile(self, excel_data):
        '''
        Adds full load hours and load profiles to the buildings.

        This method merges the building data with external Excel data containing full load hours (Volllaststunden Vlh)
        and load profiles based on the 'citygml_fu' attribute of the buildings.

        Parameters
        ----------
        excel_data : DataFrame
            A DataFrame containing the load profile data with 'Funktion', 'Lastprofil', and 'Vlh' columns.
        '''
        buildings = self.gdf
        excel_data['Funktion'] = excel_data['Funktion'].astype(str)
        buildings['GFK_last_four'] = buildings['citygml_fu'].str[-4:]
        buildings = buildings.merge(excel_data[['Funktion', 'Lastprofil', 'Vlh']], left_on='GFK_last_four', right_on='Funktion', how='left')

        # Delete the temporary column and the 'Funktion' column
        buildings.drop(columns=['GFK_last_four'], inplace=True)

        try:
            buildings.drop(columns=['Funktion'], inplace=True)
        except:
            buildings.drop(columns=['Funktion_y'], inplace=True)

        # EFH and MFH share the same ALKIS-function 1010
        buildings['Lastprofil'] = np.where(
            (buildings['Lastprofil'] == 'EFH') & (buildings['type'] != 'EFH'),
            'MFH',
            buildings['Lastprofil']
        )

        self.gdf = buildings

    def drop_unwanted(self):
        '''
        Drops buildings that do not have a load profile.

        This method removes all buildings that do not have a load profile, as these are buildings that
        are not needed or have other issues.
        '''
        b = self.gdf
        b = b[b['Lastprofil'].notna()]
        b = b.copy() # Suppress a false warning
        self.gdf = b

    def add_power(self):
        '''
        Adds a power attribute to the buildings.

        This method calculates the power attribute for each building based on the heat attribute and full load hours.
        If full load hours (Vlh) are zero, it uses a default value of 1600.
        '''
        buildings = self.gdf
        buildings['power_th'] = buildings[self.heat_att] / buildings['Vlh'].where(buildings['Vlh'] != 0, 1600) # Default to 1600 if Vlh is 0
        self.gdf = buildings
    
    @staticmethod
    def extract_year(date_str):
        '''
        Extracts the year from a date string.

        This method extracts the year as an integer from the beginning of a date string. If the date string
        is NaN, it returns NaN.

        Parameters
        ----------
        date_str : str
            The date string from which to extract the year.

        Returns
        -------
        int or float
            The extracted year or NaN if the date string is NaN.

        Examples
        --------
        >>> Buildings_adj.extract_year("2023-07-17")
        2023
        >>> Buildings_adj.extract_year(None)
        nan
        '''
        
        #if pd.notna(date_str):
        #    return int(date_str[:4])
        #return np.nan#
    
        if pd.isna(date_str):
            return np.nan

        ## Wenn es bereits ein pandas.Timestamp oder datetime ist
        if hasattr(date_str, "year"):
            return int(date_str.year)

        # Falls es ein String ist
        try:
            return int(str(date_str)[:4])
        except Exception:
            return np.nan

    def add_BAK(self,bins,labels):
        '''
        Adds building age classification based on the provided bins and labels.

        This method classifies buildings into age groups based on the 'validFrom' attribute using the
        provided bins and labels.

        Parameters
        ----------
        bins : list of int
            The bin edges for classifying buildings by age.
        labels : list of str
            The labels for the age bins.

        Examples
        --------
        >>> bins = [1800, 1900, 1950, 2000, 2024]
        >>> labels = ["1800-1899", "1900-1949", "1950-1999", "2000-2024"]
        '''
        # Convert the validFrom attribute to year
        self.gdf['jahr'] = self.gdf['validFrom'].apply(self.extract_year)

        # Classify buildings into age groups (Baualtersklassen BAK)
        self.gdf['BAK'] = pd.cut(self.gdf['jahr'], bins=bins, labels=labels, right=True)
        self.gdf['BAK'] = self.gdf['BAK'].astype(str)
        self.gdf.drop(columns=['jahr'], inplace = True)

    def add_LANUV_age_and_type(self):
        ''' 
        This method extracts the building age and type from the 'GEBAEUDETY' attribute and adds it as two new columns.
        '''
        self.gdf[['type', 'age_LANUV']] = self.gdf['GEBAEUDETY'].str.split('_', expand=True)

        # set type = NWG (Nichtwohngebaeude) for all NWG 
        self.gdf.loc[self.gdf['WG_NWG'] == 'NWG', 'type'] = 'NWG'

    def merge_buildings(self):
        '''
        Merges building geometries and attributes, performing custom aggregations.

        This method dissolves the building geometries based on 'Flurstueck', 'citygml_fu', and 'Fortschrei'
        attributes and performs custom aggregations on the attributes.
        '''

        # Aggregation functions
        def custom_agg_mix_str(s):
            '''
            Aggregates string attributes by returning the unique value or 'mix' if there are multiple unique values.

            Parameters
            ----------
            s : Series
                The series to aggregate.

            Returns
            -------
            str
                The aggregated value.
            '''
            unique_vals = s.unique()
            if len(unique_vals) == 1:
                return unique_vals[0]
            else:
                return 'mix'
            
        def custom_agg_mix_numeric(s):
            '''
            Aggregates numeric attributes by returning the unique value or None if there are multiple unique values.

            Parameters
            ----------
            s : Series
                The series to aggregate.

            Returns
            -------
            int, float, or None
                The aggregated value.
            '''
            unique_vals = s.unique()
            if len(unique_vals) == 1:
                return unique_vals[0]
            else:
                return None 
            
        def custom_agg_most_common(s):
            '''
            Aggregates by returning the most common value.

            Parameters
            ----------
            s : Series
                The series to aggregate.

            Returns
            -------
            int, float, or str
                The most common value.
            '''
            most_common = s.mode()
            if len(most_common) > 0:
                return most_common.iloc[0]
            else:
                return s.iloc[0]  # Fallback if no mode is found (should not occur in practice)

        def mode_or_string(x):
            ''' 
            Aggregates by returning the most common value or a comma-separated string if there are ties.

            Parameters
            ----------
            x : Series
                The series to aggregate.

            Returns
            -------
            str
                The aggregated value.
            '''
            counts = Counter(x)
            max_count = max(counts.values())
            max_list = [val for val, count in counts.items() if count == max_count]
            if len(max_list) == 1:
                return str(max_list[0])
            else:
                sorted_list = sorted(max_list)
                return ', '.join(map(str, sorted_list))
            
        def weighted_average(s, weights):
            '''
            Calculates the weighted average.

            Parameters
            ----------
            s : Series
                Series of values (e.g., RW_spez).
            weights : Series
                Series of weights (e.g., NF).

            Returns
            -------
            float
                The weighted average.
            '''
            return (s * weights).sum() / weights.sum()
           
        grouped_gdf = self.gdf.dissolve(
            by=['Flurstueck', 'citygml_fu', 'Fortschrei', 'type'], 
            as_index=False, 
            aggfunc={
            'Fest_ID': 'first', 
            'Nutzung': 'first', 
            'NF': 'sum', 
            'RW_spez': lambda x: weighted_average(x, self.gdf.loc[x.index, 'NF']),
            'RW': 'sum',
            'WW_spez': lambda x: weighted_average(x, self.gdf.loc[x.index, 'NF']),
            'WW': 'sum',
            'RW_WW_spez': lambda x: weighted_average(x, self.gdf.loc[x.index, 'NF']),
            'RW_WW': 'sum',
            'age_LANUV': mode_or_string,
            })
        self.gdf = grouped_gdf
    
    def add_custom_heat_demand(self, wg_data, nwg_data):
        '''
        Adds custom heat demand data to the existing GeoDataFrame based on building characteristics from two datasets.

        This method merges the existing GeoDataFrame with two external DataFrames (`wg_data` and `nwg_data`) to assign
        specific heat demand values for each building type (e.g., MFH or EFH) or function. The specific heat demand 
        values are used to calculate the total heat demand for each building.

        Parameters
        ----------
        wg_data : pd.DataFrame
            A DataFrame containing building-specific heat demand data. It must include the following columns:
            - 'Baualtersklasse': Building age class.
            - 'Waerme_MFH kWh/m²·a': Specific heat demand for multi-family houses (MFH) in kWh/m²·a.
            - 'Waerme_EFH kWh/m²·a': Specific heat demand for single-family houses (EFH) in kWh/m²·a.
        
        nwg_data : pd.DataFrame
            A DataFrame containing additional building data. It must include the following columns:
            - 'Funktion': Function classification of the building.
            - 'WVBRpEBF': Specific heat demand value based on the building function.
        
        Notes
        -----
        The method assumes that 'Lastprofil' in the GeoDataFrame specifies the building type as either 'MFH' or 'EFH'.
        Buildings not classified as 'MFH' or 'EFH' will receive their heat demand value from the 'WVBRpEBF' column in 
        `nwg_data`. If 'WVBRpEBF' is not available, the resulting demand will be NaN.

        The total heat demand is calculated by multiplying the net floor area ('NF') by the assigned specific heat demand.
        '''
        buildings = self.gdf
        # merge with wg_data
        merge1 = buildings.merge(
            wg_data[['Baualtersklasse', 'Waerme_MFH kWh/m²·a', 'Waerme_EFH kWh/m²·a']],
            left_on='BAK',
            right_on='Baualtersklasse',
            how='left'
        )

        # merge with nwg_data
        merge1['GFK_last_four'] = merge1['citygml_fu'].str[-4:]
        merged_df = merge1.merge(
            nwg_data[['Funktion', 'WVBRpEBF']],
            left_on='GFK_last_four',
            right_on='Funktion',
            how='left'
        )

        # Conditional assignment of specific heat demands
        merged_df['Spez_Waermebedarf'] = np.where(
            merged_df['Lastprofil'] == 'MFH',
            merged_df['Waerme_MFH kWh/m²·a'],
            np.where(
                merged_df['Lastprofil'] == 'EFH',
                merged_df['Waerme_EFH kWh/m²·a'],
                merged_df['WVBRpEBF']
            )
        )
        # try to delete unwanted columns
        try:
            merged_df.drop(columns=['Baualtersklasse', 'Waerme_MFH kWh/m²·a', 'Waerme_EFH kWh/m²·a', 'Funktion', 'WVBRpEBF', 'GFK_last_four'], inplace=True)
        except:
            pass
        # calculate 'Waermebedarf'
        merged_df['Waermebedarf'] = merged_df['NF'] * merged_df['Spez_Waermebedarf']
        self.gdf = merged_df

    def add_connect_option(self):
        buildings = self.gdf
        buildings['Anschluss'] = 1

    def rename_and_order_columns(self):
        '''renames and order the columns of the buildings data frame.'''
        old_df = self.gdf

        buildings = pd.DataFrame({
            'new_ID': old_df['new_ID'],
            'Anschluss': old_df['Anschluss'],
            'Funktion': old_df['citygml_fu'],
            'Nutzung': old_df['Nutzung'],
            'typ': old_df['type'],
            'NF [m²]': old_df['NF'],
            'RW_spez [kWh/a*m²]': old_df['RW_spez'],
            'RW [kWh/a]': old_df['RW'],
            'WW_spez [kWh/a*m²]': old_df['WW_spez'],
            'WW [kWh/a]': old_df['WW'],
            'RW_WW_spez [kWh/a*m²]': old_df['RW_WW_spez'],
            'RW_WW [kWh/a]': old_df['RW_WW'],
            'Leistung_th [kW]': old_df['power_th'],
            'Vlh [h]': old_df['Vlh'],
            'Lastprofil': old_df['Lastprofil'],
            'Alter_LANUV': old_df['age_LANUV'],
            #'Alter_Flurstueck': old_df['validFrom'].str[:4],
            'Alter_Flurstueck': pd.to_datetime(old_df['validFrom'], errors='coerce').dt.year,
            'BAK nach Flurstueck': old_df['BAK'],
            'Spez_WB [kWh/a*m²]': old_df['Spez_Waermebedarf'],
            'WB [kWh/a]': old_df['Waermebedarf'],
            'geometry': old_df['geometry']
        })

        # change into geodataframe
        buildings = gpd.GeoDataFrame(buildings, geometry='geometry', crs=old_df.crs)

        self.gdf = buildings

class Parcels_adj():
    '''
    A class used to represent and manipulate parcel geometries.

    This class provides a method to initialize a GeoDataFrame of parcel geometries from a shapefile.

    Attributes
    ----------
    gdf : GeoDataFrame
        A GeoDataFrame containing the parcel geometries.

    Methods
    -------
    __init__(path):
        Initializes the Parcels_adj class with a GeoDataFrame of parcel geometries.
    '''
    def __init__(self, path):
        '''
        Initializes the Parcels_adj class with a GeoDataFrame of parcel geometries.

        Parameters
        ----------
        path : str
            The file path to the shapefile containing the parcel geometries.
        '''
        self.gdf = gpd.read_file(path)

def spatial_join(shape1, shape2, attributes):
    '''
    Performs a spatial join to add attributes from shape2 to the best fitting feature in shape1.

    This function finds the best fitting feature in `shape2` that intersects with each feature in `shape1` 
    based on the intersection area. It then adds the specified attributes from `shape2` to `shape1`.

    Parameters
    ----------
    shape1 : GeoDataFrame
        The GeoDataFrame to which attributes will be added.
    shape2 : GeoDataFrame
        The GeoDataFrame from which attributes will be sourced.
    attributes : list of str
        List of attribute names to be transferred from `shape2` to `shape1`.

    Returns
    -------
    GeoDataFrame
        The updated `shape1` GeoDataFrame with the specified attributes added from `shape2`.

    Notes
    -----
    If columns named 'index_left' or 'index_right' exist in either `shape1` or `shape2`, 
    they will be removed to avoid conflicts during the spatial join.

    If an attribute specified in the `attributes` list does not exist in `shape2`, the function 
    will attempt to use a column named `{attribute}_left` instead and will print a message 
    indicating the update.

    Examples
    --------
    >>> shape1 = gpd.read_file("path/to/shape1.shp")
    >>> shape2 = gpd.read_file("path/to/shape2.shp")
    >>> attributes = ["attr1", "attr2"]
    >>> updated_shape1 = spatial_join(shape1, shape2, attributes)
    '''
    # Überprüfen, ob Spalten index_left und index_right vorhanden sind und sie gegebenenfalls entfernen
    if 'index_left' in shape1.columns:
        shape1 = shape1.drop(columns=['index_left'])
        print('index_left was removed from shape1 to execute the spatial join')
    if 'index_right' in shape1.columns:
        shape1 = shape1.drop(columns=['index_right'])
        print('index_right was removed from shape1 to execute the spatial join')
    if 'index_left' in shape2.columns:
        shape2 = shape2.drop(columns=['index_left'])
        print('index_left was removed from shape2 to execute the spatial join')
    if 'index_right' in shape2.columns:
        shape2 = shape2.drop(columns=['index_right'])
        print('index_right was removed from shape2 to execute the spatial join')

    # Räumlichen Join durchführen
    joined = gpd.sjoin(shape1, shape2, how='inner', predicate='intersects')

    # Schnittfläche für jedes überlappende Paar berechnen
    joined['intersection_area'] = joined.apply(lambda row: shape1.geometry.iloc[row.name].intersection(shape2.geometry.iloc[row['index_right']]).area, axis=1)

    # Ergebnisse basierend auf der Schnittfläche sortieren
    sorted_joined = joined.sort_values(by='intersection_area', ascending=False)

    # Den Eintrag mit der größten Schnittfläche für jedes Gebäude-Feature behalten
    max_intersection = sorted_joined.groupby(sorted_joined.index).first()

    # Attribute übertragen
    for attr in attributes:
        try:
            shape1[attr] = max_intersection[attr]
        except:
            shape1[attr] = max_intersection[(attr+'_left')]
            print(f'{attr} got updated during spatial join')
    return shape1