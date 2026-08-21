# City Air Tracker - Core Table Design

This document lays out the five core tables for the pipeline, geocoding_cache, cities, pipeline_runs, raw_air_pollution_responses, and gold_air_quality. Each section covers the primary key, foreign keys, uniqueness rules, and required fields, plus the reasoning behind a few calls that need the team's sign-off before this gets locked in.

---

## 1. geocoding_cache

This table caches lookups against the OpenWeather Geocoding API so the same city isn't re-geocoded on every run.

```sql
CREATE TABLE geocoding_cache (
    cache_id        BIGSERIAL PRIMARY KEY,
    query_text      TEXT NOT NULL,          -- exact string sent to the Geocoding API, e.g. "Austin,TX,US"
    resolved_name   TEXT NOT NULL,
    resolved_country CHAR(2) NOT NULL,
    resolved_state  TEXT,
    lat             NUMERIC(9,6) NOT NULL,
    lon             NUMERIC(9,6) NOT NULL,
    raw_response    JSONB NOT NULL,          -- full API response, for audit and debugging
    fetched_at      TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT uq_geocoding_query UNIQUE (query_text)
);
```

cache_id is a surrogate primary key rather than query_text itself. The natural key is a string that could change format later, so nothing referencing this table should depend on it.

Uniqueness is UNIQUE(query_text), which makes the cache an upsert target, a repeat geocode of the same query overwrites lat, lon, raw_response, and fetched_at.

Every column is required except resolved_state, since plenty of countries don't have a meaningful state or province.

I want to flag this before we build on top of it. A straight UNIQUE(query_text) with overwrite on refresh means we lose history. If OpenWeather ever returns a different lat/lon for the same query, whether their geocoder updates or a city gets renamed, we won't be able to tell after the fact. Any row in cities still holding the old coordinates will have no record of why. If an audit trail matters, I'd switch to UNIQUE(query_text, fetched_at) and treat the latest row per query as the effective cache through a view. That costs a bit of query complexity but buys real history. I'd like us to decide on this before we ship it.

---

## 2. cities

This is the canonical, pipeline-tracked city list, what the ETL is actually configured to pull, with a resolved coordinate locked in at config time.

```sql
CREATE TABLE cities (
    city_id           BIGSERIAL PRIMARY KEY,
    display_name      TEXT NOT NULL,         -- e.g. "Austin, TX, US", what config and UI show
    geocode_cache_id  BIGINT REFERENCES geocoding_cache(cache_id) ON DELETE SET NULL,
    lat               NUMERIC(9,6) NOT NULL,  -- denormalized copy, locked at geocode time
    lon               NUMERIC(9,6) NOT NULL,
    is_active         BOOLEAN NOT NULL DEFAULT TRUE,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT uq_cities_display_name UNIQUE (display_name)
);

CREATE UNIQUE INDEX uq_cities_coords ON cities (
    ROUND(lat::numeric, 4), ROUND(lon::numeric, 4)
);
```

city_id is again a surrogate primary key. geocode_cache_id references geocoding_cache with ON DELETE SET NULL, so if a cache row gets purged, the city doesn't disappear or get blocked from deletion, it just loses its lineage pointer.

Uniqueness has two parts. UNIQUE(display_name) covers the config-facing name, and a rounded-coordinate uniqueness index sits on top of that, about eleven meters of precision at four decimal places, to catch two differently named config entries that actually resolve to the same physical point. Required fields are display_name, lat, and lon.

I want to explain why lat and lon are duplicated here instead of always joining back to geocoding_cache. The pipeline needs a stable coordinate to call the history endpoint even if the cache entry later gets refreshed or deleted. That's deliberate denormalization, not an oversight, but it does mean cities.lat/lon and geocoding_cache.lat/lon can drift apart over time and nothing in the schema will alert us when that happens. If that drift ends up mattering operationally, we'd want a periodic reconciliation check, not just the foreign key.

I'll also call out a real risk here. The coordinate-uniqueness index assumes cities only ever get added through geocoding. If someone hand-inserts a city with slightly different precision or a typo'd decimal, this constraint is the only defense against silently duplicating pulls for the same place under two different city_ids. Worth a comment in the DDL itself saying so, since it isn't obvious just from reading the table.

---

## 3. pipeline_runs

One row per ETL execution, whether that's a geocode run, an extract run, a transform run, or a full run, for monitoring and lineage.

```sql
CREATE TABLE pipeline_runs (
    run_id         BIGSERIAL PRIMARY KEY,
    run_type       TEXT NOT NULL CHECK (run_type IN ('geocode','extract','transform','full')),
    status         TEXT NOT NULL DEFAULT 'running'
                   CHECK (status IN ('running','success','failed','partial')),
    started_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at    TIMESTAMPTZ,
    triggered_by   TEXT,               -- e.g. 'cron', 'manual:edriel'
    error_summary  TEXT
);
```

