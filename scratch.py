import os
import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import matplotlib.colors as colors

from sweep.estimator_main import sweep_estimator
from sweep.predictor_main import sweep_predictor
import sweep.config as config
from dotenv import load_dotenv
load_dotenv() 

print("Imports complete!")

# Demo 1: 
# Interactive query AND database download.
# Zogg: 2020
emissions_gdf, agg_table, vehicle_table = sweep_estimator(
    #get_mode ="refresh",
    get_mode ="use_default",
    filter_method = "Interactive",
    write = "Yes"
    )

# View outputs
emissions_gdf.head()
agg_table
vehicle_table

# Visualize using .explore()
emissions_gdf1 = emissions_gdf[emissions_gdf['STRUCTURECATEGORY'] != "Other Minor Structure"]
emissions_gdf1 = emissions_gdf1[emissions_gdf1['CONSUMPTION_FACTOR'] > 0]
emissions_gdf1.explore(
    column="E_PM_TN",
    cmap="YlOrRd",
    legend=True,
    tooltip=["E_PM_TN"],
    popup = True,
)

# Demo 2, 3, 4 (predictor): See Demo Page at https://gistarrs.github.io/sweep_test/

# Demo 5: Customizing Emissions Estimation Options
emissions_gdf, agg_table, vehicle_table = sweep_estimator(
    get_mode ="use_default",
    filter_method = "Automated",
    filter_field = "Air Basin",
    field_values = ['MOUNTAIN COUNTIES', "SAN JOAQUIN VALLEY"], 
    apply_date_filter= True,
    start_date = "2021-01-01",
    end_date = "2024-01-01",
    ef_choice = "HOLDER",
    pollutants = ["CO", "NOx"],
    vehicle_ef_choice = "HOLDER",
    vpollutants = ["CO", "NOx"],
    structure_consumption = "DINS5", # Choose from preset (HOLDER, CARB, DINS3, DINS5) or use a float
    frame_factor= 8, # Choose from preset (HOLDER, CARB) or use a float
    contents_factor = 12, # Choose from preset (HOLDER, CARB) or use a float
    aggregate_fields=['AIR DISTRICT', 'AIR BASIN', 'INCIDENT'],
    write = "NO"
    )

# Visualize using .explore()
emissions_gdf1 = emissions_gdf[emissions_gdf['STRUCTURECATEGORY'] != "Other Minor Structure"]
# Drop non-damaged structures
emissions_gdf1 = emissions_gdf1[emissions_gdf1['CONSUMPTION_FACTOR'] > 0]
emissions_gdf1.explore(
    column="E_CO_TN",
    cmap="YlOrRd",
    legend=True,
    tooltip=["E_CO_TN"],
    popup = True
)

# Demo 6: Using custom emissions factor files

# File format:
# It expects a .xlsx file.
# For structures, it requires Pollutant and Structure_gkg (emissions in grams per kg material consumed) columns:
holder_efs = pd.read_excel(os.path.join(config.ef_folder, "Holder_EFs.xlsx"))
holder_efs.head()

# Here are my test_efs, a weird subset:
test_efs = pd.read_excel(os.path.join(config.ef_folder, "Test_EFs.xlsx"))
test_efs

# For vehicles, it will also require a Vehicle_gkg column (emissions in grams per kg material consumed)
emissions_gdf, agg_table, vehicle_table = sweep_estimator(
    get_mode ="use_default",
    filter_method = "Interactive",
    ef_choice= "OTHER", # Signifies we don't want to use a preset file.
    user_efs = r"C:\Users\gstarrs\Projects\CARB\sweep_test\data\emissions_factors\Test_EFs.xlsx",
    vehicle_ef_choice = "OTHER", # Signifies we don't want to use a preset file.
    # If a path is provided, it will default to using all emissions factors in the excel file.
    user_vefs = r"C:\Users\gstarrs\Projects\CARB\sweep_test\data\emissions_factors\Test_EFs.xlsx",
    aggregate_fields=['AIR DISTRICT', 'INCIDENT']
    )















# from sweep.get_bsdb import GetBSDB
# #bsdb_df = GetBSDB("refresh", org = "IGIS").bsdb_df
# bsdb_df = GetBSDB("use_default").bsdb_df

# bsdb_dupes = bsdb_df[bsdb_df['globalid'].duplicated(keep=False)]
# bsdb_dup_uniques = bsdb_dupes['globalid'].nunique()
# true_dupes = bsdb_dupes[bsdb_dupes.duplicated(keep=False)]
