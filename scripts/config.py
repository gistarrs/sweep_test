import os
# Project settings
project = {
    'name': 'SWEEP',
    'version': '1.0'
}

# "gdb" or "api"
bsdb_source = "geojson"

config_dir = os.path.dirname(os.path.abspath(__file__))
package_root = os.path.abspath(os.path.join(config_dir, ".."))
data_dir = os.path.join(package_root, "data")
ef_folder = os.path.join(data_dir, "emissions_factors")

# Default folder outputs will be written to.
out_dir = os.path.join(package_root, "outputs")

# File paths
working_gdb = r"C:\Users\gstarrs\Projects\CARB\SWEEP\SWEEP_Project.gdb"
# parcel_gdb = r"C:\Users\gstarrs\Projects\CARB\SWEEP\inputs\PAPCEL_DATA_Q4_NOPII.gdb"


# URLs for layers used in API queries.
bsdb_url = "https://services.arcgis.com/0xnwbwUttaTjns4i/arcgis/rest/services/BSDB/FeatureServer/0/query"

ef_default = "HOLDER"
structure_consumption_default = "DINS3"
contents_factor_default = "HOLDER"
frame_factor_default = "HOLDER"
pollutants_default = ["CO", "NOx", "SOx", "PM", "TOG"]
vpollutants_default = ['CO' 'NOx' 'SOx' 'PM']
