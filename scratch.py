import os
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import matplotlib.colors as colors

from sweep.estimator_main import sweep_estimator
from sweep.predictor_main import sweep_predictor
from dotenv import load_dotenv
load_dotenv() 

import pandas as pd

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

from sweep.get_bsdb import GetBSDB
#bsdb_df = GetBSDB("refresh", org = "IGIS").bsdb_df
bsdb_df = GetBSDB("use_default").bsdb_df

bsdb_dupes = bsdb_df[bsdb_df['globalid'].duplicated(keep=False)]
bsdb_dup_uniques = bsdb_dupes['globalid'].nunique()
true_dupes = bsdb_dupes[bsdb_dupes.duplicated(keep=False)]


import pandas as pd
from collections import Counter

# Step 1: Get all rows with duplicated globalid
dupes = bsdb_df[bsdb_df['globalid'].duplicated(keep=False)]

# Step 2: Group by globalid
grouped = dupes.groupby('globalid')

# Step 3: Track which columns differ per duplicated globalid
diff_columns_by_gid = []

for gid, group in grouped:
    if len(group) > 1:
        differing = group.nunique(dropna=False) > 1
        diff_cols = list(differing[differing].index)
        diff_columns_by_gid.extend(diff_cols)

# Step 4: Count how many times each column shows up as differing
column_diff_counts = Counter(diff_columns_by_gid)

# Step 5: Convert to DataFrame
column_diff_df = pd.DataFrame.from_dict(column_diff_counts, orient='index', columns=['num_globalid_duplicates'])
column_diff_df.index.name = 'column'
column_diff_df = column_diff_df.reset_index().sort_values(by='num_globalid_duplicates', ascending=False)



# Drop where duplication is only due to non-important columns (objectid, bathrooms, municipal use code, etc)
bsdb_df1 = bsdb_df.copy()
cols_to_check = [col for col in bsdb_df1.columns if col not in [
    "OBJECTID", "total_baths", "total_rooms", "zoning", 
    "use_code_muni_desc", "use_code_muni", "site_city", "site_zip", 'bedrooms'
    ]]
bsdb_df2 = bsdb_df1.drop_duplicates(subset=cols_to_check, keep='first')

globalid_counts = bsdb_df2['globalid'].value_counts()
duplicated_globalids_after_drop = globalid_counts[globalid_counts > 1].index

# Remaining duplicated bsdb
dupes = bsdb_df2[bsdb_df2['globalid'].isin(duplicated_globalids_after_drop)].sort_values(by = ["globalid"])

important_cols = ['parcel_apn', 'site_addr', 'site_city', 'site_state', 'site_zip', 'use_code_std_lps', 'use_code_std_desc_lps', 'living_sqft', 'yr_blt',
       'total_rooms', 'units_number', 'nlcd', 'elev', 'cat', 'usecode_sd', 'parcel_cat', 'parcel_cat_match', 'fp_sqft', 'fp_pmft', 'x', 'y',
       'avg_value', 'land_type', 'sqft_source']
cleaned_dupes = []

for gid, group in dupes.groupby('globalid'):
    if len(group) > 1:
        # Count NaNs only in important columns
        group['na_count'] = group[important_cols].isna().sum(axis=1)

        # Keep the row with fewer NaNs; if tie, keep first
        best_row = group.sort_values(by='na_count').iloc[0]
        cleaned_dupes.append(best_row.drop('na_count'))  # drop helper column
    else:
        cleaned_dupes.append(group.iloc[0])  # only one row, keep as-is

dupes_cleaned = pd.DataFrame(cleaned_dupes).reset_index(drop=True)

bsdb_final = bsdb_df2[~bsdb_df2['globalid'].isin(dupes_cleaned['globalid'])]
bsdb_final = pd.concat([bsdb_final, dupes_cleaned], ignore_index=True)
assert bsdb_final['globalid'].is_unique, "Still have duplicate globalids!"