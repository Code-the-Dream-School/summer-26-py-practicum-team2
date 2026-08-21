# API Direction and Extraction Plan

## Primary API Selection: OpenWeather Air Pollution API

**Why this API**: It's included in OpenWeather's free tier at no added cost, uses the same `lat`/`lon` + `appid` auth pattern as the rest of the OpenWeather suite (so it's consistent with any other OpenWeather endpoints already in use), and returns a clean numeric AQI plus individual pollutant concentrations — well suited for a dashboard tile or trend chart.

## Connection to the Future Dashboard

This endpoint feeds an **air quality panel**: a historical AQI trend chart (1–5 scale) alongside pollutant breakdowns (CO, NO, NO2, O3, SO2, NH3, PM2.5, PM10) over a selected date range.

## Endpoint

**Historical (available from Nov 27, 2020 onward):**
```
GET http://api.openweathermap.org/data/2.5/air_pollution/history?lat={lat}&lon={lon}&start={start}&end={end}&appid={API key}
```

## Parameters

| Parameter | Required | Type | Notes |
|---|---|---|---|
| `lat` | Yes | float | Latitude of target location |
| `lon` | Yes | float | Longitude of target location |
| `start` | Yes | Unix timestamp | Start of date range |
| `end` | Yes | Unix timestamp | End of date range |
| `appid` | Yes | string | Free-tier API key |

## Important Fields

| Field | Meaning |
|---|---|
| `list[].dt` | Unix timestamp of the reading |
| `list[].main.aqi` | Air Quality Index, 1 (Good) to 5 (Very Poor) |
| `list[].components.co` | Carbon monoxide (μg/m³) |
| `list[].components.no` | Nitrogen monoxide (μg/m³) |
| `list[].components.no2` | Nitrogen dioxide (μg/m³) |
| `list[].components.o3` | Ozone (μg/m³) |
| `list[].components.so2` | Sulphur dioxide (μg/m³) |
| `list[].components.pm2_5` | Fine particulates (μg/m³) |
| `list[].components.pm10` | Coarse particulates (μg/m³) |
| `list[].components.nh3` | Ammonia (μg/m³) |

For dashboard purposes, `main.aqi`, `pm2_5`, and `pm10` are the fields most worth surfacing prominently; they're the most commonly referenced in public air quality reporting. The rest can sit behind a details view.

## Errors

| Status | Cause |
|---|---|
| 401 | Invalid or inactive API key |
| 404 | Coordinates outside coverage, incorrect coordinates, invalid date range (`start` after `end`, or `start` before Nov 27, 2020 coverage start), or incorrect API request format |
| 429 | Rate limit exceeded (free tier: 60 calls/minute) |

## Trimmed Response Sample

```json
{
  "coord": [50.0, 50.0],
  "list": [
    {
      "dt": 1606482000,
      "main": { "aqi": 2 },
      "components": {
        "co": 270.37,
        "no2": 43.18,
        "o3": 4.78,
        "pm2_5": 13.45,
        "pm10": 15.52
      }
    }
  ]
}
```
