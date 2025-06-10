from datetime import datetime
import geopandas as gpd
import numpy as np
import os
import pandas as pd
import pyogrio
import sys

def filter_bsdb(
    df, 
    filter_method, 
    apply_date_filter=False,
    start_date=None,
    end_date=None,
    filter_field=None,  # e.g. "Wildfire Name"
    field_values=None,  # list of selected values to filter by
    selected_year=None,  # only used for incidentname if no date filter
    polygon_input=None,
    geometry_col='geometry'
):

    """
    Filters a burned structure database (BSDB) using one of three methods: Interactive, Automated, or Spatial.

    Parameters
    ----------
    df : pd.DataFrame
        The input BSDB DataFrame. Must include at least the 'clean_date' column and relevant fields for filtering.

    filter_method : str
        Filtering method. One of the following (case-insensitive):
            - "Interactive" : Walks the user through an interactive filtering process.
            - "Automated"   : Uses provided parameters to apply filtering logic automatically.
            - "Spatial"     : Uses a spatial polygon input to perform a spatial filter.

    apply_date_filter : bool, optional (default: False)
        Whether to filter the data using a start and end date on the 'clean_date' field.

    start_date : str or datetime, optional
        Start date for filtering (inclusive). Required if `apply_date_filter=True`.

    end_date : str or datetime, optional
        End date for filtering (inclusive). Required if `apply_date_filter=True`.

    filter_field : str, optional
        Nickname of the field to filter by when using "Automated" mode. Must be one of:
            - "Wildfire Name" → filters on 'incidentname'
            - "Incident Number" → filters on 'incidentnum'
            - "County" → filters on 'CO_NAME'
            - "Air Basin" → filters on 'BASIN_NAME'
            - "Air District" → filters on 'DIS_NAME'
            - "CoAbDis Code" → filters on 'COABDIS'

    field_values : list of str or int, optional
        Values to filter by for the selected `filter_field`. Required when `filter_field` is set in "Automated" mode.

    selected_year : int, optional
        Required **only** if:
            - `filter_field` is "Wildfire Name"
            - `apply_date_filter` is False

    polygon_input : str or GeoDataFrame, optional
        File path or GeoDataFrame used for spatial filtering. Required if `filter_method="Spatial"`.

    geometry_col : str, optional (default: "geometry")
        Name of the geometry column in the polygon input (only applies if passing a GeoDataFrame).

    Returns
    -------
    gpd.GeoDataFrame
        A filtered copy of the input GeoDataFrame based on the selected method and filter parameters.

    Raises
    ------
    ValueError
        If required parameters are missing or if `filter_method` is invalid.

    Notes
    -----
    - For "Interactive" filtering, no additional arguments are required.
    - For "Automated" filtering:
        - If `apply_date_filter=True`, both `start_date` and `end_date` are required.
        - If filtering by "Wildfire Name" and `apply_date_filter=False`, `selected_year` is required.
        - `filter_field` and `field_values` are optional.
    - For "Spatial" filtering:
        - `polygon_input` must be provided.
        - If `apply_date_filter=True`, both `start_date` and `end_date` are also required.

    Example
    -------
    >>> filter_bsdb(df, filter_method="Automated", apply_date_filter=True,
                    start_date="2018-01-01", end_date="2019-01-01",
                    filter_field="County", field_values=["BUTTE"])
    >>> filter_bsdb(df, filter_method="Spatial", apply_date_filter=True,
                    start_date="2022-01-01", end_date="2022-08-08",
                    polygon_input = r"C:/data/demo_polygon.shp")
    """

    filter_method = filter_method.upper()

    if filter_method == "INTERACTIVE":
        filtered_bsdb = interactive_filter(df)
    elif filter_method == "AUTOMATED":
        filtered_bsdb = automated_filter(
            df=df,
            apply_date_filter=apply_date_filter,
            start_date=start_date,
            end_date=end_date,
            filter_field=filter_field,
            field_values=field_values,
            selected_year=selected_year
        )
    elif filter_method == "SPATIAL":
        filtered_bsdb = spatial_filter(
            df=df,
            apply_date_filter=apply_date_filter,
            start_date=start_date,
            end_date=end_date,
            polygon_input=polygon_input,
            geometry_col=geometry_col
        )
    else:
        raise ValueError(f"Invalid filter method '{filter_method}'. Choose 'interactive', 'automated', or 'spatial'.")
    
    return filtered_bsdb




