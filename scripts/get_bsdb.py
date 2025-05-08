import geopandas as gpd
import os
import json
from pyogrio import list_layers
from datetime import datetime
import pandas as pd
import scripts.config as config
import requests

class get_BSDB:
    """
    The `get_BSDB` class is used to retrieve the BSDB (Building Structure Damage Base) data from different sources:
    a file Geodatabase (GDB), an API, or a GeoJSON file. The class automatically loads the BSDB data into a GeoDataFrame 
    and processes any relevant date columns.

    Parameters:
    - `source` (str): The data source for retrieving the BSDB data. 
      Can be one of the following:
        - "API" (API): Fetches data from an API and saves it as a GeoJSON file. For use on first run, and periodic updates.
        - "GEOJSON" (GeoJSON): Loads BSDB data from an existing GeoJSON file. Previous API return is saved and will be called if this is chosen.
        - "GDB" (Geodatabase): Loads data from a file Geodatabase (user must already have a local GDB with a BSDB).
    
    Notes
    -----
    - source parameter is not case sensisitive.
    
    Example
    -----
    >>> bsdb_api = get_BSDB("API") 
    >>> bsdb_gjn = get_BSDB("geojson") 
    """
        
    def __init__(self, source):
        #self.bsdb_source = config.bsdb_source
        self.bsdb_source = source.upper()
        self.url = config.bsdb_url
        if self.bsdb_source == "GDB":
            self.gdb = config.working_gdb
            self.bsdb = self.get_gdb_bsdb()
            self.bsdb_df = gpd.read_file(self.gdb, layer=self.bsdb, engine = "pyogrio")
        elif self.bsdb_source == "API":
            geo_path = self.bsdb_api_query()
            self.bsdb_df = gpd.read_file(geo_path)
            self.bsdb_df['incidentstartdate'] = pd.to_datetime(self.bsdb_df['incidentstartdate'], unit='ms', errors='coerce')
            self.bsdb_df['clean_date'] = pd.to_datetime(self.bsdb_df['clean_date'], unit='ms', errors='coerce')
        elif self.bsdb_source == "GEOJSON":
            geo_path = self.get_geojson_bsdb()
            self.bsdb_df = gpd.read_file(geo_path)
            self.bsdb_df['incidentstartdate'] = pd.to_datetime(self.bsdb_df['incidentstartdate'], unit='ms', errors='coerce')
            self.bsdb_df['clean_date'] = pd.to_datetime(self.bsdb_df['clean_date'], unit='ms', errors='coerce')

    def get_gdb_bsdb(self, db_type="BSDB"):
        """Identifies the most recent {db_type} feature class in a file geodatabase."""
        gdb_path = config.working_gdb  # path to .gdb folder
        print("Getting BSDB from gdb:", gdb_path)
        # Get just the layer names from the structured array
        layers = list_layers(gdb_path)
        layer_names = layers[:, 0]  # Extracting the first column (layer names)
        db_files = [name for name in layer_names if name.startswith(db_type)]

        if not db_files:
            print(f"No {db_type} layers found in {gdb_path}.")
            return None

        # Find the latest by date string
        latest_date = None
        latest_file = None
        for fc in db_files:
            date_str = fc[-8:]  # assumes format like BSDB20240410
            try:
                date_obj = datetime.strptime(date_str, "%Y%m%d")
                if latest_date is None or date_obj > latest_date:
                    latest_date = date_obj
                    latest_file = fc
            except ValueError:
                continue

        if latest_file:
            print(f"{db_type} is set to: {latest_file}")
            return latest_file
        else:
            print(f"No valid-dated {db_type} layers found.")
            return None
    
    def get_geojson_bsdb(self):
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
        except NameError:
            script_dir = os.getcwd()
        data_dir = os.path.join(script_dir, "..", "data")
        os.makedirs(data_dir, exist_ok=True)  # Create data folder if it doesn't exist
        geojson_path = os.path.join(data_dir, "bsdb_data.geojson")
        return geojson_path

    def fetch_data(self, query_url):
        """Makes an quest and returns the JSON response."""
        response = requests.get(query_url)
        response.raise_for_status()
        return response.json()

    def bsdb_api_query(self):
        """Queries the BSDB API and saves the entire dataset as a GeoJSON file."""
        import json

        print("✅ API query for BSDB initiated!")
        offset = 0
        result_record_count = 2000
        all_features = []

        while True:
            query_url = (
                f"{self.url}?where=1=1"
                f"&outFields=*"
                f"&outSR=4326"
                f"&f=geojson"
                f"&resultOffset={offset}"
                f"&resultRecordCount={result_record_count}"
            )
            features_data = self.fetch_data(query_url)

            # Check if the response is a valid GeoJSON FeatureCollection
            features = features_data.get("features")
            if not features:
                break

            all_features.extend(features)
            offset += result_record_count

        # ✅ Create final GeoJSON FeatureCollection
        geojson_data = {
            "type": "FeatureCollection",
            "features": all_features
        }
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
        except NameError:
            script_dir = os.getcwd()
        data_dir = os.path.join(script_dir, "..", "data")
        os.makedirs(data_dir, exist_ok=True)  # Create data folder if it doesn't exist
        geojson_path = os.path.join(data_dir, "bsdb_data.geojson")
        
        with open(geojson_path, "w", encoding="utf-8") as f:
            json.dump(geojson_data, f, ensure_ascii=False, indent=2)

        print(f"✅ API data saved to {geojson_path}. Total features: {len(all_features)}")
        return geojson_path
