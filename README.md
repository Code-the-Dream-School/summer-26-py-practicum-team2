# City Air Tracker

This repo contains a Code the Dream-friendly batch ETL project that:

1. Geocodes global cities to lat/lon
2. Pulls OpenWeather Air Pollution historical data
3. Transforms PostgreSQL-backed raw response records into a gold dataset
4. Writes the gold dataset to PostgreSQL
5. Serves a React dashboard backed by a Python API over PostgreSQL data

The pipeline uses DB-first gold persistence by default, with PostgreSQL as the primary gold-data target
City configuration, geocoding cache, and raw extract persistence are in PostgreSQL as runtime state.
The same PostgreSQL runtime path can target either local Docker/Postgres or managed Azure Database for PostgreSQL through environment configuration.

## Team repository setup (Sprint 0)

One student should complete the initial setup below. These instructions follow the repository setup used in the Code the Dream Python 100 homework repository.

1. Sign into your GitHub, and create a repository for your team's City Air Tracker project. It must be a public repository. Do not create a `.gitignore` or a `README.md`.
2. On your computer, clone the [`city-air-tracker-student`](https://github.com/Code-the-Dream-School/city-air-tracker-student) repository. (Do not clone the repository you just created.)
3. Change to the `city-air-tracker-student` directory you just cloned. Enter the following commands, replacing `team-repository-owner` and `team-repository-name` with the values for the repository your team created:

```shell
# if you use SSH authentication:
git remote set-url origin git@github.com:team-repository-owner/team-repository-name.git

# if you use token-based authentication:
git remote set-url origin https://github.com/team-repository-owner/team-repository-name

git remote add upstream https://github.com/Code-the-Dream-School/city-air-tracker-student
git push origin main
```

4. In the team's new GitHub repository, add every student and mentor on the team as a collaborator.
5. All other team members should clone the new team repository:

```shell
git clone https://github.com/team-repository-owner/team-repository-name.git
cd team-repository-name
git remote add upstream https://github.com/Code-the-Dream-School/city-air-tracker-student
```

Each team member can confirm both remotes with:

```shell
git remote -v
```

`origin` should point to the team's repository. `upstream` should point to the Code the Dream starter repository.

## How to run this

There is no `docker-compose.yml` on `main`. Start Postgres with Docker, then migrate, seed, run the pipeline, and open the dashboard. Fuller detail: [`docs/setup/local_storage_workflow.md`](docs/setup/local_storage_workflow.md).

### 1. Postgres

Docker Desktop must be running. From any terminal:

```shell
docker run --name cityair-postgres \
  -e POSTGRES_USER=cityair \
  -e POSTGRES_PASSWORD=cityair \
  -e POSTGRES_DB=cityair \
  -p 5432:5432 \
  -d postgres:17
```

If that container already exists:

```shell
docker start cityair-postgres
```

`localhost:5432` is the published Docker port, not a separate Windows Postgres service. Confirm with `docker ps`. Do not start a second container on the same port.

### 2. Python env and `.env`

From the repository root:

```shell
python -m venv .venv
source .venv/Scripts/activate   # Git Bash on Windows; otherwise `.venv/bin/activate`
pip install -r requirements.txt
cp .env.example .env
```

Keep `.env` at the repo root. Set `DATABASE_URL` (the example matches the container above) and `OPENWEATHER_API_KEY`.

### 3. Schema and cities

```shell
cd services/pipeline
alembic upgrade head
python seed_cities.py
```

Re-run seed after you edit `services/pipeline/config/cities.csv`.

### 4. Pipeline (live OpenWeather)

Still in `services/pipeline`:

```shell
PYTHONPATH=src python -m pipeline.cli --history-hours 24
```

Extract persists raw responses, then transform writes `gold_air_quality`. The first run can take several minutes.

### 5. Dashboard

Two terminals, from the repository root:

```shell
python services/dashboard/server.py
```

```shell
cd services/dashboard/frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173). If the UI has no cities, gold is empty — finish step 4 first.

## Additional docs

Browse `docs/README.md` for the full categorized index.

- `docs/milestones/week0.md`
- `docs/milestones/week1.md`
- `docs/setup/local_postgresql_first_workflow.md`
- `docs/setup/run_and_debug_guide.md`
- `docs/setup/github_quality_gates_setup.md`
- `docs/collaboration/github_feature_branch_pr_guide.md`
- `docs/collaboration/pr_review_best_practices.md`
- `docs/collaboration/what_is_a_data_pipeline.md`
- `docs/architecture/architecture.md`
- `docs/architecture/data_flow_diagram.md`
- `docs/architecture/postgresql_schema_design.md`
- `docs/reference/data_dictionary.md`
- `docs/reference/openweather_environmental_api_fields_reference.md`