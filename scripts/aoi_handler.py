
from datetime import datetime
import geopandas as gpd
import numpy as np
import os
import pandas as pd
import pyogrio
import sys
import rasterio
from shapely.geometry import Point

from scripts import config

# bsdb_df = GET.get_BSDB("geojson").bsdb_df
# bsdb_cols = list(bsdb_df.columns)

# aoi_path = r"C:\Users\gstarrs\Projects\CARB\SWEEP\sweep_test\data\fire_demo.shp"
# aoi_handler = AOIParcels(aoi_path)
# aoi_parcels, aoi_points = aoi_handler.aoi_parcels_from_bbox()
# processor = AOIProcessor()
# aoi_bsdb = processor.run_all(aoi_points)


# emissions_gdf = EE.estimate_emissions(
#     aoi_bsdb,
#     ef_choice="HOLDER",
#     pollutants=["CO", "NOx", "PO"]
# )

class AOIParcels:
    """
    A class to extract parcels that intersect with a user-submitted Area of Interest (AOI).

    Attributes:
        aoi_path (str): Path to the AOI file.
        parcel_path (str): Path to the parcel dataset. Defaults to config.parcel_path.
        parcel_layer (str): Layer name for the parcel data. Defaults to config.parcel_layer.
        crs (str): Coordinate reference system to use. Defaults to "EPSG:3310".
        aoi_gdf (GeoDataFrame): GeoDataFrame of the AOI.
    """
    def __init__(self, aoi_path, parcel_path = config.parcel_path, parcel_layer = config.parcel_layer, crs="EPSG:3310"):
        self.aoi_path = aoi_path
        self.parcel_path = parcel_path
        self.parcel_layer = parcel_layer
        self.crs = crs
        self.aoi_gdf = self._read_aoi_layer()

    def _read_aoi_layer(self):
        """
        Reads the AOI layer into a GeoDataFrame.
        """

        aoi_gdf = gpd.read_file(self.aoi_path, engine="pyogrio", layer=None)
        print(f"AOI layer read from {self.aoi_path}.")
        aoi_gdf = aoi_gdf.rename(columns={
            col: f"{col}_AOI" for col in aoi_gdf.columns if col != "geometry"
        })
        return aoi_gdf

    def _aoi_to_coordinates(self):
        """
        Converts AOI geometries to bounding boxes.

        Returns:
            list of dict: Each dict contains an index, bounding box (xmin, ymin, xmax, ymax),
                          and non-geometry properties of the AOI feature.
        """
        if self.aoi_gdf.crs.to_epsg() != 3310:
            self.aoi_gdf = self.aoi_gdf.to_crs(self.crs)
        
        bboxes = []
        for idx, row in self.aoi_gdf.iterrows():
            xmin, ymin, xmax, ymax = row.geometry.bounds
            bboxes.append({
                "index": idx,
                "bbox": [xmin, ymin, xmax, ymax],
                "properties": row.drop("geometry")
            })
        return bboxes

    def _read_parcels_by_bboxes(self, bbox_list):
        """
        Reads parcels that fall within each bounding box in the list.

        Args:
            bbox_list (list of dict): Bounding boxes with associated AOI indices.

        Returns:
            GeoDataFrame: Concatenated GeoDataFrame of all parcels intersecting the bounding boxes.
        """
        results = []

        for bbox in bbox_list:
            bounds = tuple(bbox["bbox"])  # Convert list to tuple
            df = pyogrio.read_dataframe(self.parcel_path, layer=self.parcel_layer, bbox=bounds)
            if not df.empty:
                df["aoi_index"] = bbox["index"]
                results.append(df)

        if results:
            parcels_gdf = gpd.GeoDataFrame(pd.concat(results, ignore_index=True), crs=results[0].crs)
        else:
            parcels_gdf = gpd.GeoDataFrame(columns=["geometry"], crs=self.crs)

        return parcels_gdf

    def aoi_parcels_from_bbox(self):
        """
        Performs spatial join between parcels and AOI features using bounding boxes
        and returns both parcel geometries and their centroids.

        Returns:
            tuple:
                - GeoDataFrame: Parcels intersecting AOI features.
                - GeoDataFrame: Point geometries of parcel centroids with same attributes.
        """
        bbox_list = self._aoi_to_coordinates()
        parcels_gdf = self._read_parcels_by_bboxes(bbox_list)

        # Ensure matching CRS
        if parcels_gdf.crs != self.aoi_gdf.crs:
            self.aoi_gdf = self.aoi_gdf.to_crs(parcels_gdf.crs)

        # Final spatial join to get precise AOI-parcel matches and attributes
        aoi_parcels = gpd.sjoin(parcels_gdf, self.aoi_gdf, how="inner", predicate="intersects")

        aoi_parcels['centroid'] = aoi_parcels.geometry.centroid
        point_gdf = gpd.GeoDataFrame(aoi_parcels, geometry='centroid', crs=aoi_parcels.crs)

        return aoi_parcels, point_gdf