def interactive_filter(df):
    """
    Walks users through selection of burned structure database records using available filter criteria.

    Parameters:
    ----------
    df : pd.DataFrame
        The input DataFrame (BSDB).

    Returns:
    -------
    pd.DataFrame
        A filtered DataFrame based on provided criteria.
    """
    
    def restart():
        """Restarts the function by prompting the user if they want to restart."""
        restart_choice = input("Would you like to restart? (yes/no): ").strip().lower()
        if restart_choice in ['yes', 'y']:
            return True
        return False

    def exit_program():
        """Exit the function."""
        exit_choice = input("Would you like to exit? (yes/no): ").strip().lower()
        if exit_choice in ['yes', 'y']:
            print("Exiting program...")
            return True
        return False
    
    if 'clean_date' in df.columns:
        df['clean_date'] = pd.to_datetime(df['clean_date'])

    # Step 0: ask about date filter
    while True:
        date_filter_choice = input("Would you like to apply a date filter? (yes/no): ").strip().lower()
        if date_filter_choice == 'exit':
            if exit_program():
                return None
        elif date_filter_choice in ['yes', 'y']:
            min_date = df['clean_date'].min().date()
            max_date = df['clean_date'].max().date()
            print(f"Available date range: {min_date} to {max_date}")
            
            start_date = input(f"Enter start date (YYYY-MM-DD) between {min_date} and {max_date}: ")
            end_date = input(f"Enter end date (YYYY-MM-DD) between {min_date} and {max_date}: ")
            
            try:
                start_date = pd.to_datetime(start_date)
                end_date = pd.to_datetime(end_date)
                df = df[(df['clean_date'] >= start_date) & (df['clean_date'] <= end_date)]
                print(f"{len(df)} rows after date filtering.")
                date_filtered = True
                break
            except Exception as e:
                print(f"Invalid date input: {e}")
                return None
        elif date_filter_choice == 'no' or date_filter_choice == 'n':
            print("Skipping date filter.")
            break
        else:
            print("Invalid input. Please enter 'yes', 'no', or 'exit'.")
    
    # Step 1: Ask if user wants to apply other filters
    while True:
        apply_other_filters = input("Would you like to apply other filters? (yes/no): ").strip().lower()
        if apply_other_filters == 'exit':
            if exit_program():
                return None
        elif apply_other_filters in ['yes', 'y']:
            # Field nicknames
            field_nicknames = {
                'Wildfire Name': 'incidentname',
                'Incident Number': 'incidentnum',
                'County': 'CO_NAME',
                'Air Basin': 'BASIN_NAME',
                'Air District': 'DIS_NAME',
                'CoAbDis Code': 'COABDIS'
            }
            
            display_fields = list(field_nicknames.keys())
            print("\nAvailable fields to filter by:")
            for i, display_name in enumerate(display_fields, start=1):
                print(f"{i}. {display_name}")

            while True:
                try:
                    field_choice = int(input("Enter the number corresponding to the field you want to filter by: "))
                    if 1 <= field_choice <= len(display_fields):
                        selected_display = display_fields[field_choice - 1]
                        selected_field = field_nicknames[selected_display]
                        break
                    else:
                        print("Invalid choice, please enter a number from the list.")
                except ValueError:
                    print("Please enter a valid number.")
            
            # --- special handling for Wildfire Name ---
            if selected_field == 'incidentname':
                if 'date_filtered' not in locals() or not date_filtered:
                    df['year'] = df['clean_date'].dt.year
                    unique_years = sorted(df['year'].dropna().unique())
                    print("\nAvailable years:")
                    for year in unique_years:
                        print(year)
                    while True:
                        try:
                            chosen_year = int(input("Enter the year you want to filter by: "))
                            if chosen_year in unique_years:
                                df = df[df['year'] == chosen_year]
                                print(f"{len(df)} rows after year filtering.")
                                break
                            else:
                                print("Invalid year, choose from the list.")
                        except ValueError:
                            print("Please enter a valid year.")

                # Now show incident names (with clean_date and counts)
                incidents = df.groupby('incidentname').agg(
                    count=('incidentname', 'count'),
                    first_date=('clean_date', 'min')
                ).reset_index()
                
                print("\nAvailable Wildfire Names:")
                for idx, row in incidents.iterrows():
                    name = row['incidentname']
                    date = row['first_date'].date() if pd.notnull(row['first_date']) else 'Unknown'
                    count = row['count']
                    print(f"{idx + 1}. {name} (Start: {date}, Records: {count})")
                
                while True:
                    choice_str = input("Enter one or more numbers separated by commas for Wildfire Names: ")
                    try:
                        choices = [int(c.strip()) for c in choice_str.split(',')]
                        if all(1 <= c <= len(incidents) for c in choices):
                            chosen_names = incidents.iloc[[c-1 for c in choices]]['incidentname'].tolist()
                            df = df[df['incidentname'].isin(chosen_names)]
                            print(f"{len(df)} rows after filtering for Wildfire Names {chosen_names}.")
                            break
                        else:
                            print("Invalid choices, enter numbers from the list.")
                    except ValueError:
                        print("Please enter valid numbers separated by commas.")
            else:
                # Handle other fields (with multiple selections)
                options = df[selected_field].dropna().unique()
                print(f"\nAvailable {selected_display}:")
                for i, option in enumerate(options, start=1):
                    count = (df[selected_field] == option).sum()
                    print(f"{i}. {option} (Records: {count})")
                
                while True:
                    choice_str = input(f"Enter one or more numbers separated by commas for {selected_display}: ")
                    try:
                        choices = [int(c.strip()) for c in choice_str.split(',')]
                        if all(1 <= c <= len(options) for c in choices):
                            chosen_values = [options[c-1] for c in choices]
                            df = df[df[selected_field].isin(chosen_values)]
                            print(f"{len(df)} rows after filtering for {selected_display} values {chosen_values}.")
                            break
                        else:
                            print("Invalid choices, enter numbers from the list.")
                    except ValueError:
                        print("Please enter valid numbers separated by commas.")
        elif apply_other_filters == 'no' or apply_other_filters == 'n':
            print("Skipping other filters.")
            break
        else:
            print("Invalid input. Please enter 'yes', 'no', or 'exit'.")
            if exit_program():
                return None

    return df

