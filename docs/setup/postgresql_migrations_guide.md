# PostgreSQL migrations

Apply the database schema without creating tables by hand. Alembic creates tables on an empty database and applies later changes the same way.

For the full local bring-up flow (Docker Postgres, seed cities, verify rows, run persistence tests), see [local_storage_workflow.md](local_storage_workflow.md).

## Setup (once)

1. Have an empty Postgres database (local install, Docker, or Azure).
2. At the **repository root** (the same folder as `.env.example`), copy `.env.example` to `.env` and set `DATABASE_URL`:

```
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:5432/DATABASE
```

Do not put `.env` in `services/pipeline`. Alembic still runs from that folder, and `load_dotenv()` walks up from the pipeline code to the repository-root `.env`.

## Create or update the schema

From `services/pipeline`, with the virtualenv active:

```bash
alembic upgrade head
```

- **Empty database:** creates the current tables (`cities`, `gold_air_quality`) and `alembic_version`.
- **Database that already has migrations:** applies only new revisions. Safe to run again.

## Seed city records

`alembic upgrade head` creates the `cities` table but leaves it empty. Load rows from `config/cities.csv` (or set `CITIES_FILE` / pass a path):

From `services/pipeline`, with the virtualenv active:

```bash
python seed_cities.py
python seed_cities.py config/cities.csv
```

Same validation as the Week 2 CSV loader. Invalid rows are skipped. Inactive cities are stored. Run it again after you edit the file; existing `city_id`s are updated. Downstream code can read the table with `load_cities_from_db()`.

## Gold rows

`gold_air_quality` is keyed by `(city_id, observed_at)`. Calling `upsert_gold()` again for the same city and hour overwrites AQI and pollutants; it does not add another row. Sample records are enough to test this before the real transform exists. See `docs/reference/gold_table_contract.md`.

## Later schema changes

1. Change models in `services/pipeline/src/pipeline/db/models.py`.
2. Add a revision: `alembic revision -m "describe the change"` (fill in `upgrade` / `downgrade`).
3. Run `alembic upgrade head` again.

Undo the last change with `alembic downgrade -1`.
