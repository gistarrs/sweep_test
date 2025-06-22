from datetime import datetime, date
from typing import Union, Optional, List, Dict, Any, Literal
from urllib.parse import quote

import geopandas as gpd
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import requests
from shapely.geometry import box
import shapely.wkt as wkt
from shapely.wkt import dumps, loads

from sweep import config

class GetParcels:
    def __init__(self, aoi_source: Union[str, gpd.GeoDataFrame], api_key: str, crs: str = 'EPSG:4269') -> None:
        """
        Initializes GetParcels instance.

        Args:
            aoi_source (str | gpd.GeoDataFrame): Path to AOI file or a GeoDataFrame representing the AOI.
            api_key (str): API key for the LightBox API.
            crs (str, optional): Coordinate reference system to use. Defaults to 'EPSG:4269'.

        Raises:
            TypeError: If `aoi_source` is neither a string nor a GeoDataFrame.
        """
        
        self.crs = crs
        self.api_key = api_key
        self.parcel_url = config.lightbox_url_template

        if isinstance(aoi_source, str):
            self.aoi_path = aoi_source
            self.aoi_gdf = self._read_aoi_layer()
        elif isinstance(aoi_source, gpd.GeoDataFrame):
            self.aoi_gdf = aoi_source
            if self.aoi_gdf.crs != self.crs:
                self.aoi_gdf = self.aoi_gdf.to_crs(self.crs)
        else:
            raise TypeError("aoi_source must be a path (str) or a GeoDataFrame.")

    def _read_aoi_layer(self):
        """
        Reads the AOI layer from a file path into a GeoDataFrame.

        Returns:
            gpd.GeoDataFrame: AOI layer as GeoDataFrame in the specified CRS.
        """

        aoi_gdf = gpd.read_file(self.aoi_path, engine="pyogrio", layer=None)
        print(f"AOI layer read from {self.aoi_path}.")

        if aoi_gdf.crs != self.crs:
            aoi_gdf = aoi_gdf.to_crs(self.crs)
        return aoi_gdf
    def _fetch_lightbox_parcels(self, query_type = "parcels", limit=500):
        """
        Fetch parcel features from the LightBox API for the AOI's WKT polygon.

        Args:
            query_type (str, optional): The type of query, defaults to "parcels".
            limit (int, optional): Number of records to fetch per page, defaults to 500.

        Returns:
            List[Dict[str, Any]]: List of parcel JSON features.

        Raises:
            RuntimeError: If a request to the API returns a non-200 status code.
        """

        #url = f"https://api.lightboxre.com/v1/{query_type}/us/geometry"
        
        url = self.parcel_url.format(query_type=query_type)
        print(url)

        headers = {
            "accept": "application/json",
            "x-api-key": self.api_key
        }

        offset = 0
        all_features = []

        try:
            while True:
                params = {
                    "wkt": self.aoi_wkt,
                    "bufferDistance": "0",
                    "bufferUnit": "m",
                    "limit": str(limit),
                    "offset": str(offset)
                }

                response = requests.get(url, headers=headers, params=params)

                #print(f"Offset: {offset}, Limit: {limit}")
                # print(f"Request URL: {response.url}")
                print(f"Offset: {offset}, Limit: {limit}, Status code: {response.status_code}")

                if response.status_code != 200:
                    raise RuntimeError(f"Request failed: {response.status_code} - {response.text}")

                data = response.json()
                features = data.get(query_type, [])
                all_features.extend(features)

                if len(features) < limit:
                    break  # Last page
                offset += limit

        except Exception as e:
            print(f"⚠️ Request failed at offset {offset}: {e}")
            print(f"✅ Returning {len(all_features)} records fetched before failure.")

        return all_features
   
    def _json_to_gdf(self, features, crs=None):
        """
        Converts a list of JSON parcel features into a GeoDataFrame.

        Args:
            features (List[Dict[str, Any]]): List of JSON features.
            crs (str, optional): Coordinate reference system. Defaults to self.crs.

        Returns:
            gpd.GeoDataFrame: GeoDataFrame with geometries and flattened attribute columns.
        """

        if crs is None:
            crs = self.crs

        records = []
        geometries = []

        for feature in features:
            try:
                geometry_wkt = feature["location"]["geometry"]["wkt"]
                geometry = wkt.loads(geometry_wkt)
                flat_record = self._flatten_dict(feature)  # Use the new flatten function here
                records.append(flat_record)
                geometries.append(geometry)
            except Exception as e:
                print(f"Skipping record due to error: {e}")
                continue

        df = pd.DataFrame(records)
        gdf = gpd.GeoDataFrame(df, geometry=geometries, crs=crs)
        return gdf

    def _flatten_dict(self, d, parent_key='', sep='_'):
        """
        Recursively flattens a nested dictionary.

        Args:
            d (Dict[str, Any]): Dictionary to flatten.
            parent_key (str, optional): Prefix for keys. Defaults to ''.
            sep (str, optional): Separator between keys. Defaults to '_'.

        Returns:
            Dict[str, Any]: Flattened dictionary.
        """

        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(self._flatten_dict(v, new_key, sep=sep).items())
            elif isinstance(v, list):
                items.append((new_key, str(v)))  # convert lists to strings
            else:
                items.append((new_key, v))
        return dict(items)
    def fetch_parcels_for_aoi(
        self,
        query_type: Literal["parcels", "assessments"] = "parcels",
        limit: int = 500
    ) -> gpd.GeoDataFrame:
        """
        Loops over each geometry in the AOI GeoDataFrame, fetches parcels for each, clips results,
        and combines all into a single GeoDataFrame.

        Args:
            query_type (Literal["parcels", "assessments"], optional): Type of data to fetch.
                Either "parcels" or "assessments". Defaults to "parcels".
            limit (int, optional): Number of records to fetch per request. Defaults to 500.
            
        Returns:
            pd.GeoDataFrame: Combined GeoDataFrame of all fetched parcels clipped to AOI geometries.
        """

        all_gdfs = []

        for idx, row in self.aoi_gdf.iterrows():
            try:
                geom = row.geometry
                minx, miny, maxx, maxy = geom.bounds
                geom_wkt = dumps(box(minx, miny, maxx, maxy))

                # Temporarily assign this WKT to the instance
                self.aoi_wkt = geom_wkt

                features = self._fetch_lightbox_parcels(query_type=query_type, limit=limit)
                gdf = self._json_to_gdf(features)

                # Clip parcels by the original AOI geometry for precision
                gdf_clipped = gpd.clip(gdf, geom)

                gdf_clipped["aoi_index"] = idx
                for col in self.aoi_gdf.columns:
                    if col != "geometry":
                        gdf_clipped[f"aoi_{col}"] = row[col]

                all_gdfs.append(gdf_clipped)

            except Exception as e:
                print(f"❌ Failed on AOI index {idx}: {e}")
                continue

        if all_gdfs:
            return gpd.GeoDataFrame(pd.concat(all_gdfs, ignore_index=True), crs=self.crs)
        else:
            print("⚠️ No parcels fetched.")
            return gpd.GeoDataFrame(columns=["geometry"], crs=self.crs)