run_id is a surrogate primary key. Nothing references into this table from outside, other tables reference out of it. No uniqueness constraint is needed beyond the primary key. Required fields are run_type, status, and started_at.

One thing isn't decided yet, and I want the team's input on it. Right now nothing stops two extract runs from overlapping and racing each other against the same cities. If we never want concurrent runs of the same type, a partial unique index on run_type where status equals running would enforce that at the database level instead of relying on application logic to prevent it.

---

## 4. raw_air_pollution_responses

Append-only log of every API call attempt against the history endpoint, including the failed ones. This is the audit trail and the replay source if the transform logic ever changes.

```sql
CREATE TABLE raw_air_pollution_responses (
    raw_id         BIGSERIAL PRIMARY KEY,
    city_id        BIGINT NOT NULL REFERENCES cities(city_id) ON DELETE RESTRICT,
    run_id         BIGINT NOT NULL REFERENCES pipeline_runs(run_id) ON DELETE RESTRICT,
    window_start   TIMESTAMPTZ NOT NULL,   -- the `start` param, stored as a timestamp, not raw epoch
    window_end     TIMESTAMPTZ NOT NULL,
    http_status    INTEGER NOT NULL,
    raw_response   JSONB,                  -- NULL when the body wasn't valid JSON
    response_text  TEXT,                   -- raw body fallback when raw_response is NULL
    error_message  TEXT,
    fetched_at     TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT uq_raw_run_window UNIQUE (city_id, run_id, window_start, window_end),
    CONSTRAINT ck_raw_window CHECK (window_end > window_start)
);
```

raw_id is a surrogate primary key. Two foreign keys sit on this table, city_id to cities and run_id to pipeline_runs, both ON DELETE RESTRICT. Deleting a city or a run that has historical raw pulls attached should fail loudly, not silently cascade and wipe out the audit trail.

Uniqueness is UNIQUE(city_id, run_id, window_start, window_end). That stops the same run from double-writing the same city and window, so a run is idempotent within one execution, while still letting a later run legitimately re-pull the same window for a backfill or a retry after a prior failure. Required fields are city_id, run_id, window_start, window_end, http_status, and fetched_at. raw_response is nullable by design, a 401 or a malformed body still needs a row here, just without a parseable payload.

I want to flag a design call here rather than let it slide by. This table stores one row per API call, and each call's raw_response contains a list array covering the whole window, not one row per hourly reading. That means source_raw_id on the gold table, covered below, tells us which fetch produced a gold row, not which specific hourly JSON element did. If we ever need to debug why one particular hour is wrong, down to the exact array index, this schema can't do that without re-parsing the JSONB. If per-hour lineage turns out to matter, we'd need an intermediate raw_air_pollution_readings table that unnests list into one row per hour with an array_index or the item's own dt. I'd only add that complexity once we've actually hit a debugging case that needs it, not build it speculatively.

---

## 5. gold_air_quality

One row per city per hour, the deduplicated, transformed dataset the dashboard reads from.

```sql
CREATE TABLE gold_air_quality (
    gold_id        BIGSERIAL PRIMARY KEY,
    city_id        BIGINT NOT NULL REFERENCES cities(city_id) ON DELETE RESTRICT,
    observed_at    TIMESTAMPTZ NOT NULL,   -- converted from the response's `dt` epoch field
    aqi            SMALLINT NOT NULL CHECK (aqi BETWEEN 1 AND 5),  -- OpenWeather's 1-5 scale, not US EPA 0-500
    co             NUMERIC,
    no             NUMERIC,
    no2            NUMERIC,
    o3             NUMERIC,
    so2            NUMERIC,
    pm2_5          NUMERIC,
    pm10           NUMERIC,
    nh3            NUMERIC,
    source_raw_id  BIGINT REFERENCES raw_air_pollution_responses(raw_id) ON DELETE SET NULL,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT uq_gold_city_hour UNIQUE (city_id, observed_at)
);
```

gold_id is a surrogate primary key, kept separate from the natural key so anything referencing gold rows down the line doesn't have to carry a composite key around. Two foreign keys sit here. city_id references cities with RESTRICT, so a city can't disappear out from under historical gold data, and source_raw_id references raw_air_pollution_responses with SET NULL, since losing the raw lineage pointer is acceptable but losing the gold row itself is not.

The uniqueness constraint here, UNIQUE(city_id, observed_at), is the one that matters most functionally. It's the real natural key. The raw table can and will have overlapping or duplicate windows from retries, and this constraint is what forces the transform step to dedupe down to exactly one row per city hour. INSERT ... ON CONFLICT (city_id, observed_at) DO UPDATE handles reprocessing. Required fields are city_id, observed_at, and aqi. Pollutant components are left nullable. OpenWeather's docs suggest they're always present alongside aqi, but the verification notes already flagged that a malformed response could show up with main.aqi but no full components block, so one bad upstream record shouldn't be able to fail an entire transform batch.

---

## Serving layer for the React dashboard

