import os
from typing import Literal

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
#agol_oauth = "U4aVA527VsrHv4er"

agol_oauth_igis = "8LMSvsV75c4n3RUB"
agol_path_igis= "https://ucanr.maps.arcgis.com"
bsdb_id_igis = "3477a953ef1640d792c3bf294b2a1fa9"
bsdb_url_igis  = "https://services.arcgis.com/0xnwbwUttaTjns4i/arcgis/rest/services/BSDB/FeatureServer/0"

agol_oauth_carb= "mJDhSWckLJjDANvf"
agol_path_carb = "https://californiaarb.maps.arcgis.com"
bsdb_id_carb = "afd2f64e066d4d2ca1c6534e95815841"
bsdb_url_carb  = "https://services6.arcgis.com/x7ftScCDR8g2kVFB/arcgis/rest/services/BSDB/FeatureServer/0"


# ------------------------
# Parameter Options
# ------------------------

bsdb_source = "geojson"  # options: "gdb", "api", "geojson"

FilterField = Literal[
    "Wildfire Name",
    "Incident Number",
    "County",
    "Air Basin",
    "Air District",
    "CoAbDis Code"
]

ef_default = "HOLDER"
structure_consumption_default = "DINS3"
contents_factor_default = "HOLDER"
frame_factor_default = "HOLDER"

pollutants_default = ["CO", "NOx", "SOx", "PM", "TOG"]
vpollutants_default = ['CO', 'NOx', 'SOx', 'PM']  # fixed missing commas

# ------------------------
# Paths setup
# ------------------------
script_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(script_dir)  # one level up from scripts/
data_dir = os.path.join(root_dir, "data")
bsdb_dir = os.path.join(data_dir, "bsdb_datasets")
out_dir = os.path.join(root_dir, "outputs")
demo_dir = os.path.join(data_dir, "demo_shapes")
demo_poly = os.path.join(demo_dir, "demo_polygon.shp")

parcel_path = r"C:\Users\gstarrs\Projects\CARB\SWEEP\inputs\PAPCEL_DATA_Q4_NOPII.gdb"
parcel_layer = "Statewide_Polygons_Q4_2023_cleaned"
# config_dir = os.path.dirname(os.path.abspath(__file__))
# package_root = os.path.abspath(os.path.join(config_dir, ".."))


predictor_dir = os.path.join(data_dir, "predictor_inputs")
category_crosswalk = os.path.join(predictor_dir, "CAT_USECODE_crossref.csv")
coabdis_layer = os.path.join(predictor_dir, "CoAbDis.shp")
ef_folder = os.path.join(data_dir, "emissions_factors")

# Demo shapefiles
demo_aoi_path = os.path.join(demo_dir, "fire_demo.shp")
demo_spatial_filter = os.path.join(demo_dir, "demo_polygon.shp")




# ------------------------
# API URLs
# ------------------------
#bsdb_url = "https://services.arcgis.com/0xnwbwUttaTjns4i/arcgis/rest/services/BSDB/FeatureServer/0/query"
lightbox_url = "https://api.lightboxre.com/v1/parcels/us/geometry"
