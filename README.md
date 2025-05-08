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
- pandas
- geopandas
- numpy
- requests
- pyogrio

You can install these dependencies by running:

```bash
pip install -r requirements.txt
```

## Usage

### Running the Estimator

To execute the full pipeline, run the `SWEEP_estimator.py` script. This will execute the sequence of functions to retrieve data, apply filters, estimate emissions, aggregate the results, and write the outputs.
For the first run, unsure hte bsdb_source is set to 'aAPI'-- this will write locally to geojson, but updating the bsdb via API periodically is recommended.
### Command to run the estimator:

```bash
python SWEEP_estimator.py
```
You can modify the parameters within config.py and SWEEP_estimator.py or call specific functions as needed.

### Example Outputs:

- Spatial file: Geopackage(gpkg), shapefile (.shp), or geojson containing point emissions data.
- Emissions report: .xlsx of per-structure emissions data.
- Aggregated report: .xlsx of aggregated emissions data.
- Vehicle report: .xslx of estimated emissions from vehicles consumed by fire.

### Scripts Overview:

- config.py

    Contains configuration settings for the project, including any necessary API keys, file paths, or environment-specific settings.
- get_bsdb.py

    Handles the retrieval of BSDB (Base Spatial Data) from the API, loading it into a DataFrame for further processing.
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
- **[Microsoft Building footprints](https://github.com/Microsoft/USBuildingFootprints)**: Microsoft building footprints.
- **[Lightbox Parcel Data](https://www.lightboxre.com/data/lightbox-parcel-data/)**

### Emissions Estimation
- **[Holder et al. 2023](https://doi.org/10.1093/pnasnexus/pgad186)**: Paper summarizing findings of recent research regarding emissions estimation from structures, including a comprehensive list of pollutant species and emissions factors, contents and frame factors, and estimated damage from fire.
- **[CARB 1999](https://ww2.arb.ca.gov/carb-miscellaneous-process-methodologies-fires)**: California Air Resources Board (CARB) Structural and Automobile Fires document.

### Fire Perimeter Data
- **[CAL FIRE FRAP Historical Fire Perimeters](https://data.ca.gov/dataset/california-historical-fire-perimeters)**: CAL FIRE compilation of historical fire perimeters for California.
- **[WFIG Fire Perimeters](https://data-nifc.opendata.arcgis.com/datasets/nifc::wfigs-current-interagency-fire-perimeters/about)**: Fire perimeters compiled across multiple agencies by the National Interagency Fire Center Wildland Fire Interagency Geospatial Services (WFIGS) Group.

### Administrative Boundaries
- **[CARB CoAbDis](https://ww2.arb.ca.gov/geographical-information-system-gis-library)** California Air Resources Board (CARB) county, air basin, and air pollution control district boundaries.



