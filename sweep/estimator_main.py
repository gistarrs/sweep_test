import os
import geopandas as gpd
import pandas as pd

from datetime import datetime
from typing import Literal, Optional, Union, List  # typing imports
from dotenv import load_dotenv
load_dotenv() 

from sweep import config
from sweep.get_bsdb import GetBSDB
from sweep.filters import filter_bsdb
from sweep.emissions import estimate_emissions
from sweep.aggregate import aggregated_report
from sweep.vehicles import vehicle_calculator
from sweep.write_outputs import write_outputs

def sweep_estimator(
    get_mode: Literal["use_default", "use_custom", "refresh"] = "use_default",
    org: Literal["CARB", "IGIS"] = "CARB",
    write: Literal["YES", "NO"] = "YES",
    custom_filename: Optional[str] = None,
    filter_method: Literal["Interactive", "Automated", "Spatial"] = "Interactive",
    filter_field: Optional[config.FilterField] = "Wildfire Name",
    field_values: Optional[List[Union[str, int]]] = None,
    apply_date_filter: bool = False,
    start_date: Optional[Union[str, datetime]] = None,
    end_date: Optional[Union[str, datetime]] = None,
    polygon_input: Optional[Union[str, gpd.GeoDataFrame]] = None,
    geometry_col: str = "geometry",
    ef_choice: Literal["HOLDER", "CARB", "OTHER"] = "HOLDER",
    user_efs: Optional[str] = None,
    frame_factor: Optional[Union[Literal["HOLDER", "CARB"], float]] = "HOLDER",
    contents_factor: Optional[Union[Literal["HOLDER", "CARB"], float]] = "HOLDER",
    structure_consumption: Optional[Literal["HOLDER", "CARB", "DINS3", "DINS5"]] = "DINS3",
    vehicle_ef_choice: Literal["HOLDER", "CARB", "OTHER"] = "CARB",
    user_vefs: Optional[str] = None,
    pollutants: Optional[Union[Literal["ALL"], str, List[str]]] = None,
    vehicle_count_or_ratio: Literal["RATIO", "COUNT"] = "RATIO",
    vehicle_cr_value: float = 1.44,
    vpollutants: Optional[Union[Literal["ALL"], str, List[str]]] = None,
    aggregate_fields: Optional[List[str]] = None
) -> tuple[gpd.GeoDataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Main workflow for retrieving, filtering, and processing Burned Structure Database (BSDB) data
    to estimate structure fire emissions, generate summary statistics, and calculate vehicle equivalents.

    Parameters
    ----------
    get_mode : {'use_default', 'use_custom', 'refresh'}, default='use_default'
        Determines how the BSDB is loaded:
        - 'use_default': load cached data from default location.
        - 'use_custom': load from `custom_filename`.
        - 'refresh': pull new data from the API and update cache.

    org : {'CARB', 'IGIS'}, default='CARB'
        Indicates which organization's configuration settings to use (e.g., filtering fields, paths).

    write : {'YES', 'NO'}, default='YES'
        If 'YES', writes outputs to disk in spatial and tabular formats.

    custom_filename : str, optional
        Path to a custom BSDB input file (GeoJSON or GPKG), used when `get_mode='use_custom'`.

    filter_method : {'Interactive', 'Automated', 'Spatial'}, default='Interactive'
        Method used to filter the BSDB:
        - 'Interactive': prompts user to select values.
        - 'Automated': filters by supplied values in `filter_field` and `field_values`.
        - 'Spatial': uses geometry from `polygon_input`.

    filter_field : str, optional
        The field to filter on (e.g., "Wildfire Name", "Incident", "County"). Required for non-spatial filters.

    field_values : list of str or int, optional
        Values to filter on in `filter_field`. Used only with 'Automated' filter method.

    apply_date_filter : bool, default=False
        Whether to filter incidents by start and end date.

    start_date : str or datetime, optional
        Start date for filtering (inclusive), used only when `apply_date_filter=True`.

    end_date : str or datetime, optional
        End date for filtering (inclusive), used only when `apply_date_filter=True`.

    polygon_input : str or GeoDataFrame, optional
        Input geometry used for spatial filtering (e.g., fire perimeter or AOI polygon).

    geometry_col : str, default='geometry'
        Name of the geometry column in `polygon_input` if provided as a GeoDataFrame.

    ef_choice : {'HOLDER', 'CARB', 'OTHER'}, default='HOLDER'
        Emission factor source for estimating emissions.

    frame_factor : {'HOLDER', 'CARB'} or float, default='HOLDER'
        Frame fuel load factor (kg/m²). Use standard presets or a custom numeric value.

    contents_factor : {'HOLDER', 'CARB'} or float, default='HOLDER'
        Contents fuel load factor (kg/m²). Use standard presets or a custom numeric value.

    structure_consumption : {'HOLDER', 'CARB', 'DINS3', 'DINS5'}, default='DINS3'
        Method for estimating percentage of structure consumed by fire.

    user_efs : str, optional
        Path to a custom CSV file defining emission factors.

    vehicle_ef_choice : {'HOLDER', 'CARB', 'OTHER'}, default='CARB'
        Emission factor source for calculating vehicle equivalents.

    pollutants : list of str or str or 'ALL', optional
        List of pollutants to estimate (e.g., ['CO', 'PM']). If None, uses default list.

    vehicle_count_or_ratio : {'RATIO', 'COUNT'}, default='RATIO'
        Whether to return vehicle equivalents as a count or ratio of emissions.

    vehicle_cr_value : float, default=1.44
        Ratio of vehicle emission contribution used in calculations.

    vpollutants : list of str or str or 'ALL', optional
        Pollutants to include in vehicle emissions calculations. If None, uses a default list.

    aggregate_fields : list of str, optional
        Fields to use for aggregating emissions output (e.g., ['YEAR', 'COUNTY']).
        Must be a subset of: {"YEAR", "MONTH", "INCIDENT", "COABDIS", "COUNTY",
        "AIR DISTRICT", "AIR DISTRICT ID", "AIR BASIN"}.

    Returns
    -------
    emissions_gdf : GeoDataFrame
        Geospatial dataframe of filtered structures with estimated emissions by pollutant.

    agg_table : DataFrame
        Tabular summary of emissions grouped by `aggregate_fields`.

    vehicle_table : DataFrame
        Table showing estimated vehicle emissions or vehicle equivalents.

    Notes
    -----
    This function integrates structure-level emissions estimation with optional filters
    and reporting formats. The entire BSDB dataset is processed through a flexible pipeline
    enabling geographic, temporal, or categorical filters.

    Workflow Steps
    --------------
    1. Load the BSDB dataset.
    2. Apply filtering by attribute, date, or spatial overlay.
    3. Estimate structure emissions based on fuel loads and fire consumption models.
    4. Generate aggregated emissions summaries.
    5. Calculate vehicle equivalents based on selected emission factors.
    6. Optionally export spatial/tabular outputs to disk.
    """

    if pollutants is None:
        pollutants = ["CO", "NOx", "SOx", "PM", "TOG"]
    
    if ef_choice.upper() == "OTHER":
        pollutants = "ALL"

    if vpollutants is None:
        vpollutants = ['CO', 'NOx', 'SOx', 'PM']

    if vehicle_ef_choice.upper() == "OTHER":
        vpollutants = "ALL"

    if aggregate_fields is None:
        aggregate_fields = ['YEAR', 'INCIDENT']   

    VALID_AGG_FIELDS = {
    "YEAR", "MONTH", "INCIDENT", "COABDIS", "COUNTY",
    "AIR DISTRICT", "AIR DISTRICT ID", "AIR BASIN", 'AOI_INDEX'
    }

    for field in aggregate_fields:
        if field.upper() not in VALID_AGG_FIELDS:
            raise ValueError(f"Invalid aggregate field: {field}. Must be one of: {sorted(VALID_AGG_FIELDS)}")

    print(f"Loading BSDB using {get_mode}...")
    bsdb_df = GetBSDB(get_mode, org, custom_filename).bsdb_df

    print("Applying filter criteria...")
    filt_bsdb = filter_bsdb(
        df=bsdb_df,
        filter_method=filter_method,
        filter_field=filter_field,
        field_values=field_values,
        apply_date_filter=apply_date_filter,
        start_date=start_date,
        end_date=end_date,
        polygon_input=polygon_input,
        geometry_col=geometry_col
    )
    if len(filt_bsdb) == 0:
        print("No structures meeting the specified criteria found.")
        return None, None, None

    else:
        print(f"Estimating emissions for pollutants: {pollutants}...")
        emissions_gdf = estimate_emissions(
            structure_df = filt_bsdb,
            ef_choice=ef_choice,
            frame_factor=frame_factor,
            contents_factor=contents_factor,
            structure_consumption=structure_consumption,
            sqft_choice=None,
            user_efs=user_efs,
            pollutants=pollutants
        )

        print(f"Aggregating report by: {aggregate_fields}...")
        agg_table = aggregated_report(emissions_gdf, aggregates=aggregate_fields)

        print(f"Calculating vehicle emissions with {vehicle_ef_choice} factors...")
        vehicle_table = vehicle_calculator(
            emissions_gdf,
            count_or_ratio=vehicle_count_or_ratio,
            cr_value=vehicle_cr_value,
            vef_choice=vehicle_ef_choice,
            user_vefs=user_vefs,
            vpollutants=vpollutants,
        )

        # 6. Optionally write all outputs to disk
        if write.upper() == "YES":
            write_outputs(
                emissions_gdf,
                suffix=None,
                aggregated_report=agg_table,
                vehicle_report=vehicle_table,
                spatial=True,             # Include spatial output
                spatial_type="GPKG"       # Select spatial write type
            )
        return emissions_gdf, agg_table, vehicle_table