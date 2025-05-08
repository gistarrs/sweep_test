import scripts.config as config
import scripts.get_bsdb as GET
import scripts.filters as FILTER
import scripts.emissions as EE
import scripts.aggregate as AGG
import scripts.vehicles as VEH
import scripts.write_outputs as OUT

def main(write = "YES"):
    # 1. Load BSDB
    # If running for the first time or updating BSDB, use "API".
    # If running on existing BSDB from previous run, use "geojson."
    bsdb_df = GET.get_BSDB("api").bsdb_df

    # 2. Filter
    filt_bsdb = FILTER.filter_bsdb(
        df = bsdb_df, 
        filter_method = "interactive", 
        # if filter_method is "interactive" below fields will be ignored.
        apply_date_filter = True, 
        start_date = "2021-02-02", 
        end_date = "2022-02-02", 
        filter_field = "COUNTY", 
        field_values = ["MARIPOSA"]
    )

    # 3. Estimate Emissions
    emissions_gdf = EE.estimate_emissions(
        filt_bsdb,
        ef_choice="HOLDER",
        pollutants=["CO", "NOx", "PO"]
    )

    # 4. Aggregate
    agg_table = AGG.aggregated_report(
        emissions_gdf, 
        aggregates = ["county"])

    # 5. Vehicles
    vehicle_table = VEH.vehicle_calculator(
        emissions_gdf,
        count_or_ratio="RATIO",
        cr_value = 1.44,
        vef_choice="CARB",
        vpollutants="ALL"
    )

    if write.upper() == "YES":
        # 6. Write outputs
        OUT.write_outputs(
            emissions_gdf,
            suffix=None,
            aggregated_report=agg_table,
            vehicle_report=vehicle_table,
            spatial=True,
            spatial_type="GPKG"
        )
    return emissions_gdf, agg_table, vehicle_table

if __name__ == "__main__":
    emissions_gdf, agg_table, vehicle_table = main()
    print("Run complete. Emissions GeoDataFrame preview:")
    print(emissions_gdf.head())
