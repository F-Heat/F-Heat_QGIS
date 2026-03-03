import numpy as np
import pandas as pd
import geopandas as gpd

class WLD:
    '''
    A class to manage the relationship between buildings and streets, including adding centroids, 
    finding the closest street for each building, and calculating heat attributes.

    Attributes
    ----------
    buildings : GeoDataFrame
        A GeoDataFrame containing building geometries and attributes.
    streets : GeoDataFrame
        A GeoDataFrame containing street geometries and attributes.

    Methods
    -------
    get_centroid():
        Adds the centroid of each building to the buildings GeoDataFrame.
    closest_street_buildings():
        Finds the nearest street for each building based on the centroid and assigns a street ID.
    add_length():
        Adds a column for the length of each street segment to the streets GeoDataFrame.
    add_heat_att(heat_att):
        Adds heat consumption attributes to each street based on connected buildings.
    add_WLD(heat_att):
        Calculates and adds the heat line density (Wärmeliniendichte) to each street segment.
    '''

    def __init__(self,buildings,streets):
        '''
        Initializes the WLD class with buildings and streets GeoDataFrames.

        Parameters
        ----------
        buildings : GeoDataFrame
            A GeoDataFrame containing building geometries and attributes.
        streets : GeoDataFrame
            A GeoDataFrame containing street geometries and attributes.
        '''
        self.buildings = buildings
        self.streets = streets

    def get_centroid(self):
        '''
        Adds the centroid of each building to the buildings GeoDataFrame.
        '''
        self.buildings['centroid'] = self.buildings['geometry'].centroid

    def closest_street_buildings(self):
        '''
        Finds the nearest street for each building based on the centroid and assigns a street ID.
        
        This method iterates over each building's centroid, finds the nearest street segment,
        and records the street ID in the buildings GeoDataFrame.
        '''
        for index, row in self.buildings.iterrows():
            centroid = row['centroid']
            closest_line = self.streets.geometry.distance(centroid).idxmin()
            self.buildings.at[index, 'street_id'] = int(closest_line)

    def add_lenght(self):
        '''
        Adds a column for the length of each street segment to the streets GeoDataFrame.
        '''
        self.streets['length'] = self.streets['geometry'].length

    def add_heat_att(self,heat_att):
        '''
        Adds heat consumption attributes to each street based on connected buildings.

        Parameters
        ----------
        heat_att : str
            The attribute in the buildings GeoDataFrame representing heat consumption.
        '''
        self.streets['connected'] = [[] for _ in range(len(self.streets))]
        self.streets[f'{heat_att}'] = 0

        for idx, row in self.buildings.iterrows():
            heat_demand = row[heat_att]
            id = row['street_id']
            
            self.streets.loc[id, f'{heat_att}'] += heat_demand
            self.streets.at[id, 'connected'].append(row['new_ID'])
            
        # Convert the list of polygons to a comma-separated string: [123, 456, 789] >>> "123,456,789"
        self.streets['connected'] = self.streets['connected'].apply(lambda x: ','.join(map(str, x)))
        

    def add_WLD(self, heat_att):
        '''
        Calculates and adds the heat line density (Wärmeliniendichte) to each street segment.

        Parameters
        ----------
        heat_att : str
            The attribute in the streets GeoDataFrame representing heat consumption.
        '''
        self.streets['WLD [kWh/a*m]'] = np.where(
            self.streets['length'] != 0, self.streets[f'{heat_att}'] / self.streets['length'], np.nan)
    
    def rename_columns(self):
        '''
        renames columns of self.streets.
        '''
        rename_dict = {
            'length': 'Laenge',
            'connected': 'angeschlossen'
        }
        self.streets = self.streets.rename(columns=rename_dict)
        
