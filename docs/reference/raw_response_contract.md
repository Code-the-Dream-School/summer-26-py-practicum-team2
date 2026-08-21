# Raw Response Contract

**Purpose:** This explains what a raw OpenWeather air pollution record looks like when it is saved, before any cleaning or changes.

## 1. What the Raw Layer Is

When the pipeline calls the OpenWeather API, it saves the response exactly as it arrives, plus a few extra details about the request. The data is not changed at this step. That way the original copy is always kept, in case something needs to be fixed or re-run later.

Each raw record keeps track of:

1. What was requested (city, coordinates, endpoint, and time range).
2. When the request happened and whether it worked (time and status code).
3. What came back (the OpenWeather JSON response).

## 2. Raw Record Fields

Each raw record is one row. The `payload` field holds the JSON from the API. The other fields are extra info the pipeline adds.

| Field | Type | Required? | Description |
| --- | --- | --- | --- |
| `raw_id` | Text | Yes | Unique ID for this record. |
| `city_id` | Text | Yes | Which city this is for, matching `cities.csv` (`US_RAL_01`). |
| `lat` | Number | Yes | Latitude used in the request. |
| `lon` | Number | Yes | Longitude used in the request. |
| `endpoint` | Text | Yes | Which OpenWeather endpoint was called (`air_pollution/history`). |
| `window_start` | Integer | No | Start of the time range, in Unix seconds (UTC). |
| `window_end` | Integer | No | End of the time range, in Unix seconds (UTC). |
| `fetched_at` | Timestamp | Yes | When the response arrived (UTC). |
| `http_status` | Integer | Yes | Status code from OpenWeather (`200`). |
| `payload` | JSON | Yes | The response from OpenWeather, saved as-is. |

### What's inside `payload`

The `payload` is saved exactly as OpenWeather sends it. It looks like this:

| Field | Type | Description |
| --- | --- | --- |
| `coord` | array | The coordinates, as `[lat, lon]`. |
| `list` | array | One item for each time sample. |
| `list[].dt` | integer | Time of the reading, in Unix seconds (UTC). |
| `list[].main.aqi` | integer | Air Quality Index (`1` = Good to `5` = Very Poor). |
| `list[].components` | object | Pollutant amounts (`co`, `no`, `no2`, `o3`, `so2`, `pm2_5`, `pm10`, `nh3`). |

See `reference/openweather_environmental_api_fields_reference.md` for the full list of payload fields.

## 3. Sample Record

Here is one raw record for Raleigh, NC:

```json
{
  "raw_id": "raw_0001",
  "city_id": "US_RAL_01",
  "lat": 35.7796,
  "lon": -78.6382,
  "endpoint": "air_pollution/history",
  "window_start": 1606488670,
  "window_end": 1606747870,
  "fetched_at": "2026-08-12T21:45:00Z",
  "http_status": 200,
  "payload": {
    "coord": [35.7796, -78.6382],
    "list": [
      {
        "dt": 1606482000,
        "main": { "aqi": 2 },
        "components": {
          "co": 270.367,
          "no": 5.867,
          "no2": 43.184,
          "o3": 4.783,
          "so2": 14.544,
          "pm2_5": 13.448,
          "pm10": 15.524,
          "nh3": 0.289
        }
      }
    ]
  }
}
```

## 4. Week 3 Handoff

### Storage needs for later

- Save the `payload` in PostgreSQL as JSON so it can be searched later.
- Pick a way to avoid saving the same record twice (for example, `city_id` + `endpoint` + `window_start` + `window_end`).
- Keep the request info (`endpoint`, time range, `http_status`) so each record can be traced back to its source.
- Decide how long raw records are kept.

### Open questions

1. Should raw data live only in PostgreSQL, or also as a backup JSON file?
2. Should `raw_id` be random, or built from the request info?
3. One row per API call (keep the whole `list` together), or one row per reading (split `list` so each hourly `dt` is its own row)? (This doc assumes one row per API call.)
4. For historical data, which time ranges should be requested, and how should long ranges be split?
5. If OpenWeather adds new fields later, does the record need a version number?

## Related docs

- `reference/openweather_environmental_api_fields_reference.md` — full API field reference.
- `reference/city_input_contract.md` — the rules for the `cities.csv` input that feeds this step.
