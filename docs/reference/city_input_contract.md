# City Input Contract

**Purpose:** Define the schema and rules for city input file, which will feed the geocoding service in extract layer.

## 1. Purpose of the City Configuration

The city configuration file (`cities.csv`) defines the list of target locations for the data pipeline. Rather than hardcoding city parameters directly into Python scripts, this file provides a central input structure that drives execution across the Extract Layer.

The configuration serves the following functions:
* **Input to Geocoding:** Supplies target city names and country codes to the geocoding service to retrieve latitude and longitude coordinates.
* **Pipeline Triggering:** Enables selective execution by allowing cities to be activated or deactivated without code modifications.
* **Traceability:** Assigns a unique identifier to each location, establishing primary key references for downstream database tables and log entries.

---

## 2. Required Fields / Columns

The configuration file requires the following five columns:

| Column Name | Data Type | Required? | Description |
| :--- | :--- | :--- | :--- |
| `city_id` | String | **Yes** | Unique primary identifier for tracking records across pipeline steps and database tables. |
| `city_name` | String | **Yes** | Official city name passed to the geocoding service. |
| `state` | String | No | Two-letter state or region code (optional; applicable primarily to US locations). |
| `country` | String | **Yes** | ISO 3166-1 alpha-2 country code (e.g., `US`, `GB`) required for geocoding accuracy. |
| `is_active` | Boolean | **Yes** | Execution flag (`TRUE` / `FALSE`) indicating whether the pipeline should process the city. |

---

## 3. Valid Example

`cities.csv`:

```csv
city_id,city_name,state,country,is_active
US_RAL_01,Raleigh,NC,US,TRUE
US_DUR_02,Durham,NC,US,TRUE
GB_LON_01,London,,GB,TRUE
```

---

## 4. Initial Rules for Missing or Invalid Values

* **Missing Required Fields:** If `city_id`, `city_name`, or `country` is missing, the entire row is skipped and logged to the `error_logs` table.
* **Missing Optional Fields:** If `state` is null or empty, processing continues normally.
* **Geocoding Failures:** If the geocoding service fails to resolve coordinates for a given `city_name` and `country` combination, the error is recorded in `error_logs` and extraction of OpenWeather air pollution data for that city is skipped.
* **Inactive Records:** Records where `is_active` is set to `FALSE` are skipped without creating error log entries.
* **Data Formatting:** Extra spaces are automatically removed from text fields, and `country` codes are changed to uppercase before API submission.