class Polygons:
    '''
    A class to process parcels, heat line density (Wärmeliniendichte WLD), and building data.

    Attributes
    ----------
    parcels : GeoDataFrame
        GeoDataFrame of parcels.
    wld : GeoDataFrame
        GeoDataFrame of heat line density.
    buildings : GeoDataFrame
        GeoDataFrame of buildings.
    '''

    def __init__(self, parcels, wld, buildings):
        '''
        Initializes the Polygons class with the given parcels, WLD, and building data.

        Parameters
        ----------
        parcels : GeoDataFrame
            GeoDataFrame of parcels.
        wld : GeoDataFrame
            GeoDataFrame of heat line density.
        buildings : GeoDataFrame
            GeoDataFrame of buildings.
        '''
        self.parcels = parcels
        self.wld = wld
        self.buildings = buildings
    
    def select_parcels_by_building_connection(self, WLD_value):
        '''
        Selects parcels based on connected buildings and a WLD threshold.

        Parameters
        ----------
        WLD_value : float
            Threshold value of heat line density (Waermeliniendichte WLD).
        '''
        # Filter WLD for values > WLD_value
        filtered_wld = self.wld[self.wld['WLD [kWh/a*m]']>= WLD_value] 

        # Extract all connected building IDs from the 'connected' column
        connected_building_ids = [int(id) for sublist in filtered_wld['connected'].dropna().str.split(',').tolist() if isinstance(sublist, list) for id in sublist]

        # Select buildings that are in the list of connected building IDs
        connected_buildings = self.buildings[self.buildings['new_ID'].isin(connected_building_ids)].copy()

        # Calculate area of building footprint
        connected_buildings['building_area'] = connected_buildings.geometry.area

        # Remove index_left and index_right from the dataframes
        if 'index_left' in self.parcels.columns:
            self.parcels = self.parcels.drop(columns=['index_left'])
        if 'index_right' in self.parcels.columns:
            self.parcels = self.parcels.drop(columns=['index_right'])

        if 'index_left' in connected_buildings.columns:
            connected_buildings = connected_buildings.drop(columns=['index_left'])
        if 'index_right' in connected_buildings.columns:
            connected_buildings = connected_buildings.drop(columns=['index_right'])

        # Add identifier to remove duplicates
        self.parcels['identifier'] = range(len(self.parcels))

        # Perform spatial join: check which parcels touch buildings
        join_result = gpd.sjoin(self.parcels, connected_buildings, how="inner", predicate="intersects")

        # Calculate area of overlap between parcels and buildings
        if join_result.empty:
            join_result['overlap_area'] = 0.0
        else:
            join_result = join_result.dropna(subset=['index_right']).copy()
            join_result['index_right'] = join_result['index_right'].astype(int)
            join_result['overlap_area'] = join_result.apply(
                lambda row: self.parcels.geometry.loc[row.name].intersection(
                    connected_buildings.geometry.loc[row['index_right']]
                ).area,
                axis=1,
            )
        
        # Calculate coverage ratio
        join_result['coverage_ratio'] = join_result['overlap_area'] / join_result['building_area']

        # Sort by coverage_ratio descending
        sorted_joined = join_result.sort_values(by='coverage_ratio', ascending=False)

        # --- Primary: parcel-centric selection (>= 10 % footprint coverage) ---
        max_coverage_by_parcel = sorted_joined.groupby(sorted_joined.index).first()
        selected_by_parcel = max_coverage_by_parcel[max_coverage_by_parcel['coverage_ratio'] >= 0.1]

        # --- Fallback: centroid-based selection for buildings not yet represented ---
        # MultiPolygon buildings that span parcel boundaries never achieve >= 10 % per parcel.
        # Use the building centroid to identify the containing parcel and add that row directly,
        # without any coverage threshold.  Downstream dissolve() merges duplicate parcel geometries.
        already_covered_ids = set(selected_by_parcel['new_ID'].dropna())
        missing_ids = set(connected_buildings['new_ID']) - already_covered_ids

        fallback_rows = gpd.GeoDataFrame()
        if missing_ids and 'centroid' in self.buildings.columns:
            missing_buildings = connected_buildings[connected_buildings['new_ID'].isin(missing_ids)].copy()
            centroids_gdf = missing_buildings.set_geometry('centroid')

            # Find which parcel each missing building's centroid falls within
            centroid_join = gpd.sjoin(
                centroids_gdf[[centroids_gdf.geometry.name, 'new_ID']],
                self.parcels[['geometry', 'identifier']],
                how='left',
                predicate='within',
            )
            centroid_join = centroid_join[centroid_join['index_right'].notna()]

            # For each missing building pick the row from join_result with the
            # best matching parcel (centroid-parcel preferred, else highest coverage)
            centroid_parcel_map = (
                centroid_join.drop_duplicates(subset='new_ID', keep='first')[['new_ID', 'index_right']]
                .set_index('new_ID')['index_right']
                .astype(int)
                .to_dict()
            )

            collected = []
            for bid, parcel_idx in centroid_parcel_map.items():
                # Prefer the row from join_result where new_ID == bid and parcel == parcel_idx
                mask = (join_result['new_ID'] == bid) & (join_result.index == parcel_idx)
                candidate = join_result[mask]
                if candidate.empty:
                    # Fall back to any row for this building (highest coverage)
                    candidate = sorted_joined[sorted_joined['new_ID'] == bid].head(1)
                else:
                    candidate = candidate.head(1)
                collected.append(candidate)

            if collected:
                fallback_rows = gpd.GeoDataFrame(pd.concat(collected))
                # Ensure CRS matches the main selection
                if fallback_rows.crs is None and not selected_by_parcel.empty:
                    fallback_rows = fallback_rows.set_crs(selected_by_parcel.crs)

        # Combine: allow same parcel to appear multiple times for different buildings.
        # Downstream buffer_dissolve_and_explode uses only geometry, so duplicates are fine.
        if not fallback_rows.empty:
            selected_parcels = gpd.GeoDataFrame(pd.concat([selected_by_parcel, fallback_rows]))
        else:
            selected_parcels = selected_by_parcel

        # Remove 'centroid' column
        if 'centroid' in selected_parcels.columns:
            selected_parcels = selected_parcels.drop(columns=['centroid'])
        
        self.selected_parcels = selected_parcels

    def buffer_dissolve_and_explode(self, buffer_distance):
        """
        Creates a buffer around the polygons, dissolves them, and explodes multipolygons into their components.
        
        Parameters
        ----------
        buffer_distance : float
            Distance of the buffer in meters.
        """
        # define crs
        crs = self.buildings.crs

        # Buffer
        self.selected_parcels['geometry'] = self.selected_parcels.buffer(buffer_distance)
        
        # Dissolving all Polygons
        dissolved = self.selected_parcels.dissolve()

        # explode multipolygons
        exploded = dissolved.explode(index_parts=True).reset_index(drop=True)

        # set crs
        exploded = exploded.set_crs(crs, allow_override=True)

        # remove all attributes 
        self.polygons = exploded[['geometry']]

    def add_attributes(self,heat_attribute, power_attribute):
        '''
        Adds attributes like the number of connections, heat demand, and power to the polygons.
        
        Parameters
        ----------
        heat_attribute : str
            Name of the heat demand attribute.
        power_attribute : str
            Name of the power attribute.
        '''
        # only buildings with heat demand
        buildings = self.buildings[self.buildings[heat_attribute]>0] 

        # add area
        self.polygons['Area [m²]'] = self.polygons['geometry'].area

        # add columns for attributes
        self.polygons['Connections'] = 0
        self.polygons['Heat_Demand [kWh/a]'] = 0.0
        self.polygons['Power_th [kW]'] = 0.0

        for idx, polygon in self.polygons.iterrows():
            # buildings within polygon
            contained_buildings = buildings[buildings.geometry.within(polygon.geometry)]

            # connections in polygon
            self.polygons.loc[idx, 'Connections'] = len(contained_buildings)

            # cumulated heat demand
            self.polygons.loc[idx, 'Heat_Demand [kWh/a]'] = contained_buildings[heat_attribute].sum()
            
            # accumulated power
            self.polygons.loc[idx,'Power_th [kW]'] = contained_buildings[power_attribute].sum()
        
        # heat deman per area 
        self.polygons['Demand/Area [MWh/ha*a]'] = 10 * self.polygons['Heat_Demand [kWh/a]'] / self.polygons['Area [m²]'] # 1000 kW 10000 m^2 in 1 MW 1 ha
        
        # mean power
        self.polygons['Mean_Power_th [kW]'] = self.polygons['Power_th [kW]'] / self.polygons['Connections']
    
    def rename_columns(self):
        '''
        renames columns of self.polygons.
        '''
        rename_dict = {
            'Area [m²]': 'Flaeche [m²]',
            'Connections': 'Anschluesse',
            'Heat_Demand [kWh/a]': 'Waermebedarf [kWh/a]',
            'Power_th [kW]': 'Thermische Leistung [kW]',
            'Demand/Area [MWh/ha*a]': 'Waermebedarf/Flaeche [MWh/ha*a]',
            'Mean_Power_th [kW]': 'Mittlere thermische Leistung [kW]'
        }
        self.polygons = self.polygons.rename(columns=rename_dict)