# Dashboard Data Contract

**Purpose:** Define the fields the dashboard and its API need, and where each one comes from.

The dashboard reads only two tables: `cities` and `gold_air_quality`.

## 1. Source of truth

| Source | Provides |
| :--- | :--- |
| `cities` | `city_id`, `city_name`, `state`, `country`, `is_active` |
| `gold_air_quality` | `city_id`, `observed_at`, `aqi`, and eight pollutant columns |

See [gold_table_contract.md](gold_table_contract.md) for gold keys and upsert rules, and [city_input_contract.md](city_input_contract.md) for the city fields.

Only cities with `is_active = TRUE` are ever exposed. Inactive cities stay in the database but must not reach the dashboard.

## 2. Shared conventions

These apply to every shape in this document.

| Rule | Value |
| :--- | :--- |
| Field naming | `camelCase` in JSON, `snake_case` in the database |
| Timestamps | ISO 8601 with explicit UTC offset (`2026-09-04T11:00:00+00:00`) |
| Timezone | Always UTC. The database column is `timestamptz`; the API must not emit naive timestamps. |
| City identity | `city_id` from `cities`, exposed as `id` |
| Display name | `"{city_name}, {state or country}"` → `Raleigh, NC`, `London, GB` |
| Missing value | `null`, never `0` and never an empty string |

`aqi` is an integer on the OpenWeather 1–5 scale, enforced in the database by `ck_gold_aqi`. Averages are the one exception and may be fractional.

| `aqi` | Label |
| :--- | :--- |
| 1 | Good |
| 2 | Fair |
| 3 | Moderate |
| 4 | Poor |
| 5 | Very Poor |

The API returns the number. Labels and colors belong to the frontend (`AqiBadge.tsx`). 

## 3. Latest observation by city

The city selector and the overview grid. One row per active city, using that city's newest `observed_at`.

| Field | Type | Required? | Source |
| :--- | :--- | :--- | :--- |
| `id` | Text | Yes | `cities.city_id` |
| `cityName` | Text | Yes | Composed from `city_name` + `state`/`country` |
| `aqi` | Integer 1–5 | Yes | `gold_air_quality.aqi` at the newest `observed_at` |
| `observedAt` | Timestamp | Yes | `gold_air_quality.observed_at` of that row |

```json
[
  { "id": "GB_LON_01", "cityName": "London, GB", "aqi": 1, "observedAt": "2026-09-04T10:00:00+00:00" },
  { "id": "US_RAL_01", "cityName": "Raleigh, NC", "aqi": 4, "observedAt": "2026-09-04T11:00:00+00:00" }
]
```

`observedAt` is required, not decorative. It is the only way the UI can tell a current reading from a stale one when the pipeline has not run recently.

**Open question:** whether a city with no gold rows yet should appear here. Today it cannot, because the query inner-joins gold. A freshly seeded database therefore returns an empty list even though cities exist. See section 7.

## 4. Trend data

One city over time, for the trend chart. Ordered oldest to newest.

| Field | Type | Required? | Source |
| :--- | :--- | :--- | :--- |
| `id` | Text | Yes | `cities.city_id` |
| `cityName` | Text | Yes | Composed, as above |
| `aqi` | Integer 1–5, or `null` | Yes | Newest reading in the window; `null` when the window is empty |
| `trend[]` | Array | Yes | One entry per gold row in the window |
| `trend[].observedAt` | Timestamp | Yes | `gold_air_quality.observed_at` |
| `trend[].aqi` | Integer 1–5 | Yes | `gold_air_quality.aqi` |
| `trend[].pollutants` | Object | Yes | Eight gold pollutant columns |
| `trend[].pollutants.co` (and `no`, `no2`, `o3`, `so2`, `pm2_5`, `pm10`, `nh3`) | Number, or `null` | Yes | Matching gold column; `null` when missing |

```json
{
  "id": "US_RAL_01",
  "cityName": "Raleigh, NC",
  "aqi": 4,
  "trend": [
    {
      "observedAt": "2026-09-04T09:00:00+00:00",
      "aqi": 2,
      "pollutants": {
        "co": 270.4, "no": 5.9, "no2": 43.2, "o3": 4.8,
        "so2": 14.5, "pm2_5": 13.4, "pm10": 15.5, "nh3": 0.3
      }
    },
    {
      "observedAt": "2026-09-04T11:00:00+00:00",
      "aqi": 4,
      "pollutants": {
        "co": null, "no": null, "no2": null, "o3": null,
        "so2": null, "pm2_5": null, "pm10": null, "nh3": null
      }
    }
  ]
}
```

Window: the last 24 hours. Gold is hourly, so a complete window is 24 points, but gaps are normal and the array is not padded. Consumers must not assume a fixed length or evenly spaced points.

`aqi` is nullable here because a city can have readings that are all older than the window.

Pollutants are nested on each trend point so the hourly tab can show the latest hour without a second request (AIR-45). Units are µg/m³. Labels belong to the frontend (`PollutantsPanel.tsx`).

## 5. City comparison fields

Several cities on one chart. One entry per selected city, so the frontend can merge series by `observedAt`.

Requirements specific to comparison:

- Timestamps must be directly comparable across cities, which is why UTC is mandatory rather than a preference.
- Points must be merged on `observedAt` and sorted, because cities may have different gaps and arrive in any order.
- `cityName` is the series label, so it must be unique across the selected set. `"{city_name}, {state or country}"` is unique for the current city list; two same-named cities in one state would collide.

## 6. Summary counts

Daily and weekly averages per city, for the summary view.

| Field | Type | Required? | Source |
| :--- | :--- | :--- | :--- |
| `date` | Text | Yes | Bucket label |
| `aqi` | Number | Yes | Mean AQI in the bucket, one decimal |

Daily:

```json
[{ "date": "2026-09-02", "aqi": 3.0 }, { "date": "2026-09-04", "aqi": 2.5 }]
```

Weekly:

```json
[{ "date": "2026-W36 (partial)", "aqi": 2.5 }]
```

Window: the last 14 days.

Rules that need to hold for these numbers to mean anything:

- **Buckets are calendar-based.** A daily bucket is one UTC date (`YYYY-MM-DD`). A weekly bucket is one UTC ISO week (Monday start), labeled `{year}-W{week}` (`2026-W36`). Both are derived from `observed_at`, not from the position of a row in a list.
- **Empty buckets are omitted, not zero-filled.** An absent day means no data, which is not the same as an AQI of 0 — and 0 is not even a valid AQI.
- **Weekly average is the mean of all hourly readings** in that UTC ISO week, not the mean of that week's daily means.
- **Partial weeks are labeled.** Fewer than seven distinct UTC dates → `{year}-W{week} (partial)`.

Do not group every 7 consecutive daily rows as `"Week of {first_date}"`. That stretches a bucket across a gap and uses the mean of daily means.

The upsert rule in [gold_table_contract.md](gold_table_contract.md) is what makes these averages trustworthy: one row per city per hour means no double counting.

## 7. Known gaps

| Gap | Detail |
| :--- | :--- |
| Cities without readings | An active, seeded city with no gold rows is currently invisible to the dashboard. Acceptable for a demo; confusing on a fresh database. |
| Staleness | Overview cards show `observedAt`, so a reading from days ago is visible as a timestamp. There is still no separate stale/fresh badge. |
| Endpoint disagreement | The latest observation uses the newest reading at any age, while trend looks back only 24 hours. The same city can report an AQI in one place and `null` in another. |
