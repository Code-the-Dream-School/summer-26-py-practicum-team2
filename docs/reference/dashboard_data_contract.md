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

The API returns the number. 

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

```json
{
  "id": "US_RAL_01",
  "cityName": "Raleigh, NC",
  "aqi": 4,
  "trend": [
    { "observedAt": "2026-09-04T09:00:00+00:00", "aqi": 2 },
    { "observedAt": "2026-09-04T11:00:00+00:00", "aqi": 4 }
  ]
}
```

Window: the last 24 hours. Gold is hourly, so a complete window is 24 points, but gaps are normal and the array is not padded. Consumers must not assume a fixed length or evenly spaced points.

`aqi` is nullable here because a city can have readings that are all older than the window.

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

```json
[
  { "date": "2026-09-02", "aqi": 3.0 },
  { "date": "2026-09-04", "aqi": 2.5 }
]
```

Window: the last 14 days.

Rules that need to hold for these numbers to mean anything:

- **Buckets are calendar-based.** A daily bucket is one UTC date; a weekly bucket is one calendar week. Buckets must be derived from `observed_at`, not from the position of a row in a list, otherwise gaps silently stretch a bucket beyond its label.
- **Empty buckets are omitted, not zero-filled.** An absent day means no data, which is not the same as an AQI of 0 — and 0 is not even a valid AQI.
- **Averaging is defined once.** A weekly average is the **mean of all hourly readings** in that UTC ISO week (Monday start), not the mean of that week's daily means. The two differ whenever days have unequal reading counts.
- **Partial buckets are labeled.** A week with fewer than seven distinct UTC dates is labeled `{year}-W{week} (partial)`, for example `2026-W36 (partial)`.

The upsert rule in [gold_table_contract.md](gold_table_contract.md) is what makes these averages trustworthy: one row per city per hour means no double counting.

## 7. Known gaps

| Gap | Detail |
| :--- | :--- |
| Cities without readings | An active, seeded city with no gold rows is currently invisible to the dashboard. Acceptable for a demo; confusing on a fresh database. |
| Staleness | Overview cards show `observedAt`, so a reading from days ago is visible as a timestamp. There is still no separate stale/fresh badge. |
| Endpoint disagreement | The latest observation uses the newest reading at any age, while trend looks back only 24 hours. The same city can report an AQI in one place and `null` in another. |
| Pollutants unused | Gold stores `co`, `no`, `no2`, `o3`, `so2`, `pm2_5`, `pm10`, `nh3`, and the dashboard exposes none of them. We need to show them or record that AQI alone is intended. |
