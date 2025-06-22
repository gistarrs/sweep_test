import geopandas as gpd
import numpy as np
import os
import pandas as pd

from typing import Literal, Optional, Union, List

from sweep import config

def aggregated_report(
    emissions_gdf: gpd.GeoDataFrame,
    aggregates: Optional[List[str]] = None
) -> pd.DataFrame:
    """
    Generate an aggregated emissions summary report by specified groupings.

    This function processes a GeoDataFrame of per-structure emissions and returns a summary 
    aggregated by one or more user-specified fields (e.g., 'YEAR', 'MONTH', 'INCIDENT').
    The summary includes totals of all fields starting with 'E_' and a count of structures 
    with a `CONSUMPTION_FACTOR` greater than zero.

    Parameters
    ----------
    emissions_gdf : geopandas.GeoDataFrame
        A GeoDataFrame containing structure-level emissions data. Must include at least:
            - 'START_DATE' (datetime or string convertible to datetime)
            - 'CONSUMPTION_FACTOR' (numeric)
            - One or more columns starting with 'E_' for emissions values.
    
    aggregates : list of str, optional
        A list of high-level grouping keys for the report. Valid values include:
            - 'YEAR', 'MONTH', 'INCIDENT', 'COABDIS', 'COUNTY',
              'DISTRICT', 'DISTRICT ID', 'AIR BASIN', 'AOI_INDEX'
        If None or empty, defaults to ['YEAR', 'INCIDENT'] (or AOI_INDEX for predictor).
        If 'MONTH' is specified but 'YEAR' is not, 'YEAR' will be automatically included.

    Returns
    -------
    pandas.DataFrame
        A DataFrame containing aggregated emissions values and a count of damaged structures 
        (where CONSUMPTION_FACTOR > 0) for each group. All numeric outputs are rounded to 2 decimals.
        The DataFrame includes:
            - Selected grouping columns
            - All 'E_' emissions columns
            - 'DAMAGED_STRUCTURES' column
        Incidents with no damaged structures are excluded.

    Notes
    -----
    - Unrecognized aggregate fields are ignored with a warning.
    - The output is sorted by the grouping columns in a consistent order.
    """
    
    e_columns = [col for col in emissions_gdf.columns if col.startswith('E_')]
    emissions_gdf['START_DATE'] = pd.to_datetime(emissions_gdf['START_DATE'])
    emissions_gdf['MONTH'] = emissions_gdf['START_DATE'].dt.month
    emissions_gdf['YEAR'] = emissions_gdf['START_DATE'].dt.year

    aggregate_cols = {
        "INCIDENT": ['INCIDENTNAME', 8],
        "MONTH": ['MONTH', 7],
        "YEAR": ['YEAR', 6],
        "COABDIS" : ['COABDIS', 5],
        "COUNTY": ['COUNTY', 4], 
        "AIR DISTRICT": ['AIR_DISTRICT', 3], 
        "AIR DISTRICT ID": ['DISA_ID', 3], 
        "AIR BASIN": ['AIR_BASIN', 2],
        "AOI_INDEX": ['AOI_INDEX', 8]
    }
    
    # Check if aggregate is None or an empty string
    if not aggregates:
        aggregates = ['YEAR', 'INCIDENT']
        print("Default aggregates (YEAR and INCIDENT) used.")
    else:
        # Ensure all items in aggregates are uppercase
        aggregates = [agg.upper() if isinstance(agg, str) else agg for agg in aggregates]

        # Add 'YEAR' if 'MONTH' is selected but 'YEAR' is missing
        if "MONTH" in aggregates and "YEAR" not in aggregates:
            aggregates.append("YEAR")
    
    group_columns = []    
    for aggregate in aggregates:
        if aggregate in aggregate_cols:
            group_columns.append(aggregate_cols[aggregate])
        else:
            print(f"Warning: Unknown aggregate '{aggregate}' ignored.")

    # Sort group columns based on predefined order
    group_columns = sorted(group_columns, key=lambda x: x[1])
    sorted_columns = [col[0] for col in group_columns]
        
    # Perform aggregation based on the group columns
    agg_df = emissions_gdf.groupby(sorted_columns).sum(numeric_only=True)

    # Count the number of structures where CONSUMPTION_FACTOR > 0
    impacted_structures = emissions_gdf[emissions_gdf['CONSUMPTION_FACTOR'] > 0] \
        .groupby(sorted_columns).size().reset_index(name='DAMAGED_STRUCTURES')

    # Merge the impacted structures count back into the aggregated dataframe
    # Retain only the group columns and E_ columns in the output and round
    agg_df = agg_df.merge(impacted_structures, on=sorted_columns, how='left')
    retained_columns = sorted_columns + e_columns + ['DAMAGED_STRUCTURES']
    agg_df = agg_df[agg_df.columns.intersection(retained_columns)]
    agg_df = round(agg_df, 2)

    # Sort the final output by the grouped columns
    agg_out = agg_df.sort_values(sorted_columns)

    # Reset index if necessary to include group columns as regular columns
    # Remove incidents where no structures were actually damaged from report.
    agg_out = agg_out[agg_out['DAMAGED_STRUCTURES'] > 0]
    agg_out = agg_out.reset_index(drop=True)

    return agg_out