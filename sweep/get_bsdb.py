
import glob
import json
import os
import re
from datetime import datetime
from typing import Optional, Literal

import geopandas as gpd
import pandas as pd
import pyogrio
import requests
from dotenv import load_dotenv
from pyogrio import list_layers

from sweep import config


class GetBSDB:
    """
    Retrieves Burned Structure Database (BSDB) data and loads it into a GeoDataFrame.

    Parameters
    ----------
    mode : Literal["use_default", "use_custom", "refresh"]
        Determines how the data is loaded.
    org : Literal["CARB", "IGIS"]
        Organization used for AGOL credentials.
    custom_filename : Optional[str]
        Custom file name to use when mode is "use_custom" or saving a refreshed file.
    overwrite : bool
        Whether to overwrite an existing file in refresh mode.
    """
    
    def __init__(
        self,
        mode: Literal["use_default", "use_custom", "refresh"] = "use_default",
        org: Literal["CARB", "IGIS"] = "CARB",
        custom_filename: Optional[str] = None,
        overwrite: bool = False,
    ) -> None:
        self.data_dir = config.data_dir
        if org == "IGIS":
            self.agol_portal = config.agol_path_igis
            self.agol_oauth = config.agol_oauth_igis
            self.bsdb_id = config.bsdb_id_igis
            self.url = config.bsdb_url_igis
        else:
            self.agol_portal = config.agol_path_carb
            self.agol_oauth = config.agol_oauth_carb
            self.bsdb_id = config.bsdb_id_carb
            self.url = config.bsdb_url_carb

        geo_path = self.get_bsdb_data(mode=mode, custom_filename=custom_filename, overwrite=overwrite)
        self.bsdb_df = gpd.read_file(geo_path)
        # BSDB is in 3310, geojson assumes 4326.
        self.bsdb_df = self.bsdb_df.set_crs(epsg=3310, allow_override = True)

        for col in ["incidentstartdate", "clean_date"]:
            if col in self.bsdb_df.columns:
                self.bsdb_df[col] = pd.to_datetime(self.bsdb_df[col], unit="ms", errors="coerce")

    def get_geojson_bsdb(self) -> str:
        # Use the 'data' folder inside the current script directory
        pattern = os.path.join(self.data_dir, "bsdb_data_*.geojson").replace("\\", "/")
        geojson_files = glob.glob(pattern)

        if not geojson_files:
            raise FileNotFoundError("No bsdb_data_*.geojson files found in the data directory.")

        def extract_timestamp(f):
            basename = os.path.basename(f)
            match = re.search(r"bsdb_data_(\d{8}_\d{6})\.geojson", basename)
            if match:
                return datetime.strptime(match.group(1), "%Y%m%d_%H%M%S")
            return datetime.min

        latest_file = max(geojson_files, key=extract_timestamp)
        return latest_file


    def api_bsdb_features(self)  -> list:
        from arcgis.gis import GIS

        print("🔐 Starting AGOL authentication")
        print("\033[1;31m❗If Paste or Ctrl V don't work, use Shift Insert to paste code.❗\033[0m")
        gis = GIS(self.agol_portal, client_id=self.agol_oauth, profile=None)
        print("🔓 Logged in as:", gis.users.me.username)

        item = gis.content.get(self.bsdb_id)
        if not item:
            raise Exception(f"Item with ID {self.bsdb_id} not found!")
        layers = item.layers
        if not layers:
            raise Exception("No layers found in this item!")

        feature_layer = layers[0]
        print(f"Accessing FeatureLayer: {feature_layer.url}")

        features = feature_layer.query(where="1=1", out_fields="*", return_all_records=True, return_geometry=True)
        print(f"Retrieved {len(features)} features")
        return features

    def save_features_to_geojson(self, features: list, path: str) -> None:
        geojson_features = []
        for feature in features:
            f_dict = feature.as_dict
            geometry = f_dict.get("geometry")
            attributes = f_dict.get("attributes", {})
            if geometry is None:
                continue

            if isinstance(geometry, dict) and "x" in geometry and "y" in geometry:
                geometry = {
                    "type": "Point",
                    "coordinates": [geometry["x"], geometry["y"]]
                }
            elif isinstance(geometry, dict) and "rings" in geometry:
                geometry = {
                    "type": "Polygon",
                    "coordinates": geometry["rings"]
                }
            # else: assume geometry is already valid GeoJSON

            geojson_features.append({
                "type": "Feature",
                "geometry": geometry,
                "properties": attributes
            })

        geojson_data = {
            "type": "FeatureCollection",
            "features": geojson_features
        }

        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(geojson_data, f, ensure_ascii=False, indent=2)

        print(f"✅ Saved {len(geojson_features)} features to {path}")

    def get_bsdb_data(
        self,
        mode: Literal["use_default", "use_custom", "refresh"] = "use_default",
        custom_filename: Optional[str] = None,
        overwrite: bool = False
    ) -> str:
        """
        Controls BSDB data retrieval and loading.

        Parameters
        ----------
        mode : str
            One of:
                - "use_default": Load the latest BSDB GeoJSON from the data folder.
                - "use_custom": Load a specific file by name from the data folder.
                - "refresh": Download fresh data from the API. If custom_filename is provided, save to that file. Otherwise file will be named using date/time of download.
        custom_filename : str, optional
            File name to load (for 'use_custom') or save to (for 'refresh').
        overwrite : bool, optional
            Whether to overwrite file if it exists (only applies to 'refresh' + custom_filename).
        """
        if mode == "use_default":
            return self.get_geojson_bsdb()

        elif mode == "use_custom":
            if custom_filename:
                filename = custom_filename if custom_filename.endswith(".geojson") else f"{custom_filename}.geojson"
            else:
                raise ValueError("custom_filename is required for 'use_custom' mode.")
            path = os.path.join(self.data_dir, filename)
            if not os.path.exists(path):
                print(f"{path} does not exist. Use mode = refresh with custom_filename to write new file from API, mode = use_latest for default file, or file name for other existing file in data folder.")
                raise FileNotFoundError(f"Custom file not found: {path}")
            return path

        elif mode == "refresh":
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            if custom_filename:
                filename = custom_filename if custom_filename.endswith(".geojson") else f"{custom_filename}.geojson"
            else:
                filename = f"bsdb_data_{timestamp}.geojson"
                filename = custom_filename if custom_filename else f"bsdb_data_{timestamp}.geojson"
            path = os.path.join(self.data_dir, filename)

            if os.path.exists(path) and not overwrite:
                raise FileExistsError(f"{path} already exists. Use overwrite=True to replace it.")

            features = self.api_bsdb_features()
            self.save_features_to_geojson(features, path)
            return path

        else:
            raise ValueError("Invalid mode. Choose from 'use_default', 'use_custom', or 'refresh'.")