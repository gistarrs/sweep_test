import os

# ------------------------
# Project metadata
# ------------------------
project = {
    'name': 'SWEEP',
    'version': '1.0'
}

# ------------------------
# Default SWEEP settings
# ------------------------
bsdb_source = "geojson"  # options: "gdb", "api", "geojson"

ef_default = "HOLDER"
structure_consumption_default = "DINS3"
contents_factor_default = "HOLDER"
frame_factor_default = "HOLDER"

pollutants_default = ["CO", "NOx", "SOx", "PM", "TOG"]
vpollutants_default = ['CO', 'NOx', 'SOx', 'PM']  # fixed missing commas


# ------------------------
# File paths (absolute)
# ------------------------
working_gdb = r"C:\Users\gstarrs\Projects\CARB\SWEEP\SWEEP_Project.gdb"
parcel_path = r"C:\Users\gstarrs\Projects\CARB\SWEEP\inputs\PAPCEL_DATA_Q4_NOPII.gdb"
parcel_layer = "Statewide_Polygons_Q4_2023_cleaned"


# ------------------------
# Paths setup
# ------------------------
config_dir = os.path.dirname(os.path.abspath(__file__))
package_root = os.path.abspath(os.path.join(config_dir, ".."))

data_dir = os.path.join(package_root, "data")
demo_dir = os.path.join(data_dir, "demo_shapes")

predictor_dir = os.path.join(data_dir, "predictor_inputs")
category_crosswalk = os.path.join(predictor_dir, "CAT_USECODE_crossref.csv")
coabdis_layer = os.path.join(predictor_dir, "CoAbDis.shp")
ef_folder = os.path.join(data_dir, "emissions_factors")

# Demo shapefiles
demo_aoi_path = os.path.join(demo_dir, "fire_demo.shp")
demo_spatial_filter = os.path.join(demo_dir, "demo_polygon.shp")

# Default output directory
out_dir = os.path.join(package_root, "outputs")


# ------------------------
# API URLs
# ------------------------
bsdb_url = "https://services.arcgis.com/0xnwbwUttaTjns4i/arcgis/rest/services/BSDB/FeatureServer/0/query"