class ParcelHandler:
    def __init__(self, 
                 aoi_source: Union[str, gpd.GeoDataFrame], 
                 parcel_gdf: gpd.GeoDataFrame, 
                 assmt_gdf: gpd.GeoDataFrame, 
                 crs: str = 'EPSG:3310') -> None:
        """
        Initializes the ParcelHandler with AOI source, parcel and assessment GeoDataFrames.
        
        Args:
            aoi_source (Union[str, gpd.GeoDataFrame]): File path to AOI layer or AOI GeoDataFrame.
            parcel_gdf (gpd.GeoDataFrame): GeoDataFrame of parcels.
            assmt_gdf (gpd.GeoDataFrame): GeoDataFrame of assessments.
            crs (str): Coordinate Reference System to use (default 'EPSG:3310').
        
        Raises:
            TypeError: If `aoi_source` is not a string or GeoDataFrame.
        """

        self.parcel_gdf = parcel_gdf
        self.assmt_gdf = assmt_gdf
        self.crs = crs
        
        if isinstance(aoi_source, str):
            self.aoi_path = aoi_source
            self.aoi_gdf = self._read_aoi_layer()
        elif isinstance(aoi_source, gpd.GeoDataFrame):
            self.aoi_gdf = aoi_source
            if self.aoi_gdf.crs != self.crs:
                self.aoi_gdf = self.aoi_gdf.to_crs(self.crs)
        else:
            raise TypeError("aoi_source must be a path (str) or a GeoDataFrame.")

    def _read_aoi_layer(self):
        """
        Reads the AOI layer from file and reprojects to target CRS if needed.
        
        Returns:
            gpd.GeoDataFrame: AOI layer as GeoDataFrame with correct CRS.
        """
        
        aoi_gdf = gpd.read_file(self.aoi_path, engine="pyogrio", layer=None)
        print(f"AOI layer read from {self.aoi_path}.")
        if aoi_gdf.crs != self.crs:
            aoi_gdf = aoi_gdf.to_crs(self.crs)
        return aoi_gdf

    def _clean_and_join(self):
        """
        Cleans and filters the parcel and assessment GeoDataFrames, then joins them on parcel ID.
        
        Returns:
            gpd.GeoDataFrame: Joined and cleaned GeoDataFrame.
        """

        keep_columns_parcels = [
            '$ref', 'id', '$metadata_geocode', 'fips', 'parcelApn', 'assessment_apn', 
            'census_blockGroup', 'census_tract', 'county', 'derived_calculatedLotArea', 
            'landUse_code', 'landUse_description', 'landUse_normalized_code', 
            'landUse_normalized_description', 'landUse_normalized_categoryDescription', 
            'location_streetAddress', 'location_countryCode', 'location_locality', 
            'location_regionCode', 'location_postalCode', 'occupant_owner', 
            'opportunityZone', 'primaryStructure_yearBuilt', 'primaryStructure_yearRenovated', 
            'primaryStructure_units', 'primaryStructure_livingArea', 'subdivision', 
            'structures', 'geometry'
        ]
        keep_columns_assmt = [
        '$ref', 'apn', 'id', 'parcel_$ref', 'parcel_id', '$metadata', 'assessedValue_total', 
        'assessedValue_year', 'assessedLotSize', 'lot_lotNumber', 'lot_blockNumber', 'zoning_assessment', 
        'transaction_multipleApnFlag', 'primaryStructure_stories_count', 'primaryStructure_yearBuilt', 'primaryStructure_buildingArea',
        'primaryStructure_units', 'primaryStructure_livingArea', 'primaryStructure_numberOfBuildings', 'geometry'
        ]

        existing_columns_parcels = [col for col in keep_columns_parcels if col in self.parcel_gdf.columns]
        missing_columns_parcels = [col for col in keep_columns_parcels if col not in self.parcel_gdf.columns]
        aoi_columns = [col for col in self.parcel_gdf.columns if col.startswith('aoi_')]
        columns_to_keep = list(dict.fromkeys(existing_columns_parcels + aoi_columns)) 

        parcel_gdf_abbr = self.parcel_gdf[columns_to_keep]
        if missing_columns_parcels:
            print(f"⚠️ These columns are missing and will not be included: {missing_columns_parcels}")

        existing_columns_assmt = [col for col in keep_columns_assmt if col in self.assmt_gdf.columns]
        missing_columns_assmt = [col for col in keep_columns_assmt if col not in self.assmt_gdf.columns]
        assmt_gdf_abbr = self.assmt_gdf[existing_columns_assmt]
        if missing_columns_assmt:
            print(f"⚠️ These columns are missing and will not be included: {missing_columns_assmt}")
        
        assmt_gdf_abbr = assmt_gdf_abbr.rename(columns={
            "geometry": "asst_geom", 
            "id" : "assmt_id",
            'primaryStructure_yearBuilt': 'assmt_yrblt',
            'primaryStructure_livingArea': 'assmt_livingarea',
            'id_y': 'assmt_id'})

        joined = pd.merge(
            parcel_gdf_abbr, 
            assmt_gdf_abbr,
            left_on= 'id',
            right_on='parcel_id', 
            how='left'
            )

        rename_dict = {
            'parcelApn': 'PARCEL_APN',
            'apn': 'ASSMT_APN',
            'fips': 'FIPS_CODE',
            'county': 'COUNTYNAME',
            'location_streetAddress': 'SITE_ADDR',
            'location_locality': 'SITE_CITY',
            'location_regionCode': 'SITE_STATE',
            'location_postalCode': 'SITE_ZIP',
            'location_postalCodeExt': 'SITE_PLUS_4',
            'census_tract': 'CENSUS_TRACT',
            'census_blockGroup': 'CENSUS_BLOCK_GROUP',       
            'landUse_code': 'USE_CODE_MUNI',
            'landUse_description': 'USE_CODE_MUNI_DESC',
            'landUse_normalized_code': 'USE_CODE_STD_LPS',
            'landUse_normalized_description': 'USE_CODE_STD_DESC_LPS',
            'assessment_zoning_assessment': 'Zoning',
            'primaryStructure_livingArea': 'LIVING_SQFT',
            'assmt_livingarea': 'ASSMT_SQFT',
            'primaryStructure_yearBuilt': 'YR_BLT',
            'assmt_yearBuilt': 'ASSMT_YRBLT',
            'primaryStructure_stories_count': 'STORIES_NUMBER',
            'primaryStructure_rooms': 'TOTAL_ROOMS',
            'primaryStructure_units': 'UNITS_NUMBER',
        }
        joined = joined.rename(columns = rename_dict)
        joined = joined.to_crs("EPSG:3310")
        joined['centroid'] = joined.geometry.centroid
        joined = joined[joined['LIVING_SQFT'].notna()]
        print("Parcel and assessment datasets joined and fields cleaned.")
        return(joined)

    def _clip_extent(self):
        """
        Clips the joined parcel and assessment GeoDataFrame to the AOI polygon(s) using a spatial join (API data uses bounding boxes for polygons.)
        
        Returns:
            gpd.GeoDataFrame: GeoDataFrame clipped to the AOI polygons.
        """
        joined = self._clean_and_join()

        # Spatial join to keep only points within the AOI polygon(s)
        gdf_within = gpd.sjoin(joined, self.aoi_gdf[['geometry']], predicate='within', how='inner')

        # Optional: drop the join index if you don't need it
        gdf_within = gdf_within.drop(columns=["index_right"])
        print("Joined dataset clipped to fire geometry.")
        return gdf_within

    def process_parcels(self):
        """
        Runs the full parcel processing pipeline: clean, join, and clip to AOI.
        
        Returns:
            gpd.GeoDataFrame: Processed parcels clipped to AOI.
        """
        return self._clip_extent()