def automated_filter(df,
                    apply_date_filter,
                    start_date,
                    end_date,
                    filter_field,  # e.g. "Wildfire Name"
                    field_values,  # list of selected values to filter by,
                    selected_year,  # only used for incidentname if no date filter
                    ):
    """
    Filters a DataFrame by an optional date range and a field with selected values.

    Parameters:
    ----------
    df : pd.DataFrame
        The input DataFrame. Must contain at least 'clean_date' and other filterable fields.
    
    apply_date_filter : bool, optional
        Whether to apply a date range filter based on 'clean_date'. Default False.

    start_date : str or datetime, optional
        Start date for filtering (inclusive), e.g., "2018-01-01". Required if apply_date_filter=True.

    end_date : str or datetime, optional
        End date for filtering (inclusive), e.g., "2019-01-01". Required if apply_date_filter=True.

    filter_field : str, optional
        The field to filter by. Use the **nickname** from this list:
            - "Wildfire Name" → filters on 'incidentname'
            - "Incident Number" → filters on 'incidentnum'
            - "County" → filters on 'CO_NAME'
            - "Air Basin" → filters on 'BASIN_NAME'
            - "Air District" → filters on 'DIS_NAME'
            - "CoAbDis Code" → filters on 'COABDIS'

    field_values : list of str/int, optional
        The values to filter the selected field by (passed as a list).
        Example: ["Camp"], ["Butte"], ["Camp", "Woolsey"], ["Napa"], [601], etc.
        All caps for County, Air Basin, and Air District, sentence case for Widlfire Name.

    selected_year : int, optional
        Year to filter on if filtering by "Wildfire Name" **and no date filter is applied**.
        Ignored if apply_date_filter=True.

    Returns:
    -------
    pd.DataFrame
        A filtered DataFrame based on provided criteria.

    Notes:
    -----
    - If apply_date_filter=True, start_date and end_date must be provided.
    - If filter_field is None, no field filtering is applied.
    - If filter_field is "Wildfire Name" and apply_date_filter=False, selected_year is required.
    - Fields and values should not be case sensitive.
    """

    if 'clean_date' in df.columns:
        df['clean_date'] = pd.to_datetime(df['clean_date'])
    
    # Map field nicknames to actual fields
    field_nicknames = {
        'Wildfire Name': 'incidentname',
        'Incident Number': 'incidentnum',
        'County': 'CO_NAME',
        'Air Basin': 'BASIN_NAME',
        'Air District': 'DIS_NAME',
        'CoAbDis Code': 'COABDIS'
    }
    
    # Apply date filter if requested
    if apply_date_filter:
        if start_date is None or end_date is None:
            raise ValueError("start_date and end_date must be provided when apply_date_filter is True")
        start_date = pd.to_datetime(start_date)
        end_date = pd.to_datetime(end_date)
        df = df[(df['clean_date'] >= start_date) & (df['clean_date'] <= end_date)]
        print(f"{len(df)} rows after date filtering from {start_date.date()} to {end_date.date()}.")
    else:
        print("No date filter applied.")
    
    if filter_field is None:
        print("No field filter applied. Returning current DataFrame.")
        return df

    # Make lookup case-insensitive by converting keys and input to uppercase
    field_nicknames_upper = {k.upper(): v for k, v in field_nicknames.items()}
    filter_field_upper = filter_field.upper()

    if filter_field_upper not in field_nicknames_upper:
        raise ValueError(f"Invalid filter_field. Must be one of {list(field_nicknames.keys())}")

    selected_field = field_nicknames_upper[filter_field_upper]
    
    # Special handling for incidentname when no date filter
    if selected_field == 'incidentname' and not apply_date_filter:
        if selected_year is None:
            raise ValueError("selected_year must be provided for Wildfire Name filtering without date filter.")
        df['year'] = df['clean_date'].dt.year
        df = df[df['year'] == selected_year]
        print(f"{len(df)} rows after filtering by year {selected_year}.")
    
    # Apply value filter
    if field_values is not None:
        df = df[df[selected_field].str.upper().isin([v.upper() for v in field_values])]
        print(f"{len(df)} rows after filtering by {filter_field}: {field_values}.")
    else:
        print(f"No {filter_field} filter values provided. No filtering on this field.")
    
    return df