class AOIProcessor:
    """
    A class to process AOI point data through three stages:
    1. Spatial join with COABDIS layer.
    2. Cleaning and formatting of columns.
    3. Adding synthetic damage data.

    Parameters:
    -----------
    coabdis_path : str
        Path to the COABDIS layer (GeoPackage, Shapefile, etc.).
    cat_crosswalk : str
        Path to the category crosswalk CSV.
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

    def _parse_date(self, run_date):
        if run_date is None:
            return datetime.today().date()
        if isinstance(run_date, str):
            return datetime.strptime(run_date, "%m/%d/%Y").date()
        return run_date

    def add_coabdis(self, aoi_points):
        """Filters and joins AOI points with the COABDIS layer using spatial join."""
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
        print(aoi_coab.columns)
        return aoi_coab

    def clean_columns(self, aoi_points):
        """Standardizes column names, adds metadata fields, and filters columns."""
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

        print("Before drop", aoi_points.columns)
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
            'AOI_INDEX', 'GEOMETRY', 'geometry', 'CENTROID', 'centroid'
        ]

        aoi_cols = [col for col in aoi_points.columns if col.endswith('_AOI')]
        keep_cols = keep_fields + aoi_cols

        existing_columns = [col for col in keep_cols if col in aoi_points.columns]
        missing_columns = set(keep_fields) - set(aoi_points.columns)
        if missing_columns:
            print("Missing columns:", missing_columns)

        return aoi_points[existing_columns]

    def add_damage(self, aoi_points, ratio_destroyed):
        """Adds synthetic 'DAMAGE' column based on a destruction ratio."""
        if 'DAMAGE' not in aoi_points.columns:
            total_rows = len(aoi_points)
            destroyed_count = int(ratio_destroyed * total_rows)
            destroyed_indices = np.random.choice(aoi_points.index, size=destroyed_count, replace=False)
            aoi_points['DAMAGE'] = "No Damage"
            aoi_points.loc[destroyed_indices, 'DAMAGE'] = "Destroyed (>50%)"
        return aoi_points

    def run_all(self, aoi_points, ratio_destroyed=1.0):
        """
        Runs the full processing pipeline:
        1. Spatial join with COABDIS
        2. Clean columns
        3. Add damage

        Parameters:
        -----------
        aoi_points : GeoDataFrame
            Input point data to process.

        ratio_destroyed : float
            Proportion of points to label as "Destroyed (>50%)".

        Returns:
        --------
        GeoDataFrame
            Fully processed AOI points.
        """
        out = self.add_coabdis(aoi_points)
        out = self.clean_columns(out)
        out = self.add_damage(out, ratio_destroyed)
        out.columns = out.columns.str.lower()
        out = out.rename(columns={
            "geometry": "parcel_geometry",
            "centroid": "geometry"
        })
        out.set_geometry("geometry", inplace=True)
        return out




# def add_coabdis(aoi_points, coabdis = config.coabdis_layer):
#     aoi_points = aoi_points[aoi_points['LIVING_SQFT'].notna()]
#     aoi_points = aoi_points[aoi_points['LIVING_SQFT']>0]
    
#     coabdis = gpd.read_file(coabdis)
#     if aoi_points.crs != coabdis.crs:
#         coabdis = coabdis.to_crs(aoi_points.crs)
    
#     if "index_right" in aoi_points.columns:
#         aoi_points = aoi_points.drop(columns="index_right")

#     aoi_coab = gpd.sjoin(
#         aoi_points,
#         coabdis,
#         how="left",
#         predicate="within"
#     )
#     return aoi_coab

# def clean_columns(aoi_points, run_date = None, run_name = None, cat_crosswalk = config.category_crosswalk):
    
#     aoi_points.columns = aoi_points.columns.str.upper()

#     if run_date is None:
#         run_date = datetime.today()
#     elif isinstance(run_date, str):
#         run_date = datetime.strptime(run_date, "%m/%d/%Y").date()
#     if run_name is None:
#         run_name = "SWEEP" + datetime.now().strftime("%Y%m%d%H%M")
    
#     codes = pd.read_csv(cat_crosswalk)
#     codes.rename(columns = {'USECODE_S': 'USE_CODE_STD_LPS'}, inplace = True)
#     codes['USE_CODE_STD_LPS'] = codes['USE_CODE_STD_LPS'].astype(str).str.split('.').str[0]

#     aoi_points = pd.merge(aoi_points, codes, on = 'USE_CODE_STD_LPS', how = 'left')
#     aoi_points['CAT'] = aoi_points['PARCEL_CAT']

#     if 'INCIDENTNAME' not in aoi_points.columns:
#         aoi_points['INCIDENTNAME'] = run_name
#     aoi_points['CLEAN_DATE'] = pd.to_datetime(run_date)

#     aoi_points['YEAR'] = aoi_points['CLEAN_DATE'].dt.year
#     aoi_points['MONTH'] = aoi_points['CLEAN_DATE'].dt.month
#     aoi_points['CLEAN_DATE'] = aoi_points['CLEAN_DATE'].dt.date

#     aoi_points['FP_SQFT'] = None
#     aoi_points['FP_PMFT'] = None

#     aoi_points['SQFT'] = aoi_points['LIVING_SQFT']
#     aoi_points['SQFT_SOURCE'] = aoi_points['PARCEL']

#     keep_fields = [
#         'OBJECTID', 'DAMAGE', 'STREETNUMBER', 'STREETNAME', 'STREETTYPE', 'STREETSUFFIX', 'CITY', 'STATE', 
#         'ZIPCODE', 'CALFIREUNIT', 'COUNTY', 'COMMUNITY', 'INCIDENTNAME', 'INCIDENTNUM', 'INCIDENTSTARTDATE', 
#         'CLEAN_DATE', 'HAZARDTYPE', 'STRUCTURECATEGORY', 'STRUCTURETYPE', 'APN', 'YEARBUILT', 'SITEADDRESS', 
#         'GLOBALID', 'YEAR', 'MONTH', 'SQFEET', 'FEMA_SQFT', 'FEMA_PMFT', 'PARCEL_APN', 'SITE_ADDR', 'SITE_CITY', 'SITE_STATE', 'SITE_ZIP',
#         'SITE_UNIT_PREFIX', 'SITE_UNIT_NUMBER', 'SITE_HOUSE_NUMBER', 'SITE_DIRECTION', 'USE_CODE_MUNI_DESC', 
#         'USE_CODE_MUNI', 'USE_CODE_STD_LPS', 'USE_CODE_STD_DESC_LPS', 'ZONING', 'LIVING_SQFT', 'YR_BLT', 'STORIES_NUMBER', 
#         'TOTAL_ROOMS', 'UNITS_NUMBER', 'BEDROOMS', 'TOTAL_BATHS', 'CAT', 'USECODE_SD', 'PARCEL_CAT', 'PARCEL_CAT_MATCH',
#         'SQFT_SOURCE', 'SQFT', 'CO_NAME', 'BASIN_NAME', 'DIS_NAME', 'COABDIS', 'GEOMETRY', 'geometry', 'CENTROID', 'centroid'
#         ]

#     existing_columns = [col for col in keep_fields if col in aoi_points.columns]
#     missing_columns = set(keep_fields) - set(aoi_points.columns)
#     aoi_points = aoi_points[existing_columns]
#     if missing_columns:
#         print("Missing columns:", missing_columns)

#     return aoi_points

# def add_damage(aoi_points, ratio_destroyed = 1):
#     if 'DAMAGE' not in aoi_points.columns:
#         aoi_points['DAMAGE'] = "No Damage" # You can choose a default value here (e.g., "Unknown")
#         # Set percentage of rows to be "Destroyed (>50%)"
#         total_rows = len(aoi_points)
#         destroyed_count = int(ratio_destroyed * total_rows)
#         destroyed_indices = np.random.choice(aoi_points.index, size=destroyed_count, replace=False)
#         aoi_points['DAMAGE'] = "No Damage"  # Set all rows to "No Damage" first
#         aoi_points.loc[destroyed_indices, 'DAMAGE'] = "Destroyed (>50%)"  # Assign "Destroyed (>50%)" to the selected rows
#     return aoi_points
