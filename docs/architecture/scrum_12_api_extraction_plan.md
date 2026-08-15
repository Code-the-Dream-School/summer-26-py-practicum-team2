# SCRUM-12: API Direction and Extraction Plan

## Purpose

This document defines the planned direction for the Extract stage of the City Air Tracker pipeline: which OpenWeather endpoints will be used, the order calls will happen in, how errors will be handled, and a trimmed sample of the expected response shape.

## Selected API direction

City Air Tracker will use the following endpoints from OpenWeather:

1. **Geocoding API** — converts a city name + country code into latitude/longitude.
2. **Historical Air Pollution API** — returns hourly air quality data for a given coordinate over a UTC time range. This is the primary endpoint for the pipeline: it feeds the Extract → Transform → Load flow and ultimately the gold dataset used by the dashboard.
3. **Current Air Pollution API** — returns air quality at the present moment for a coordinate.
4. **Forecast Air Pollution API** — returns hourly air quality forecasts (up to 4 days) for a coordinate.

Current and Forecast are not part of the active pipeline today. They were evaluated (tested directly against the API, see below) and are available as optional extensions, for example, showing present-day conditions on the dashboard, or supporting the planned ML forecasting module, but no ticket currently depends on them.

Since Current, Forecast, and Historical share the same base URL and response shape (`coord` + `list[]` of `main.aqi` / `components`), the extraction client is designed around a single function parameterized by a `mode` (`"current"`, `"forecast"`, or `"history"`) rather than three separate implementations. `history` is the only mode required for the current pipeline; `current` and `forecast` remain available if a future ticket needs them.

**Verified response sizes** (tested for Chicago and Miami, same result for both):

| Mode | `list[]` length | Notes |
|---|---|---|
| `current` | 1 | Single snapshot for right now |
| `history` | 24 | One record per hour, for the requested 24-hour window |
| `forecast` | 96 | Hourly records covering 4 days (24 × 4) |

All three modes return the same per-record shape (`dt`, `main.aqi`, `components.*`), so the same `inspectdata`-style flattening and AQI-category mapping logic works unchanged across all three.

## Extraction plan

For each city in the input list:

1. **Geocode the city** — call the Geocoding API with `city` and `country_code` to resolve `lat`/`lon`.
   - If no result is returned, the city is considered invalid.
2. **Fetch historical air pollution** — call the Historical Air Pollution API (mode `"history"`) with the resolved `lat`/`lon` and a `start`/`end` UTC time range (currently the last 24 hours).
3. **Parse the response** — flatten each record in `list[]` so that `main.aqi` and each `components.*` field sit at the top level alongside `dt`.
4. **Map AQI category** — convert the numeric `aqi` (1–5) to a readable category (`Good`, `Fair`, `Moderate`, `Poor`, `Very Poor`) using a static mapping.

This repeats independently for each city in the input list. The `current` and `forecast` modes follow the same parsing logic but are not called by the pipeline today.

## Error handling

- If geocoding fails to find a city (empty response), the extraction for that city is skipped with a logged/printed message, and the loop continues to the next city. This is implemented using a `try/except ValueError` around the geocoding step.
- Cities that fail geocoding do not proceed to the historical air pollution call.
- A summary count (cities processed vs. total cities requested) is reported at the end of a run.

## Optional second API integration

If the team keeps a human-friendly city input instead of supplying coordinates directly, the optional supporting integration is the OpenWeather Direct Geocoding API:

- Endpoint: `GET /geo/1.0/direct`
- Input: `city`, optional `state`, `country_code`
- Query pattern: `q=city,state,country_code&limit=1`
- Returned fields used by the pipeline: `name`, `lat`, `lon`, `country`, `state`

This integration is intentionally limited to resolving one best-match coordinate pair for the configured city. It supports the primary historical air-pollution extract path without adding separate persistence or caching requirements to the extract client itself.

## Trimmed response sample

Example of a single flattened record after parsing (real output from Chicago, mode `"history"`):

```json
{
  "dt": "2026-08-06T23:00:00Z",
  "aqi": 1,
  "aqi_category": "Good",
  "co": 140.33,
  "no": 0.31,
  "no2": 2.79,
  "o3": 57.41,
  "so2": 0.35,
  "pm2_5": 6.33,
  "pm10": 6.37,
  "nh3": 0.23
}
```

Notes:
- `dt` is converted from Unix UTC seconds to an ISO-8601 timestamp.
- All component values are in µg/m³.
- A full API response for a 24-hour window returns one such record per hour (~24 records per city per run).
