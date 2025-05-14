import scripts.config as config
import scripts.aoi_handler as AOI
import scripts.emissions as EE
import scripts.aggregate as AGG
import scripts.vehicles as VEH
import scripts.write_outputs as OUT

def main(aoi_path, write = "YES"):
    """
    Main processing workflow for estimating emissions from an AOI.

    Parameters:
    -----------
    aoi_path : str
        File path to the AOI polygon shapefile.
    write : str, optional
        If "YES" (default), writes output files to disk.

    Returns:
    --------
    predicted_emissions_gdf : GeoDataFrame
        GeoDataFrame of predicted emissions for AOI parcels.
    agg_table : DataFrame
        Aggregated emissions report by specified groups (e.g., county).
    vehicle_table : DataFrame
        Calculated vehicle-related emissions or ratios.

    Workflow steps:
    ---------------
    1. Extract parcel data within the AOI bounding box.
    2. Create a synthetic burned structure database (BSDB) based on AOI parcels.
    3. Estimate emissions using chosen emission factors and pollutants.
    4. Aggregate emissions data by spatial or administrative units.
    5. Calculate vehicle-related emissions or ratios.
    6. Optionally write outputs to disk.
    """

     # 1. Extract parcel data and points inside AOI bounding box
    aoi_handler = AOI.AOIParcels(config.demo_aoi_path)
    aoi_parcels, aoi_points = aoi_handler.aoi_parcels_from_bbox()

    # 2. Generate synthetic BSDB (Burned Structure Database) from AOI points
    processor = AOI.AOIProcessor()
    aoi_bsdb = processor.run_all(aoi_points, ratio_destroyed=1.0)

    # 3. Estimate emissions from BSDB using Holder emission factors for selected pollutants
    predicted_emissions_gdf = EE.estimate_emissions(
        aoi_bsdb,
        ef_choice="HOLDER",             # Emission factor choice
        pollutants=["CO", "NOx", "PO"]  # List of pollutants to calculate
    )

    # 4. Aggregate emissions by county (or other specified groups)
    agg_table = AGG.aggregated_report(
        predicted_emissions_gdf, 
        aggregates = ["county"])

    # 5. Calculate vehicle-related emissions or ratios using CARB vehicle emission factors
    vehicle_table = VEH.vehicle_calculator(
        predicted_emissions_gdf,
        count_or_ratio="RATIO",  # Use ratio-based method for vehicle calc
        cr_value=1.44,           # Ratio of people per vehicle
        vef_choice="CARB",       # Vehicle emission factors source
        vpollutants="ALL"        # Calculate for all pollutants
    )
    
    # 6. Write spatial and tabular outputs to disk if requested
    if write.upper() == "YES":
        # 6. Write outputs
        OUT.write_outputs(
            predicted_emissions_gdf,
            suffix=None,
            aggregated_report=agg_table,
            vehicle_report=vehicle_table,
            spatial=True,             # Include spatial output
            spatial_type="GPKG"       # Select spatial write type
        )
    return predicted_emissions_gdf, agg_table, vehicle_table

if __name__ == "__main__":
    predicted_emissions_gdf, agg_table, vehicle_table = main(aoi_path)
    print("Run complete. Emissions GeoDataFrame preview:")
    print(predicted_emissions_gdf.head())
