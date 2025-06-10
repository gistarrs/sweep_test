# SWEEP: Structure Wildfire Emissions Estimator and Predictor

## Description
SWEEP is designed to estimate emissions from structures damaged or destoryed by wildfire in California.
SWEEP applies filters based on specific criteria (such as date ranges and geographic areas), estimates emissions, and generates aggregated reports on the results. The project utilizes a series of Python scripts, each of which handles a different part of the pipeline (e.g., data retrieval, emissions estimation, aggregation, etc.).

## Table of Contents
- [Installation](#installation)
- [Requirements](#requirements)
- [Running the Estimator](#running-the-estimator)
- [Running the Predictor](#running-the-predictor)
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

This tool estimates structure fire emissions from the California Burned Structures Database (BSDB). It supports flexible filtering modes—interactive, spatial, and automated—and calculates emissions from destroyed structures, as well as estimates for vehicles consumed by wildfire.

Users can rely on built-in defaults for emission factors (EFs), frame/contents fuel load factors, and consumption factors, or supply custom values for each.

### Importing the estimator

```bash
from SWEEP_estimator import main
```

### General Parameters

#### Getting BSDB Data and Writing Outputs
Regardless of the query type, users will need to specify get_mode in all queries.
- get_mode: Literal["refresh", "use_default", "use_custom"] = "use_default".

      - "refresh" downloads the latest BSDB dataset and requires a CARB ArcGIS Online login. If custom_filename is not provided, a default name (bsdb_data_timestamped) is used.
      - "use_default" can be used once a local bsdb is written to access the locally saved bsdb.
      - "use_custom": loads a file specified by custom_filename.
  
- custom_filename: str. If get_mode = "refresh", writes BSDB from API query to custom_filename in bsdb_dataset folder. If get_mode = "use_custom", reads from custom_filename in bsdb_dataset folder.
- write: Literal["YES", "NO"] = "YES".  "Yes" to saves outputs to disk in the outputs folder, or "NO" doesn't write.

#### Emissions Estimation Parameters
- ef_choice: Literal["HOLDER", "CARB", "OTHER"] = "HOLDER".  Choice of emission factors dataset:
  
        - "HOLDER": Emission factors from Holder et al. (2023)
        - "CARB": Emission factors from CARB's internal 1999 process
        - "OTHER": User provides a custom emissions factors path via `user_efs`
  
- frame_factor: Optional[Union[Literal["HOLDER", "CARB"], float]] = "HOLDER". Choice of frame factor source:

        - "HOLDER": Use Holder et al. (2023) frame factor
        - "CARB": Use CARB frame factor
        - float: User-specified numeric frame factor
  
- contents_factor: Optional[Union[Literal["HOLDER", "CARB"], float]] = "HOLDER". Choice of contents factor source:
  
        - "HOLDER": Use Holder et al. (2023) contents factor
        - "CARB": Use CARB contents factor
        - float: User-specified numeric contents factor

- structure_consumption: Optional[Literal["HOLDER", "CARB", "DINS3", "DINS5"]] = "DINS3". Determines how to convert damage inspection damage bins into consumption factors.

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
  
- pollutants: Optional[Union[Literal["ALL"], str, List[str]]] = None. Either "All", None (uses the default, criteria pollutants), or takes a list of pollutants ["CO", "NOx"].

- user_efs: Optional[str] = None. Path to emissions factors .xlsx file if users choose ef_choice "OTHER". Requires "Pollutant" and "Structure_gkg" columns.

- vehicle_ef_choice: Literal["HOLDER", "CARB", "OTHER"] = "CARB". Choice of vehicle emission factors dataset:

        - "HOLDER": Emission factors from Holder et al. (2023)
        - "CARB": Emission factors from CARB's internal 1999 process
        - "OTHER": User provides a custom emissions factors path via `user_vefs`
  
- vpollutants: Optional[Union[Literal["ALL"], str, List[str]]] = None. Either "All", None (uses the default, criteria pollutants), or takes a list of pollutants ["CO", "NOx"].

- user_vefs: Optional[str] = None. Path to emissions factors .xlsx file if users choose vef_choice "OTHER". Requires "Pollutant" and "Vehicle_gkg" columns.

- vehicle_count_or_ratio: Literal["RATIO", "COUNT"] = "RATIO". Method for estimating number of vehicles. Options:

        - "RATIO": Default. User will supply ratio of vehicles to structures destroyed.
        - "COUNT": User will supply count of vehicles estimated to be destroyed.
  
- vehicle_cr_value: float = 1.44, User-specified ratio (vehicles to structures) if vehicle_count_or_rato = "RATIO" or absolute count (if vehicle_count_or_rato = "COUNT")

### Query Types
#### Interactive query
Use this option to explore and filter the BSDB through guided prompts.

Key Parameters:
- filter_method="Interactive": Enables step-by-step filtering by county, incident, air basin, air district, and date range.
- aggregate_fields: Grouping fields for the emissions summary. Options include:
["YEAR", "MONTH", "INCIDENT", "COABDIS", "COUNTY", "AIR DISTRICT", "AIR DISTRICT ID", "AIR BASIN"]. Defaults to ['YEAR', 'INCIDENT'].

```bash
emissions_gdf, agg_table, vehicle_table = main(
    get_mode="refresh",
    filter_method="Interactive",
    aggregate_fields=["AIR DISTRICT"],
    write = "Yes"
)
```

#### Spatial query
Use a polygon shapefile or GeoDataFrame to select structures within specific geographic areas.

Key Parameters:
- filter_method="Spatial": Filters data based on the spatial extent of polygon_input.
- polygon_input: Path to a shapefile or GeoPackage, or a GeoDataFrame with one or more polygons.
- apply_date_filter: Optional boolean to apply a date range filter.
- start_date: String or datetime object in "YYYY-MM-DD" format, applied if apply_date_filter == True.
- end_date: String or datetime object in "YYYY-MM-DD" format, applied if apply_date_filter == True.
- geometry_col: Name of the geometry column if not "geometry".
- aggregate_fields: - aggregate_fields: Grouping fields for the emissions summary. Options include:
["YEAR", "MONTH", "INCIDENT", "COABDIS", "COUNTY", "AIR DISTRICT", "AIR DISTRICT ID", "AIR BASIN", "AOI_INDEX"]. Defaults to ['YEAR', 'INCIDENT']
  
```bash
emissions_gdf, agg_table, vehicle_table = main(
    get_mode="use_default",
    filter_method="Spatial",
    polygon_input = os.path.join(config.demo_dir, "demo_multipoly.shp")
    aggregate_fields=["AIR DISTRICT", "AOI_INDEX]
)
```

#### Automated query
Use this option to programmatically apply filters without interactive prompts.

Key Parameters:
- filter_method="automated"
- filter_field: One of ["Wildfire Name", "Incident Number", "County", "Air Basin", "Air District", "CoAbDis Code"] (case-insensitive).
- field_values: List of values to filter on, e.g. ["Camp"], ["Napa"], ["Camp", "Napa"], [601].
- apply_date_filter: Optional boolean to apply a date range filter.
- start_date: String or datetime object in "YYYY-MM-DD" format, applied if apply_date_filter == True.
- end_date: String or datetime object in "YYYY-MM-DD" format, applied if apply_date_filter == True.
- aggregate_fields: - aggregate_fields: Grouping fields for the emissions summary. Options include:
["YEAR", "MONTH", "INCIDENT", "COABDIS", "COUNTY", "AIR DISTRICT", "AIR DISTRICT ID", "AIR BASIN"]. Defaults to ['YEAR', 'INCIDENT']

```bash
emissions_gdf, agg_table, vehicle_table = main(
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

This tool rougly predicts fire emissions from structures using parcel structure square footage data as a proxy for damage inspection data. It extracts parcel records within a user-provided area of interest (either a shapefile/geopackage path or geodataframe), assigns a random subset damage due to fire (based on user-input "ratio_destroyed"), and estimates emissions for those structures and vehicles. Users can use pre-set defaults for emissions factors, contents factors, consumption factors, and frame factors or provide their own values.

### Importing the predictor

```bash
from SWEEP_predictor import main
```
### General Parameters
The general parameters (aside from get_mode) are the same as those for SWEEP_estimator.

### Predictor Parameters
- aoi_source: The polygon feature(s) as a path to a .shp or .gpkg or geodataframe.
- api_key: a LightBox API key. In this example it is loaded from a .env file.
- ratio_destroyed: The ratio of structures in the dataset to assume destroyed by fire.
- aggregate_fields:  Grouping fields for the emissions summary. Options include:
["YEAR", "MONTH", "INCIDENT", "COABDIS", "COUNTY", "AIR DISTRICT", "AIR DISTRICT ID", "AIR BASIN", "AOI_INDEX"]. Defaults to ['YEAR', 'INCIDENT']

```bash
predicted_emissions_gdf, agg_table, vehicle_table = main(
    aoi_source = os.path.join(config.demo_dir, "demo_multipoly.shp"),
    # You need a lightbox API key to get the parcel data.
    api_key = os.getenv('LB_API_KEY'),
    ratio_destroyed = 0.8,
    pollutants = None, 
    aggregate_fields = ['AIR DISTRICT', 'AOI_INDEX'],
    write = "No")
```







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