The dashboard reads through the Python API, not directly against Postgres, so everything in this section describes objects the API queries, not new base tables. The dashboard needs four things, a latest snapshot for the map and overview, a single city's hourly trend, a multi-city comparison over a date range, and daily and weekly aggregates.

Single-city trend and multi-city comparison don't need any new schema. The UNIQUE(city_id, observed_at) index on gold_air_quality already leads with city_id, so both a single-city query filtered by date and a multi-city IN query filtered by date hit that index directly.

For the latest snapshot, running a window function over the full table on every map load won't scale as city count and history grow, so this gets materialized:

```sql
CREATE MATERIALIZED VIEW latest_city_aqi AS
SELECT DISTINCT ON (city_id)
    city_id, observed_at, aqi, co, no, no2, o3, so2, pm2_5, pm10, nh3
FROM gold_air_quality
ORDER BY city_id, observed_at DESC;

CREATE UNIQUE INDEX uq_latest_city_aqi_city ON latest_city_aqi (city_id);
```

The unique index there is required for REFRESH MATERIALIZED VIEW CONCURRENTLY, which matters specifically because a non-concurrent refresh locks the view against reads, and that's the query the map view hits most often.

The daily rollup is also materialized, since recomputing an average over raw hourly rows on every dashboard load is wasted work when the underlying data only changes once per pipeline run.

```sql
CREATE MATERIALIZED VIEW gold_air_quality_daily AS
SELECT
    city_id,
    date_trunc('day', observed_at) AS observed_date,
    ROUND(AVG(aqi)::numeric, 2)   AS avg_aqi,
    MAX(aqi)                       AS max_aqi,
    ROUND(AVG(pm2_5)::numeric, 2) AS avg_pm2_5,
    ROUND(AVG(pm10)::numeric, 2)  AS avg_pm10,
    ROUND(AVG(co)::numeric, 2)    AS avg_co,
    ROUND(AVG(no2)::numeric, 2)   AS avg_no2,
    ROUND(AVG(o3)::numeric, 2)    AS avg_o3,
    ROUND(AVG(so2)::numeric, 2)   AS avg_so2,
    ROUND(AVG(nh3)::numeric, 2)   AS avg_nh3,
    COUNT(*)                       AS reading_count
FROM gold_air_quality
GROUP BY city_id, date_trunc('day', observed_at);

CREATE UNIQUE INDEX uq_gold_daily_city_date ON gold_air_quality_daily (city_id, observed_date);
```

reading_count isn't just decorative. It lets the dashboard distinguish eighteen of twenty four hours reported, take this average with a grain of salt, from a genuinely complete day, worth surfacing in the UI rather than silently averaging over gaps.

A third materialized view for weekly numbers was deliberately left out. gold_air_quality_daily already collapses the row count by a factor of twenty four, so grouping that by ISO week at query time is cheap, and a third materialized object is one more thing to keep in sync for marginal benefit at current scale. Worth revisiting if weekly queries become a measured bottleneck, not worth building speculatively now.

There's one thing not decided yet, and it's better decided explicitly than left to default. The natural point to refresh both materialized views is right after a pipeline_runs row transitions to run_type equals transform, status equals success. What isn't clear is what to do when status is partial. Refreshing shows the dashboard fresher but incomplete data. Not refreshing shows a fully stale but complete picture. Both are defensible, but I'd like the team to pick one and document it, because right now nothing in the schema encodes that decision and it'll otherwise get decided implicitly by whoever writes the refresh call.

City display info like name and lat/lon isn't in gold_air_quality or either view above, the API joins to cities for that. That's fine at query time given how small the city count is, not worth denormalizing into the views unless that join ever shows up as a real cost.

---

## Entity relationship summary

```
geocoding_cache (1) --< (0..1) cities
cities          (1) --< (many) raw_air_pollution_responses
pipeline_runs   (1) --< (many) raw_air_pollution_responses
cities          (1) --< (many) gold_air_quality
raw_air_pollution_responses (0..1) --< (many) gold_air_quality   [lineage, nullable]
```

## Judgment calls worth revisiting if the assumptions behind them stop holding

1. The geocode cache overwrites on refresh, so there's no history, unless we switch to UNIQUE(query_text, fetched_at).
2. Coordinate uniqueness on cities is enforced by rounding to four decimals. Fine for city-level dedup, would falsely collide for very close but distinct points, which isn't a concern at city granularity but would be at street level.
3. The raw table is per API call, not per hourly reading, so there's no per-hour lineage without unnesting the JSONB.
4. RESTRICT is used fairly aggressively on the foreign keys pointing at cities and runs from raw and gold. Deleting a city with history attached requires an explicit decision, an archive step or a deliberate cascade override, not an accidental cascade.
5. latest_city_aqi and gold_air_quality_daily are materialized views planned to refresh after a successful transform run. I still need us to decide whether a partial run should also trigger a refresh, rather than leaving that to whoever ends up writing the refresh call.