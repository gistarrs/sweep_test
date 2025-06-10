# SWEEP: Structure Wildfire Emissions Estimator and Predictor

## Description
SWEEP is designed to estimate emissions from structures damaged or destoryed by wildfire in California.
SWEEP applies filters based on specific criteria (such as date ranges and geographic areas), estimates emissions, and generates aggregated reports on the results. The project utilizes a series of Python scripts, each of which handles a different part of the pipeline (e.g., data retrieval, emissions estimation, aggregation, etc.).

## Table of Contents
- [Installation](#installation)
- [Requirements](#requirements)
- [Usage](#usage)
- [Scripts Overview](#scripts-overview)
- [Sources](#sources)

## Installation

1. Clone this repository to your local machine:

    ```bash
    git clone https://github.com/gistarrs/sweep_test.git
    ```

2. Navigate to the project directory:

    ```bash
    cd sweep_test
    ```

3. Create a virtual environment:

    ```bash
    python -m venv venv
    ```

4. Activate the virtual environment:
   - **Windows**:
     ```bash
     venv\Scripts\activate
     ```
   - **Mac/Linux**:
     ```bash
     source venv/bin/activate
     ```

5. Install the required dependencies:

    ```bash
    pip install -r requirements.txt
    ```

## Requirements
Ensure the following libraries are installed:
- pandas>=1.3.0
- geopandas>=1.0.1
- numpy>=1.21.0
- requests>=2.25.0
- pyogrio>=0.4.0
- shapely>=2.0.0
- openpyxl>=3.0.10
- python-dotenv==1.0.0
- typing_extensions
- matplotlib>=3.0.0

You can install these dependencies by running:

```bash
pip install -r requirements.txt
```

## Running the Estimator

__NOTE: The estimator is intended for internal use by CARB and its partners. Obtaining the BSDB dataset requires a CARB organizational ArcGIS online (AGOL) account.__

This tool estimates structure fire emissions from the California Burned Structures Database (BSDB). It supports flexible filtering (spatial, automated, interactive) and calculates enissions from structures and, roughly, vehicles consumed by wildfire. Users can use pre-set defaults for emissions factors, contents factors, consumption factors, and frame factors or provide their own values.

### How to run the estimator

```bash
from SWEEP_estimator import main
```
#### Interactive query and getting BSDB data
- For an initial run (or when you want to update data), ensure the get_mode is set to "refresh". This will require a CARB AGOL account login. If a filename is not provided for optional argument "custom_filename", a date/time stamp and default filename are used. 
- filter_method = "Interactive" will walk users through the available data and allow them to set nesting filters on county, incident, air basin, air district, and date ranges.
- aggregate_fields allows users to dictate how they want emissions summed up in an aggregated table output ('YEAR', 'MONTH', 'INCIDENT', 'COABDIS', 'COUNTY', 'DISTRICT', 'DISTRICT ID', 'AIR BASIN')
- write: "Yes" or "No". Do users want files written to the output folder or just in memory?

```bash
emissions_gdf, agg_table, vehicle_table = main(
    get_mode="refresh",
    filter_method="Interactive",
    aggregate_fields=["AIR DISTRICT"],
    write = "Yes"
)
```
#### Spatial query
- get_mode "use default" reads the most recent bsdb data saved to the data bsdb_dataset folder (by file name).
- filter_method: setting to "Spatial" will use a file path or geodataframe to estimate emissions for all impacted structures within polygon_input.
- polygon_input:  A path (str) to a .shp or .gpkg or a geodataframe containing a single polygon or multiple polygons (one per row).
- apply_date_filter (True or False) allows users to limit the query to a specific date range set by:
- start_date: "YYYY-MM-DD"
- end_date: "YYYY-MM-DD"
- geometry_col can be used to specify a geometry column if it is not "geometry."
- for spatial queries, aggregate_fields can also include ["AOI_INDEX"], or polygon number, which is automatically assigned.
  
```bash
emissions_gdf, agg_table, vehicle_table = main(
    get_mode="use_default",
    filter_method="Spatial",
    polygon_input = os.path.join(config.demo_dir, "demo_multipoly.shp")
    aggregate_fields=["AIR DISTRICT", "AOI_INDEX]
)
```

#### Automated query
- for those familiar with the tool, this allows users to set the parameters for filter_field, field_values, and date filters without using the interactive tool.
- filter_field: Choose one: ["Wildfire Name", "Incident Number", "County", "Air Basin", "Air District", "CoAbDis Code"] (not case sensitive).
- field_value: The values to filter the selected field by (passed as a list). Example: ["Camp"], ["Butte"], ["Camp", "Woolsey"], ["Napa"], [601], etc.
- apply_date_filter (True or False) allows users to limit the query to a specific date range set by:
- start_date: "YYYY-MM-DD"
- end_date: "YYYY-MM-DD"

```bash
emissions_gdf_auto, agg_table_auto, vehicle_table_auto = main(
    get_mode = "use_default",
    filter_method = "automated",
    filter_field = "Air Basin",
    field_values = ["MOUNTAIN COUNTIES", "SAN JOAQUIN VALLEY"],
    apply_date_filter = True,
    start_date = "2018-01-01",
    end_date = "2021-01-01",
    aggregate_fields=['AIR DISTRICT', 'YEAR', 'INCIDENT'],
    write = "No"
    )
print("Complete!")
```

## Running the Predictor

__NOTE: The predictor is intended for internal use by CARB and requires access to a LightBox API key (ask your CARB GIS contact).__


To execute the full pipeline, run the `SWEEP_predictor.py` script, providing the path to a "Area of Interest" file. This will execute the sequence of functions to retrieve data, apply filters, estimate emissions, aggregate the results, and write the outputs.

### Command to run the predictor:

```bash
python SWEEP_predictor.py
```
You can modify the parameters within config.py, SWEEP_estimator.py, and SWEEP_predictor.py or call specific functions as needed.

### Example Outputs (both Estimator and Predictor):

- Spatial file: Geopackage (gpkg), shapefile (.shp), or geojson containing point emissions data.
- Emissions report: .xlsx of per-structure emissions data.
- Aggregated report: .xlsx of aggregated emissions data.
- Vehicle report: .xslx of estimated emissions from vehicles consumed by fire.

### Scripts Overview:

- config.py

    Contains configuration settings for the project, including any necessary API keys, file paths, or environment-specific settings.
- get_bsdb.py

    Handles the retrieval of BSDB (Base Spatial Data) from the API, loading it into a DataFrame for further processing.

- aoi_handler.py

    Provides classes and methods to extract and process parcel data  intersecting a user-defined Area of Interest (AOI). Generates a synthetic BSDB used by the predictor.
- filters.py

    Applies various filters to the BSDB data, such as date range filtering, geographic filtering (e.g., by county), and other conditions.
- emissions.py

    Estimates emissions based on the filtered BSDB data using emission factors (EF) for various pollutants. The emission factors are selected based on the user's choice.
- aggregate.py

    Aggregates the emissions data according to specified columns (e.g., by county, district, or year), and generates a summarized report.
- vehicles.py

    Calculates vehicle-related emissions, using emission factors and ratios specific to vehicle types.
- write_outputs.py

    Handles the writing of outputs to disk, such as GeoPackages, CSV files, or other formats. The results include both spatial and non-spatial outputs.

## Sources

### Structure Information
- **[CAL FIRE Damage Inspection Data (DINS)](https://data.ca.gov/dataset/cal-fire-damage-inspection-dins-data)**: CAL FIRE damage inspection data from structures impacted by wildland fire.
- **[FEMA building footprint data](https://gis-fema.hub.arcgis.com/pages/usa-structures)**: Federal Emergency Management Agency (FEMA) building footprint database.
- **[Microsoft Building footprints](https://github.com/Microsoft/USBuildingFootprints)**: Microsoft building footprints' public data release.
- **[Lightbox Parcel Data](https://www.lightboxre.com/data/lightbox-parcel-data/)**

### Emissions Estimation
- **[Holder et al. 2023](https://doi.org/10.1093/pnasnexus/pgad186)**: Paper summarizing findings of recent research regarding emissions estimation from structures, including a comprehensive list of pollutant species and emissions factors, contents and frame factors, and estimated damage from fire.
- **[CARB 1999](https://ww2.arb.ca.gov/carb-miscellaneous-process-methodologies-fires)**: California Air Resources Board (CARB) Structural and Automobile Fires document.

### Fire Perimeter Data
- **[CAL FIRE FRAP Historical Fire Perimeters](https://data.ca.gov/dataset/california-historical-fire-perimeters)**: CAL FIRE compilation of historical fire perimeters for California.
- **[WFIG Fire Perimeters](https://data-nifc.opendata.arcgis.com/datasets/nifc::wfigs-current-interagency-fire-perimeters/about)**: Fire perimeters compiled across multiple agencies by the National Interagency Fire Center Wildland Fire Interagency Geospatial Services (WFIGS) Group.

### Administrative Boundaries
- **[CARB CoAbDis](https://ww2.arb.ca.gov/geographical-information-system-gis-library)**: California Air Resources Board (CARB) county, air basin, and air pollution control district boundaries.



