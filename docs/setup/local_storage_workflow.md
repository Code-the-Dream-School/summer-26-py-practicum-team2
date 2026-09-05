# Local storage workflow

Use this guide to set up PostgreSQL locally, apply the schema, seed city records, run persistence checks, and confirm rows in the database. Follow the steps in order.

For migration details and schema changes, see [postgresql_migrations_guide.md](postgresql_migrations_guide.md).
For CSV field rules, see [city_input_contract.md](../reference/city_input_contract.md).

## What you need

- Python 3.12+ with the repo virtualenv active
- Docker Desktop (or another local Postgres you can reach on port 5432)
- Repo cloned and dependencies installed:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## 1. Start Postgres

From any terminal, start a Postgres container that matches `.env.example`:

```bash
docker run --name cityair-postgres \
  -e POSTGRES_USER=cityair \
  -e POSTGRES_PASSWORD=cityair \
  -e POSTGRES_DB=cityair \
  -p 5432:5432 \
  -d postgres:17
```

If the container already exists, start it instead:

```bash
docker start cityair-postgres
```

Check that it is running:

```bash
docker ps
```

## 2. Configure `DATABASE_URL`

At the **repository root** (same folder as `.env.example`), copy the example env file:

```bash
cp .env.example .env
```

The default connection string should be:

```
DATABASE_URL=postgresql+psycopg://cityair:cityair@localhost:5432/cityair
```

Keep `.env` at the repo root. Do not put it inside `services/pipeline`.

## 3. Initialize the schema

From `services/pipeline`, with the virtualenv active:

```bash
cd services/pipeline
alembic upgrade head
```

**Expected result:** on an empty database, Alembic runs four migrations in order and records the final revision in `alembic_version`:

```text
001_initial_schema -> a00e2d059c17 -> 002_add_geocoding_cache -> 002_gold_air_quality
```

That creates `cities`, `pipeline_runs`, `geocoding_cache`, and `gold_air_quality`.

If Alembic prints no upgrade lines and reports it is already at head, only trust that if step 5 shows all five tables. A database migrated on an earlier branch can be stamped at head while missing tables. See [Alembic is at head but tables are missing](#alembic-is-at-head-but-tables-are-missing).

## 4. Seed cities from CSV

`alembic upgrade head` creates an empty `cities` table. Load rows from the default file:

```bash
python seed_cities.py
```

Or pass a path explicitly:

```bash
python seed_cities.py config/cities.csv
```

You can also point to another file with the `CITIES_FILE` env var in `.env`.

**Expected output** for the default `config/cities.csv`:

```text
Imported 4 cities from .../config/cities.csv (3 active, 1 inactive).
```

Notes:

- Invalid rows (missing required fields) are skipped.
- Inactive cities (`is_active=FALSE`) are still stored.
- Running seed again updates existing `city_id` rows instead of duplicating them.

## 5. Verify rows in the database

List tables:

```bash
docker exec -i cityair-postgres psql -U cityair -d cityair -c "\dt"
```

You should see exactly these five tables:

```text
alembic_version
cities
geocoding_cache
gold_air_quality
pipeline_runs
```

If any are missing, your database is stamped at head without having all migrations applied. See [Alembic is at head but tables are missing](#alembic-is-at-head-but-tables-are-missing).

Check the migration stamp. It should read `002_gold_air_quality`:

```bash
docker exec -i cityair-postgres psql -U cityair -d cityair -c "SELECT * FROM alembic_version;"
```

Inspect city rows:

```bash
docker exec -i cityair-postgres psql -U cityair -d cityair -c "SELECT city_id, city_name, state, country, is_active FROM cities ORDER BY city_id;"
```

For the default CSV you should see four rows, including one inactive city (`US_NYC_99`).

Count active vs inactive:

```bash
docker exec -i cityair-postgres psql -U cityair -d cityair -c "SELECT is_active, COUNT(*) FROM cities GROUP BY is_active ORDER BY is_active;"
```

## 6. Run persistence checks

From the **repository root**:

```bash
python -m pytest services/pipeline/tests/test_city_persistence.py -q
```

**Expected result:**

```text
....                                                                       [100%]
4 passed
```

These tests cover CSV validation, upsert behavior, active/inactive filtering, and the default cities file path logic.

To run all pipeline tests (same check CI uses):

```bash
python -m pytest services/pipeline/tests -q
```

## 7. Read cities back in Python

After seeding, downstream code can load active cities from Postgres.

The `pipeline` package lives in `services/pipeline/src`, so start Python with that
directory on the import path. From the **repository root**:

```bash
PYTHONPATH=services/pipeline/src python
```

Then, in the Python prompt:

```python
from pipeline.db import load_cities_from_db

rows = load_cities_from_db()
for row in rows:
    print(row)
```

Expected output for the default `config/cities.csv`:

```text
{'city_id': 'GB_LON_01', 'city_name': 'London', 'state': '', 'country': 'GB', 'is_active': 'TRUE'}
{'city_id': 'US_DUR_02', 'city_name': 'Durham', 'state': 'NC', 'country': 'US', 'is_active': 'TRUE'}
{'city_id': 'US_RAL_01', 'city_name': 'Raleigh', 'state': 'NC', 'country': 'US', 'is_active': 'TRUE'}
```

Each row is a dict with keys: `city_id`, `city_name`, `state`, `country`, `is_active`.

Pass `active_only=False` to include inactive cities.

If you get `ModuleNotFoundError: No module named 'pipeline'`, you started Python
without `PYTHONPATH=services/pipeline/src`, or from the wrong directory.

If the loop prints nothing, the `cities` table is empty. Run step 4 first.

## Quick checklist

Use this before opening a PR that touches persistence:

- [ ] Postgres is running and reachable on port 5432
- [ ] `.env` at repo root has a valid `DATABASE_URL`
- [ ] `alembic upgrade head` succeeds from `services/pipeline`
- [ ] `\dt` shows all five tables and `alembic_version` reads `002_gold_air_quality`
- [ ] `python seed_cities.py` reports imported cities
- [ ] `SELECT ... FROM cities` shows expected rows
- [ ] `pytest services/pipeline/tests/test_city_persistence.py -q` passes

## Troubleshooting

### `DATABASE_URL is not set`

Create or fix `.env` at the **repository root**, not inside `services/pipeline`.

### Alembic is at head but tables are missing

`alembic upgrade head` prints no upgrade lines and exits cleanly, but `\dt` shows fewer than five tables, and tests fail with `relation "pipeline_runs" does not exist` (or another missing table).

Your database was migrated on an earlier branch, when the migration order was different. Migrations later inserted above your stamped revision never ran, and Alembic will not backfill them because it considers the database current.

Reset the schema and reapply the full chain:

```bash
docker exec -i cityair-postgres psql -U cityair -d cityair -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
cd services/pipeline
alembic upgrade head
python seed_cities.py
```

This drops all local data, so reseed cities afterwards as shown. Only do this on a local dev database.

### `Can't locate revision identified by ...`

Your local Postgres was migrated on a different feature branch. Reset the schema, then rerun migrations for your current branch:

```bash
docker exec -i cityair-postgres psql -U cityair -d cityair -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
cd services/pipeline
alembic upgrade head
```

Only do this on a local dev database.

### `Did not find any relations`

The schema has not been applied yet. Run `alembic upgrade head` from `services/pipeline`.

### Seed succeeds but `cities` is empty in psql

Confirm you are querying the same database as `DATABASE_URL` (host, port, database name).

### Port 5432 already in use

Another Postgres instance may be running. Stop it or change the Docker port mapping and update `DATABASE_URL` to match.
