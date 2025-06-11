import os
import geopandas as gpd
import pandas as pd

from typing import Literal, Optional, Union, List  # typing imports
from dotenv import load_dotenv
load_dotenv() 

from sweep import config
from sweep.predictor_parcels import GetParcels, ParcelHandler, AOIProcessor
from sweep.emissions import estimate_emissions
from sweep.aggregate import aggregated_report
from sweep.vehicles import vehicle_calculator
from sweep.write_outputs import write_outputs

def sweep_predictor(
    aoi_source: Union[str, gpd.GeoDataFrame],
    api_key: str,
    ratio_destroyed: float = 1.0,
    write: Literal["YES", "NO"] = "YES",
    ef_choice: Literal["HOLDER", "CARB", "OTHER"] = "HOLDER",
    frame_factor: Optional[Union[Literal["HOLDER", "CARB"], float]] = "HOLDER",
    contents_factor: Optional[Union[Literal["HOLDER", "CARB"], float]] = "HOLDER",
    structure_consumption: Optional[Literal["HOLDER", "CARB", "DINS3", "DINS5"]] = "DINS3",
    user_efs: Optional[str] = None,
    vehicle_ef_choice: Literal["HOLDER", "CARB", "OTHER"] = "CARB",
    pollutants: Optional[Union[Literal["ALL"], str, List[str]]] = None,
    vehicle_count_or_ratio: Literal["RATIO", "COUNT"] = "RATIO",
    vehicle_cr_value: float = 1.44,
    vpollutants: Optional[Union[Literal["ALL"], str, List[str]]] = None,
    aggregate_fields: Optional[List[str]] = None
) -> tuple[gpd.GeoDataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Main workflow for estimating emissions and vehicle impacts from a user-supplied AOI.

    This function processes an Area of Interest (AOI) — either from file or in-memory GeoDataFrame — 
    and returns predicted emissions, aggregated summaries, and vehicle-related emissions.

    Parameters
    ----------
    aoi_source : str or GeoDataFrame
        Path to a polygon shapefile/GeoPackage, or a GeoDataFrame of polygon geometry.

    api_key : str
        API key required for parcel data lookup for the Lightbox Parcel API.

    ratio_destroyed : float, optional
        Proportion of points to label as "Destroyed (>50%)" (default is 1.0). 
        If another value is provided, the proportion of points destroyed will be a random subset.

    write : {"YES", "NO"}, default="YES"
        If "YES", writes the predicted emissions and reports to disk.

    ef_choice : {"HOLDER", "CARB", "OTHER"}, default="HOLDER"
        Source of structure emission factors.

    pollutants : list of str, optional
        List of pollutant names to include or "All". If None, uses the default from config.

    aggregate_fields : list of str, optional
        Fields by which to group emission results (e.g., "county", "aoi_index").
        Defaults to ["county", "aoi_index"] if None.

    vehicle_ef_choice : {"HOLDER", "CARB", "OTHER"}, default="CARB"
        Source of vehicle emission factors.

    vpollutants : str or list of str, optional
        Pollutants to use for vehicle emissions. Use "ALL" or a list of pollutants.
        If None, defaults to config.vpollutants_default.

    vehicle_count_or_ratio : {"RATIO", "COUNT"}, default="RATIO"
        Whether vehicle emissions are based on a ratio to structures or a fixed count.

    vehicle_cr_value : float, default=1.44
        Value for ratio (vehicles per structure) or a fixed count per structure.

    Returns
    -------
    predicted_emissions_gdf : GeoDataFrame
        Structure-level emissions estimates with geometry and pollutant columns.

    agg_table : DataFrame
        Emissions aggregated by the specified fields.

    vehicle_table : DataFrame
        Emissions from vehicles, based on the specified count or ratio.

    Notes
    -----
    - Writing outputs is handled via the `write_outputs` module if `write="YES"`.
    - Pollutants and grouping fields are validated internally.
    """

    if pollutants is None:
        pollutants = ["CO", "NOx", "SOx", "PM", "TOG"]

    if vpollutants is None:
        vpollutants = ['CO', 'NOx', 'SOx', 'PM']

    if aggregate_fields is None:
        aggregate_fields = ['AOI_INDEX']   

    VALID_AGG_FIELDS = {
    "YEAR", "MONTH", "INCIDENT", "COABDIS", "COUNTY",
    "AIR DISTRICT", "AIR DISTRICT ID", "AIR BASIN", "AOI_INDEX"
    }

    for field in aggregate_fields:
        if field.upper() not in VALID_AGG_FIELDS:
            raise ValueError(f"Invalid aggregate field: {field}. Must be one of: {sorted(VALID_AGG_FIELDS)}")

    print("Fetching parcel data...")
    parcel_parser = GetParcels(aoi_source, api_key)
    parcel_gdf = parcel_parser.fetch_parcels_for_aoi(query_type="parcels")
    assmt_gdf = parcel_parser.fetch_parcels_for_aoi(query_type="assessments")

    print("Processing parcels...")
    parcel_handler = ParcelHandler(aoi_source, parcel_gdf, assmt_gdf)
    aoi_points = parcel_handler.process_parcels()

    print("Generating synthetic BSDB...")
    processor = AOIProcessor()
    aoi_bsdb = processor.prep_dataset(aoi_points, ratio_destroyed)

    print(f"Estimating emissions for pollutants: {pollutants}...")
    predicted_emissions_gdf = estimate_emissions(
        structure_df=aoi_bsdb,
        ef_choice=ef_choice,
        frame_factor=frame_factor,
        contents_factor=contents_factor,
        structure_consumption=structure_consumption,
        sqft_choice=None,
        user_efs=user_efs,
        pollutants=pollutants
    )

    print(f"Aggregating report by: {aggregate_fields}...")
    agg_table = aggregated_report(predicted_emissions_gdf, aggregates=aggregate_fields)

    print(f"Calculating vehicle emissions with {vehicle_ef_choice} factors...")
    vehicle_table = vehicle_calculator(
        predicted_emissions_gdf,
        count_or_ratio=vehicle_count_or_ratio,
        cr_value=vehicle_cr_value,
        vef_choice=vehicle_ef_choice,
        vpollutants=vpollutants,
    )

    if write.upper() == "YES":
        print("Writing outputs to disk...")
        write_outputs(
            predicted_emissions_gdf,
            suffix=None,
            aggregated_report=agg_table,
            vehicle_report=vehicle_table,
            spatial=True,
            spatial_type="GPKG",
        )

    print("Processing complete.")
    return predicted_emissions_gdf, agg_table, vehicle_table