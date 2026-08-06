# City Air Tracker: Product and Data Pipeline Summary

## Product Summary

City Air Tracker is a web application that helps users explore and compare historical air-quality data for selected cities. The application will collect pollution data from an external API, process and store it, and present useful information through a dashboard.

Users will be able to select a city and view air-quality measurements and trends. The dashboard may include values such as the Air Quality Index (AQI), particulate matter levels, and comparisons between cities or time periods.

The project includes a Python-based data pipeline, a PostgreSQL database, a backend API, and a React frontend.

## Data Pipeline Summary

The data pipeline follows an Extract, Transform, and Load process.

### Extract

The pipeline reads a configured list of cities. It uses a geocoding service to convert each city into latitude and longitude coordinates. It then requests historical air-pollution data for those coordinates from the selected OpenWeather API.

The raw API responses are preserved so the team can inspect the original data and troubleshoot problems.

### Transform

The transform stage converts the raw API responses into a consistent tabular structure. It selects useful fields, standardizes dates and city information, handles missing or invalid values, and removes duplicate records.

The pipeline may also create derived fields, such as air-quality categories or risk indicators.

### Load

The processed records are loaded into PostgreSQL. The database becomes the primary source for the application dashboard and backend API.

The load process should avoid creating duplicate rows when the pipeline runs more than once.

## Application Flow

The expected application flow is:

1. Read the configured city list.
2. Geocode each city.
3. Request historical air-quality data.
4. Store or preserve the raw response.
5. Clean and transform the data.
6. Load the prepared records into PostgreSQL.
7. Query the stored data through the backend API.
8. Display trends and comparisons in the React dashboard.

This structure separates data collection, processing, storage, and presentation so each part can be developed and tested independently.
