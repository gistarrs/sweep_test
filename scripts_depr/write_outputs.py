import geopandas as gpd
import numpy as np
import os
import pandas as pd
import sys
from datetime import datetime

import scripts.config as config

def write_outputs(emissions_gdf, out_folder = config.out_dir, suffix = None, aggregated_report=None,
                  vehicle_report=None, spatial=True, spatial_type="GPKG"):
    """
    Writes emissions, optional aggregated and vehicle reports, and spatial output to a timestamped folder.
    
    Parameters:
    - emissions_gdf: GeoDataFrame (with emissions and geometry)
    - out_folder: Base folder path where output folder will be saved (timestamp will be appended if no suffix provided)
    - suffix: tag to end to output folder name. If none is provided a timestamp will be used.
    - aggregated_report: DataFrame to write to Excel (optional)
    - vehicle_report: DataFrame to write to Excel (optional)
    - spatial: Whether to write spatial file (default: True)
    - spatial_type: One of 'GPKG', 'SHP', 'GEOJSON'
    """

    # Add timestamp to output folder
    if suffix is None:
        suffix = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    out_folder = os.path.join(out_folder, f"SWEEP_{suffix}")
    os.makedirs(out_folder, exist_ok=True)

    # 1. Always write emissions report
    er_out = os.path.join(out_folder, "Emissions_Report.xlsx")
    print(f"Writing Emissions Report to {er_out}")
    emissions_excel = emissions_gdf.copy()
    emissions_excel['geometry_wkt'] = emissions_excel.geometry.astype(str)
    emissions_excel.to_excel(er_out, index=False)

    # 2. Conditionally write aggregated report
    if aggregated_report is not None:
        ar_out = os.path.join(out_folder, "Aggregated_Report.xlsx")
        print(f"Writing Aggregated Report to {ar_out}")
        aggregated_report.to_excel(ar_out, index=False)

    # 3. Conditionally write vehicle report
    if vehicle_report is not None:
        vr_out = os.path.join(out_folder, "Vehicle_Report.xlsx")
        print(f"Writing Vehicle Report to {vr_out}")
        vehicle_report.to_excel(vr_out, index=False)

    # 4. Spatial output
    if spatial:
        spatial_type = spatial_type.upper()
        spatial_out = None
        if spatial_type == "GPKG":
            spatial_out = os.path.join(out_folder, "Emissions_Spatial.gpkg")
            emissions_gdf.to_file(spatial_out, driver="GPKG")
        elif spatial_type == "SHP":
            spatial_out = os.path.join(out_folder, "Emissions_Spatial.shp")
            emissions_gdf.to_file(spatial_out, driver="ESRI Shapefile")
        elif spatial_type == "GEOJSON":
            spatial_out = os.path.join(out_folder, "Emissions_Spatial.geojson")
            emissions_gdf.to_file(spatial_out, driver="GeoJSON")
        else:
            raise ValueError(f"Unsupported spatial_type: {spatial_type}")
        print(f"Spatial data written to {spatial_out}")