class AOIProcessor:
    """
    A class to process AOI point data through three stages:
    1. Spatial join with COABDIS layer.
    2. Cleaning and formatting of columns.
    3. Adding synthetic damage data.

    Parameters:
    -----------
    coabdis_path : str
        Path to the COABDIS layer (GeoPackage, Shapefile, etc.). (default is relative path in config.py to data folder)
    cat_crosswalk : str
        Path to the category crosswalk CSV (default is relative path in config.py to data folder)
    run_date : str or datetime.date, optional
        Date to use for CLEAN_DATE column. If None, defaults to today.
    run_name : str, optional
        Name of the run used for INCIDENTNAME (if no INCIDENTNAME column present). Defaults to "SWEEP" + timestamp.
    """

    def __init__(self,
                 coabdis_path=config.coabdis_layer,
                 cat_crosswalk=config.category_crosswalk,
                 run_date=None,
                 run_name=None):
        self.coabdis_path = coabdis_path
        self.cat_crosswalk = cat_crosswalk
        self.run_date = self._parse_date(run_date)
        self.run_name = run_name or "SWEEP" + datetime.now().strftime("%Y%m%d%H%M")

    def _parse_date(self, run_date: Optional[Union[str, date]]) -> date:
        """
        Parses the run_date input to a datetime.date object.

        Parameters
        ----------
        run_date : Optional[Union[str, date]]
            Date input as a string in 'MM/DD/YYYY' format or a date object.
            If None, returns today's date.

        Returns
        -------
        date
            Parsed date object.
        """

        if run_date is None:
            return datetime.today().date()
        if isinstance(run_date, str):
            return datetime.strptime(run_date, "%m/%d/%Y").date()
        return run_date

    def _add_coabdis(self, aoi_points):
        """
        Filters AOI points and spatially joins them with the COABDIS layer.

        Parameters
        ----------
        aoi_points : gpd.GeoDataFrame
            Input AOI points with geometry and attribute data.

        Returns
        -------
        gpd.GeoDataFrame
            AOI points joined with COABDIS attributes.
        """

        aoi_points = aoi_points[aoi_points['LIVING_SQFT'].notna()]
        aoi_points = aoi_points[aoi_points['LIVING_SQFT'] > 0]

        coabdis = gpd.read_file(self.coabdis_path)
        if aoi_points.crs != coabdis.crs:
            coabdis = coabdis.to_crs(aoi_points.crs)

        if "index_right" in aoi_points.columns:
            aoi_points = aoi_points.drop(columns="index_right")

        aoi_coab = gpd.sjoin(
            aoi_points,
            coabdis,
            how="left",
            predicate="within"
        )
        aoi_coab = aoi_coab.rename(columns={
            "CO_NAME": "COUNTY"
        })

        #print(aoi_coab.columns)
        return aoi_coab

    def _clean_columns(self, aoi_points):
        """
        Standardizes column names, merges category crosswalk, adds metadata fields,
        and filters to important columns.

        Parameters
        ----------
        aoi_points : gpd.GeoDataFrame
            AOI points after spatial join.

        Returns
        -------
        gpd.GeoDataFrame
            Cleaned AOI points with standardized columns.
        """

        aoi_points.columns = aoi_points.columns.str.upper()

        codes = pd.read_csv(self.cat_crosswalk)
        codes.rename(columns={'USECODE_S': 'USE_CODE_STD_LPS'}, inplace=True)
        codes['USE_CODE_STD_LPS'] = codes['USE_CODE_STD_LPS'].astype(str).str.split('.').str[0]

        aoi_points = pd.merge(aoi_points, codes, on='USE_CODE_STD_LPS', how='left')
        aoi_points['CAT'] = aoi_points['PARCEL_CAT']

        if 'INCIDENTNAME' not in aoi_points.columns:
            aoi_points['INCIDENTNAME'] = self.run_name
        aoi_points['CLEAN_DATE'] = pd.to_datetime(self.run_date)

        aoi_points['YEAR'] = aoi_points['CLEAN_DATE'].dt.year
        aoi_points['MONTH'] = aoi_points['CLEAN_DATE'].dt.month
        aoi_points['CLEAN_DATE'] = aoi_points['CLEAN_DATE'].dt.date

        aoi_points['FP_SQFT'] = None
        aoi_points['FP_PMFT'] = None
        aoi_points['SQFT'] = aoi_points['LIVING_SQFT']
        aoi_points['SQFT_SOURCE'] = 'PARCEL'

        #print("Before drop", list(aoi_points.columns))
        # Filter to important fields
        keep_fields = [
            'OBJECTID', 'DAMAGE', 'STREETNUMBER', 'STREETNAME', 'STREETTYPE', 'STREETSUFFIX', 'CITY', 'STATE', 
            'ZIPCODE', 'CALFIREUNIT', 'COUNTY', 'COMMUNITY', 'INCIDENTNAME', 'INCIDENTNUM', 'INCIDENTSTARTDATE', 
            'CLEAN_DATE', 'HAZARDTYPE', 'STRUCTURECATEGORY', 'STRUCTURETYPE', 'APN', 'YEARBUILT', 'SITEADDRESS', 
            'GLOBALID', 'YEAR', 'MONTH', 'SQFEET', 'FEMA_SQFT', 'FEMA_PMFT', 'PARCEL_APN', 'SITE_ADDR', 'SITE_CITY', 'SITE_STATE', 'SITE_ZIP',
            'SITE_UNIT_PREFIX', 'SITE_UNIT_NUMBER', 'SITE_HOUSE_NUMBER', 'SITE_DIRECTION', 'USE_CODE_MUNI_DESC', 
            'USE_CODE_MUNI', 'USE_CODE_STD_LPS', 'USE_CODE_STD_DESC_LPS', 'ZONING', 'LIVING_SQFT', 'YR_BLT', 'STORIES_NUMBER', 
            'TOTAL_ROOMS', 'UNITS_NUMBER', 'BEDROOMS', 'TOTAL_BATHS', 'CAT', 'USECODE_SD', 'PARCEL_CAT', 'PARCEL_CAT_MATCH',
            'SQFT_SOURCE', 'SQFT', 'CO_NAME', 'BASIN_NAME', 'DIS_NAME', 'COABDIS_ID', 
            'GEOMETRY', 'geometry', 'CENTROID', 'centroid'
        ]

        aoi_cols = [col for col in aoi_points.columns if col.startswith('AOI_')]
        keep_cols = keep_fields + aoi_cols

        existing_columns = [col for col in keep_cols if col in aoi_points.columns]
        missing_columns = set(keep_fields) - set(aoi_points.columns)
        if missing_columns:
            print("Missing columns:", missing_columns)

        return aoi_points[existing_columns]

    def _add_damage(self, aoi_points: gpd.GeoDataFrame, ratio_destroyed: float) -> gpd.GeoDataFrame:
        """
        Adds synthetic 'DAMAGE' column labeling a proportion of points as destroyed.

        Parameters
        ----------
        aoi_points : gpd.GeoDataFrame
            Input AOI points.
        ratio_destroyed : float
            Proportion of points to randomly label as "Destroyed (>50%)".

        Returns
        -------
        gpd.GeoDataFrame
            AOI points with DAMAGE column added.
        """

        if 'DAMAGE' not in aoi_points.columns:
            total_rows = len(aoi_points)
            destroyed_count = int(ratio_destroyed * total_rows)
            destroyed_indices = np.random.choice(aoi_points.index, size=destroyed_count, replace=False)
            aoi_points['DAMAGE'] = "No Damage"
            aoi_points.loc[destroyed_indices, 'DAMAGE'] = "Destroyed (>50%)"
        return aoi_points

    def prep_dataset(
        self,
        aoi_points: gpd.GeoDataFrame,
        ratio_destroyed: float = 1.0
    ) -> gpd.GeoDataFrame:
        """
        Runs the full processing pipeline:
        1. Spatial join with COABDIS
        2. Clean columns
        3. Add synthetic damage data

        Parameters
        ----------
        aoi_points : gpd.GeoDataFrame
            Input point data to process.
        ratio_destroyed : float, optional
            Proportion of points to label as "Destroyed (>50%)" (default is 1.0).

        Returns
        -------
        gpd.GeoDataFrame
            Fully processed AOI points with updated columns and geometry.
        """

        out = self._add_coabdis(aoi_points)
        out = self._clean_columns(out)
        out = self._add_damage(out, ratio_destroyed)
        out.columns = out.columns.str.lower()
        out = out.rename(columns={
            "geometry": "parcel_geometry",
            "centroid": "geometry",
            "COABDIS_ID": "COABDIS",
            "BASIN_NAME": "AIR_BASIN",
            "DIS_NAME" : "AIR_DISTRICT"
        })
        out.set_geometry("geometry", inplace=True)
        return out
