"""
Here we provide a few more in-depth examples of uses for the SWEEP scripted tool.
- Demo 1 allows users to download a new BSDB and use the interactive query tool.
- Demos 2 and 3 refer to the spatial and automated queries in the demo webpage.
- Demo 4 refers to the predictor query in the demo webpage.
- Demo 5 is an automated query using a user-specified subset of emissions factors 
and custom values for frame and contents loads.
- Demo 6 is an interactive query where the user specifies a 
custom emissions factor excel file.
"""

import os
import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import matplotlib.colors as colors

from sweep.estimator_main import sweep_estimator
import sweep.config as config

print("Imports complete!")

# Demo 1: Interactive query WITH new database download (refresh).
# Zogg: 2020
# Outputs are:
# * gdf of structures
# * aggregated table
# * vehicle table
zogg_gdf, zogg_agg_table, zogg_vehicle_table = sweep_estimator(
    # Refresh downloads new copy of bsdb, saves to bsdb_datasets/
    get_mode ="refresh",
    filter_method = "Interactive",
    write = "Yes"
    )
# For interactive mode, after data download follow prompts in the console.
# To get Zogg, say "no" for date filter, "yes" for other filter
# Select "Wildfire Name", then year: 2020
# Find Zogg and select it by typing it's list number (43).
# No other filters

# View outputs
zogg_gdf.head()
zogg_agg_table
zogg_vehicle_table

# Visualize using .explore()
zogg_gdf1 = zogg_gdf[zogg_gdf['STRUCTURECATEGORY'] != "Other Minor Structure"]
zogg_gdf1 = zogg_gdf1[zogg_gdf1['CONSUMPTION_FACTOR'] > 0]
zogg_gdf1.explore(
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
    # Automated allows user to set filter values as arguments (filter_method, filter_field, data filter).
    filter_method = "Automated",
    filter_field = "Air Basin",
    field_values = ['MOUNTAIN COUNTIES', "SAN JOAQUIN VALLEY"], 
    apply_date_filter= True,
    start_date = "2021-01-01",
    end_date = "2024-01-01",
    ef_choice = "HOLDER", # Emissions factor source for structures
    # Pollutants can be None (uses config default), a list of pollutants from the ef source, or "All".
    pollutants = ["CO", "NOx"],
    vehicle_ef_choice = "HOLDER", # Emissions factor source for vehicles
    # vpollutants (vehicle pollutants) can be None (uses config default), a list of pollutants from the ef source, or "All".
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


# Users can also view their local BSDB using the following:
from sweep.get_bsdb import GetBSDB
bsdb_df = GetBSDB("use_default").bsdb_df

