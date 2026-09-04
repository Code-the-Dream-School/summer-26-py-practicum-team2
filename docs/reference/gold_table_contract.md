# Gold table keys and upsert

Gold is the hourly air-quality table the dashboard will read. This is the load-side contract.`upsert_gold()` accepts sample records with the same keys.

## Identity

One row per city per hour.

| Column | Role |
| :--- | :--- |
| `city_id` | Text, same as `cities.city_id` (`US_RAL_01`). |
| `observed_at` | UTC timestamp for that hour. |

Unique constraint: `uq_gold_city_hour` on `(city_id, observed_at)`. `gold_id` is only an internal serial PK.

## Upsert

Load the same city+hour twice: **update** AQI and pollutant columns (`co`, `no`, `no2`, `o3`, `so2`, `pm2_5`, `pm10`, `nh3`). Do not insert a second row. That is what stops double counting in averages and hour counts.

`created_at` stays on first insert. `updated_at` moves on each update.

`aqi` is required and must be 1–5 (OpenWeather scale). Pollutants may be empty.

## Load helper

```python
from pipeline.db.gold import upsert_gold

upsert_gold(sample_rows, engine=engine)
```

Pass `engine` in tests. Omit it in a real run to use `DATABASE_URL`.
