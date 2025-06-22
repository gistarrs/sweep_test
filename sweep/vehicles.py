import numpy as np
import os
import pandas as pd

from typing import Literal, Optional, Union, List

from sweep import config

def vehicle_calculator(
    structure_df: pd.DataFrame,
    count_or_ratio: Literal["RATIO", "COUNT"] = "RATIO",
    cr_value: float = 1.44,
    vef_choice: Literal["HOLDER", "CARB", "OTHER"] = "HOLDER",
    user_vefs: Optional[str] = None,
    vpollutants: Union[str, List[str]] = config.vpollutants_default,
    ef_folder: str = config.ef_folder
) -> pd.DataFrame:

    """
    Calculates emissions for vehicles based user-provided count or 
    ratio of vehicles-to-structures impacted by fire.

    Parameters:
    -----------
    df : pandas.DataFrame
        Input DataFrame containing structure data (BSDB).

    vef_choice : str
        Choice of emission factors dataset. Options:

        - "HOLDER": Emission factors from Holder et al. (2023)
        - "CARB": Emission factors from CARB's internal 1999 process
        - "OTHER": User provides a custom emissions factors path via `user_vefs`

    count_or_ratio : str
        Method for estimating number of vehicles. Options:

        - "RATIO": Default. User will supply ratio of vehicles to structures destroyed.
        - "COUNT": User will supply count of vehicles estimated to be destroyed.
    
    cr_value: float
        float: User-specified count or ratio (vehicles to structures).

    user_vefs : str, optional
        Path to user-supplied emission factors file if vef_choice= "OTHER".
        
    vpollutants : str
        Pollutant species. Options:

        - Comma-separated list of pollutants to calculate
        - Default: ["CO", "NOx", "SOx", "PM", "TOG"]
        - "ALL": all available pollutants from specified ef_choice.

    Returns:
    --------
    pandas.DataFrame
        Dataframe with estimated emissions from vehicles consumed by fire.

    Example
    -------
    >>> vehicle_calculator(emissions_gdf, "RATIO", 1.44, vef_choice = "CARB", vpollutants = "ALL")
    >>> vehicle_calculator(emissions_gdf, "RATIO", 1.44, vef_choice = "HOLDER", vpollutants = ["CO"])
    >>> vehicle_calculator(emissions_gdf, "COUNT", 1024, vef_choice = "OTHER",  vpollutants = "ALL", user_vefs = r"C:/data/efs/custom_emissions_factors.xlsx")
    
    """
    count_or_ratio = count_or_ratio.upper()

    if count_or_ratio == "COUNT":
        n_vehicles = pd.to_numeric(cr_value, errors='coerce')
        print("Count provided:", n_vehicles, "vehicles.")
    elif count_or_ratio == "RATIO":
        n_destroyed = len(structure_df[structure_df['CONSUMPTION_FACTOR'] > 0.5])
        structure_to_vehicle_n = pd.to_numeric(cr_value, errors='coerce')
        n_vehicles = n_destroyed*structure_to_vehicle_n
        print("Ratio provided:", round(n_vehicles, 2), "vehicles estimated using ratio:", cr_value)

    ef_choice = vef_choice.upper()
    if "HOLDER" in ef_choice:
        ef_path = os.path.join(ef_folder, "Holder_EFs.xlsx")
        print("Holder efs from:", ef_path)
    elif ef_choice == "CARB":
        ef_path = os.path.join(ef_folder, "CARB_EFs.xlsx")
        print("CARB efs from:", ef_path)
    elif ef_choice == "OTHER":
        ef_path = user_vefs
        print("User-speficied emissions factors from:", ef_path)

    print("Requested pollutants:", vpollutants)        
    vef_df = pd.read_excel(ef_path)        
    vef_df.columns = vef_df.columns.str.upper()  # Ensure column names are uppercase
    vef_df['VEHICLES'] = n_vehicles
    
    if 'VEHICLE_GFIRE' not in vef_df.columns:
        if 'VEHICLE_GKG' in vef_df.columns:
            vef_df['VEHICLE_GFIRE'] = vef_df['VEHICLE_GKG'] * 461  # Multiply by 461 as specified

    if vpollutants == "ALL" or vpollutants == "All" or vpollutants == "all":
        VEF = vef_df.copy()
    else:
        VEF = vef_df[vef_df['POLLUTANT'].isin(vpollutants)].copy()

    VEF = VEF[VEF['VEHICLE_GFIRE'].notna()]

    available_pollutants = VEF['POLLUTANT'].unique()
    print("Returned pollutants:", available_pollutants)

    VEF['EMISSION FACTOR'] = VEF['VEHICLE_GFIRE']
    VEF['TOTAL_VEHICLE_EMISSIONS_KG'] = round(VEF['VEHICLE_GFIRE'] * n_vehicles/1000, 2)
    VEF['TOTAL_VEHICLE_EMISSIONS_TN'] = round(VEF['TOTAL_VEHICLE_EMISSIONS_KG']/907.2, 2)

    vehicle_cols = ['POLLUTANT', 'VEHICLE_GFIRE', 'VEHICLE_GKG', 'VEHICLES', 'TOTAL_VEHICLE_EMISSIONS_G', 'TOTAL_VEHICLE_EMISSIONS_TN']
    VE_OUT = VEF[[col for col in vehicle_cols if col in VEF.columns]]
    return VE_OUT