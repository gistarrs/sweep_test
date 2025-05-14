import scripts.config as config
import scripts.get_bsdb as GET
import scripts.filters as FILTER
import scripts.emissions as EE
import scripts.aggregate as AGG
import scripts.vehicles as VEH
import scripts.write_outputs as OUT

def main(write = "NO"):
    """
    Main workflow for retrieving, filtering, and processing BSDB data
    to estimate and summarize emissions.

    Parameters:
    -----------
    write : str, optional
        If "YES", writes output files (spatial and tabular) to disk. Default is "NO".

    Returns:
    --------
    emissions_gdf : GeoDataFrame
        GeoDataFrame of estimated emissions after filtering.
    agg_table : DataFrame
        Aggregated emissions report grouped by specified attributes.
    vehicle_table : DataFrame
        Vehicle-related emissions or counts based on emissions data.

    Workflow steps:
    ---------------
    1. Load the Burned Structure Database (BSDB) from GeoJSON (or API on first run).
    2. Filter BSDB interactively or by specified criteria.
    3. Estimate emissions using selected emission factors and pollutants.
    4. Aggregate emissions by county (or other specified units).
    5. Calculate vehicle-related emissions or ratios.
    6. Optionally write the outputs to disk.
    """
    
    # 1. Load or "get" BSDB.
    # Fetch via API on first use, geojson for repeat runs)
    bsdb_df = GET.get_BSDB("geojson").bsdb_df

    # 2. Apply filters to the BSDB data
    # Interactive filtering enabled will ignore other filter options are ignored
    filt_bsdb = FILTER.filter_bsdb(
        df = bsdb_df, 
        filter_method = "interactive", 
        apply_date_filter = True, 
        start_date = "2021-02-02", 
        end_date = "2022-02-02", 
        filter_field = "COUNTY", 
        field_values = ["MARIPOSA"]
    )

    # 3. Estimate emissions using specified emission factor source and pollutants
    emissions_gdf = EE.estimate_emissions(
        filt_bsdb,
        ef_choice="HOLDER",             # Emission factor choice
        pollutants=["CO", "NOx", "PO"]  # List of pollutants to calculate
    )

    # 4. Aggregate emissions by spatial group (e.g., county)
    agg_table = AGG.aggregated_report(
        emissions_gdf, 
        aggregates = ["county"])

    # 5. Estimate potential emissions from vehicles damaged by fire.
    vehicle_table = VEH.vehicle_calculator(
        emissions_gdf,
        count_or_ratio="RATIO",  # Use ratio-based method for vehicle calc
        cr_value=1.44,           # Ratio of vehicles to structures
        vef_choice="CARB",       # Vehicle emission factors source
        vpollutants="ALL"        # Calculate for all pollutants
    )

    # 6. Optionally write all outputs to disk
    if write.upper() == "YES":
        OUT.write_outputs(
            emissions_gdf,
            suffix=None,
            aggregated_report=agg_table,
            vehicle_report=vehicle_table,
            spatial=True,             # Include spatial output
            spatial_type="GPKG"       # Select spatial write type
        )
    return emissions_gdf, agg_table, vehicle_table

if __name__ == "__main__":
    emissions_gdf, agg_table, vehicle_table = main()
    print("Run complete. Emissions GeoDataFrame preview:")
    print(emissions_gdf.head())
