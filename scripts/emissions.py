import geopandas as gpd
import numpy as np
import os
import pandas as pd
import sys
from datetime import datetime

import scripts.config as config

def estimate_emissions(
    structure_df, 
    ef_choice = config.ef_default, 
    frame_factor = config.frame_factor_default, 
    contents_factor = config.contents_factor_default, 
    structure_consumption = config.structure_consumption_default,
    sqft_choice = None, 
    user_efs = None, 
    pollutants = config.pollutants_default,
    ef_folder = config.ef_folder
    ):

    """
    Calculates emissions for structures based on damage, square footage, 
    consumption factors, emission factors, and other parameters.

    Parameters:
    -----------
    df : pandas.DataFrame
        Input DataFrame containing structure data (BSDB).

    ef_choice : str
        Choice of emission factors dataset. Options:

        - "HOLDER": Emission factors from Holder et al. (2023)
        - "CARB": Emission factors from CARB's internal 1999 process
        - "OTHER": User provides a custom emissions factors path via `user_efs`

    frame_factor : str or float
        Frame factor source. Options:

        - "HOLDER": Use Holder et al. (2023) frame factor
        - "CARB": Use CARB frame factor
        - float: User-specified numeric frame factor

    contents_factor : str or float
        Contents factor source. Options:

        - "HOLDER": Use Holder et al. (2023) contents factor
        - "CARB": Use CARB contents factor
        - float: User-specified numeric contents factor

    structure_consumption : str
        Method for estimating structure consumption. Options:

        - "HOLDER": 80% consumption if damage is Major or Destroyed (DINS categories)
        - "CARB": 7% consumption if damaged
        - "DINS3": 
            0% if No/Minor damage  
            50% if Major  
            95% if Destroyed
        - "DINS5": Uses midpoint of DINS damage percentage bins:
            0%  No damage  
            5%  Minor damage  
            17.5%  Affected  
            38%  Major  
            75.5%  Destroyed

    sqft_choice : str, optional
        Numeric value if a single square footage number is desired.

    user_efs : str, optional
        Path to user-supplied emission factors file if ef_choice="OTHER".
        
    pollutants : str
        Pollutant species. Options:

        - Comma-separated list of pollutants to calculate
        - Default: ["CO", "NOx", "SOx", "PM", "TOG"]
        - "ALL": all available pollutants from specified ef_choice.

    Returns:
    --------
    pandas.DataFrame
        Dataframe with estimated emissions per structure.

    Example
    -------
    >>> estimate_emissions(filt_bsdb, ef_choice = "HOLDER", frame_factor=.8, pollutants = ["CO", "NOx", "PO"])
    >>> estimate_emissions(filt_bsdb, ef_choice = "CARB")
    >>> estimate_emissions(filt_bsdb, ef_choice = "OTHER", pollutants = "ALL", user_efs = r"C:/data/efs/custom_emissions_factors.xlsx")
    
    """
    print(ef_folder)
    # Add consumption factor
    # Lit from Gollner/Goldstein suggests if a structure is categorized as "Major Damage" or "Destroyed", it is almost entirely consumed.
        # High-- 95% for all structures over "minor" (eg major or destroyed)
        # Medium-- 80% for all structures over "minor" (Holder et al)
        # Low -- 7% for all structures (CARB 1999)
    structure_consumption_dictionary = {
        'HOLDER' : [0, 0, 0, 0.8, 0.8],
        'DINS3' : [0, 0, 0, 0.50, 0.95],
        'DINS5' : [0, 0.05, 0.175, 0.38, 0.755],
        'CARB' : [0, 0.07, 0.07, 0.07, 0.07]
        }

    structure_consumption = structure_consumption.upper()
    for index, row in structure_df.iterrows():
        damage = row['damage']
    # Assign values based on the selected methodology
        if damage == "No Damage":
            structure_df.at[index, 'CONSUMPTION_FACTOR'] = structure_consumption_dictionary[structure_consumption][0]
        elif damage == "Affected (1-9%)":
            structure_df.at[index, 'CONSUMPTION_FACTOR'] = structure_consumption_dictionary[structure_consumption][1]
        elif damage == "Minor (10-25%)":
            structure_df.at[index, 'CONSUMPTION_FACTOR'] = structure_consumption_dictionary[structure_consumption][2]
        elif damage == "Major (26-50%)":
            structure_df.at[index, 'CONSUMPTION_FACTOR'] = structure_consumption_dictionary[structure_consumption][3]
        elif damage == "Destroyed (>50%)":
            structure_df.at[index, 'CONSUMPTION_FACTOR'] = structure_consumption_dictionary[structure_consumption][4]

    structure_df['bsdb_sqft'] = structure_df['sqft']
    structure_df['sqft'] = structure_df[sqft_choice] if sqft_choice else structure_df['bsdb_sqft']
    
    structure_df = structure_df.rename(columns = {'sqft':'SQFT'})
    
    if isinstance(frame_factor, str):
        frame_factor = frame_factor.upper()

    if frame_factor == "HOLDER":
        structure_df['FRAME_FACTOR'] = 31.07
    elif frame_factor == "CARB":
        structure_df['FRAME_FACTOR'] = 13.34
    else:
        structure_df['FRAME_FACTOR'] = frame_factor
    
    if isinstance(contents_factor, str):
        contents_factor = contents_factor.upper()
    if contents_factor == "CARB":
        structure_df['CONTENTS_FACTOR'] = 7.909
        structure_df.loc[structure_df['cat'].isin(["COMMS", "COMSS", "SCH", "HP"]), 'CONTENTS_FACTOR'] = 8.636
        condition = (structure_df['cat'].isin(["SFSS", "SFMS", "MFSS", "MFMS", "MOB", "MOTOR"]))
        structure_df.loc[condition, 'CONTENTS_FACTOR'] = 7.909  
    elif contents_factor == "HOLDER":
        structure_df['CONTENTS_FACTOR'] = 5.87
    else:
        structure_df['CONTENTS_FACTOR'] = contents_factor    

    ef_choice = ef_choice.upper()
    if "HOLDER" in ef_choice:
        ef_path = os.path.join(ef_folder, "Holder_EFs.xlsx")
        print("Holder efs from:", ef_path)
    elif ef_choice == "CARB":
        ef_path = os.path.join(ef_folder, "CARB_EFs.xlsx")
        print("CARB efs from:", ef_path)
    elif ef_choice == "OTHER":
        ef_path = user_efs
        print("User-speficied emissions factors from:", ef_path)

    print("Requested pollutants:", pollutants)
    ef_df = pd.read_excel(ef_path)
    ef_df.columns = ef_df.columns.str.upper()  # Ensure column names are uppercase

    if pollutants == "ALL" or pollutants == "All" or pollutants == "all":
        EF = ef_df[['POLLUTANT', 'STRUCTURE_GKG']]
    else: 
        EF = ef_df[ef_df['POLLUTANT'].isin(pollutants)][['POLLUTANT', 'STRUCTURE_GKG']]
    
    # Drop NAs, convert to tons
    EF = EF[EF['STRUCTURE_GKG'].notna()]
    EF['EMISSION FACTOR'] = EF['STRUCTURE_GKG'] * 2

    available_pollutants = EF['POLLUTANT'].unique()
    print("Returned pollutants:", available_pollutants)

    def calculate_emissions(df, pollutant, pollutant_df):
        ef = pollutant_df[pollutant_df['POLLUTANT'] == pollutant]['EMISSION FACTOR'].iloc[0]
        # Emissions in lbs
        df[f'E_{pollutant}'] = ((((df['SQFT'] * df['FRAME_FACTOR']) + (df['SQFT'] * df['CONTENTS_FACTOR'])) / 2000) * (df['CONSUMPTION_FACTOR']) * ef)
        return df
    
    for species in available_pollutants:
        calculate_emissions(structure_df, species, EF)

    geom_col = structure_df.geometry.name if 'geometry' in structure_df.columns or isinstance(structure_df, gpd.GeoDataFrame) else None
    structure_df.columns = [col.upper() if col != geom_col else col for col in structure_df.columns]

    structure_df = structure_df.rename(columns={
    "CLEAN_DATE": "START_DATE",
    #"CO_NAME": "COUNTY",
    "BASIN_NAME": "AIR_BASIN",
    "DIS_NAME": "AIR_DISTRICT",
    "GLOBALID": "GLOBALID_DINS"
    })

    e_columns = [col for col in structure_df.columns if col.startswith('E_')]
    new_columns = {col: f"{col}_TN" for col in e_columns}
    
    for col in e_columns:
        structure_df[f"{col}_TN"] = structure_df[col] / 2000
        structure_df[f"{col}_TN"] = structure_df[f"{col}_TN"].round(3)

    structure_df = structure_df.drop(columns=e_columns)
    tn_columns = [col for col in structure_df.columns if col.startswith('E_') and col.endswith('_TN')]

    out_cols = [
        'INCIDENTNAME', 'INCIDENTNUM', 'START_DATE', 'GLOBALID_DINS', 'DAMAGE',
        'STRUCTURETYPE', 'STRUCTURECATEGORY', 'CAT', 'SQFT', 'SQFT_SOURCE',
        'COUNTY', 'AIR_BASIN', 'AIR_DISTRICT', 'COABDIS', 'CONSUMPTION_FACTOR',
        'FRAME_FACTOR', 'CONTENTS_FACTOR', 'geometry'
    ]

    selected_out_cols = [col for col in out_cols if col in structure_df.columns] + tn_columns
    emissions_gdf = structure_df[selected_out_cols]
    
    if not isinstance(emissions_gdf, gpd.GeoDataFrame):
        emissions_gdf = gpd.GeoDataFrame(emissions_gdf, geometry='geometry')

    # cols = [col for col in emissions_gdf.columns if col != 'geometry']
    # emissions_gdf = structure_df[cols + ['geometry']]
    return emissions_gdf