def spatial_filter(
    df, 
    apply_date_filter, 
    start_date, 
    end_date, 
    polygon_input, 
    geometry_col):

    """
    Filters the BSDB data by a date range and a spatial polygon.

    Parameters
    ----------
    df : pd.DataFrame
        Input DataFrame (BSDB).

    start_date : str or datetime, optional
        Start date for filtering (inclusive), e.g., "2018-01-01". Required if apply_date_filter=True.

    end_date : str or datetime, optional
        End date for filtering (inclusive), e.g., "2019-01-01". Required if apply_date_filter=True.

    polygon_input : str
        Path to the spatial file (shapefile, GeoPackage, GeoJSON, etc.) to use for spatial filtering.

    geometry_col : str, optional
        Name of the geometry column in df (default 'geometry').

    Returns
    -------
    GeoDataFrame
        A GeoDataFrame filtered by the provided date range and spatial intersection.

    Notes
    -----
    - Both input DataFrame and polygon will be projected to EPSG:3310 for spatial filtering.
    - Uses pyogrio for fast reading of spatial files.
    - Raises error if input file or columns are missing.
    """
    # Validate columns
    if 'clean_date' not in df.columns:
        raise ValueError("Input DataFrame must include a 'clean_date' column.")
    if geometry_col not in df.columns:
        raise ValueError(f"Input DataFrame must include a '{geometry_col}' column with geometry.")

    # Convert clean_date to datetime
    df['clean_date'] = pd.to_datetime(df['clean_date'])

    if apply_date_filter:
        if start_date is None or end_date is None:
            raise ValueError("start_date and end_date must be provided when apply_date_filter is True")
        start_date = pd.to_datetime(start_date)
        end_date = pd.to_datetime(end_date)
        df = df[(df['clean_date'] >= start_date) & (df['clean_date'] <= end_date)]
        print(f"{len(df)} rows after date filtering from {start_date.date()} to {end_date.date()}.")
    else:
        print("No date filter applied.")

    # Convert DataFrame to GeoDataFrame
    gdf = gpd.GeoDataFrame(df, geometry=gpd.GeoSeries(df[geometry_col]))
    if gdf.crs is None:
        print("Warning: input CRS unknown; assuming EPSG:4326")
        gdf.set_crs("EPSG:4326", inplace=True)

    if gdf.crs != "EPSG:3310":
        gdf = gdf.to_crs(crs = "EPSG:3310")
        print(f"Reprojecting polygon from {gdf.crs} to EPSG:3310.")

    # Load polygon using pyogrio
    try:
        polygon_gdf = gpd.read_file(polygon_input, engine="pyogrio")
    except Exception as e:
        raise IOError(f"Error reading polygon file: {e}")

    # Check and match CRS
    if polygon_gdf.crs != "EPSG:3310":
        print(f"Reprojecting polygon to EPSG:3310.")
        polygon_gdf = polygon_gdf.to_crs("EPSG:3310")

    if gdf.crs != "EPSG:3310":
        print(f"Reprojecting input GeoDataFrame from {gdf.crs} to EPSG:3310.")
        gdf = gdf.to_crs("EPSG:3310")

    # Perform spatial join (intersection)
    gdf_filtered = gdf[gdf.geometry.intersects(polygon_gdf.union_all())]
    print(f"{len(gdf_filtered)} rows after spatial filtering with {polygon_input}.")

    return gdf_filtered
