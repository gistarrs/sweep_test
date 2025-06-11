import os
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import matplotlib.colors as colors

from sweep.estimator_main import sweep_estimator
from sweep.predictor_main import sweep_predictor
from dotenv import load_dotenv
load_dotenv() 

print("Imports complete!")

# import importlib
# import SWEEP_estimator

# importlib.reload(SWEEP_estimator)
# from SWEEP_estimator import main as sweep_estimator

#os.getenv('LB_API_KEY')

emissions_gdf, agg_table, vehicle_table = sweep_estimator(
    get_mode ="use_default",
    ef_choice= "OTHER",
    user_efs = r"C:\Users\gstarrs\Projects\CARB\sweep_test\data\emissions_factors\Test_EFs.xlsx",
    vehicle_ef_choice = "OTHER",
    user_vefs = r"C:\Users\gstarrs\Projects\CARB\sweep_test\data\emissions_factors\Test_EFs.xlsx",
    filter_method = "Interactive",
    aggregate_fields=['AIR DISTRICT', 'INCIDENT']
    )
