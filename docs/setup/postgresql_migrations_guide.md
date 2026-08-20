# PostgreSQL migrations

Apply the database schema without creating tables by hand. Alembic creates tables on an empty database and applies later changes the same way.

## Setup (once)

1. Have an empty Postgres database (local install, Docker, or Azure).
2. Copy `.env.example` to `.env` and set `DATABASE_URL`:

```
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:5432/DATABASE
```

## Create or update the schema

From `services/pipeline`, with the virtualenv active:

```bash
alembic upgrade head
```

- **Empty database:** creates the current tables (right now: `cities`) and `alembic_version`.
- **Database that already has migrations:** applies only new revisions. Safe to run again.

## Later schema changes

1. Change models in `services/pipeline/src/pipeline/db/models.py`.
2. Add a revision: `alembic revision -m "describe the change"` (fill in `upgrade` / `downgrade`).
3. Run `alembic upgrade head` again.

Undo the last change with `alembic downgrade -1`.
