# City Air Tracker — Dashboard (prototype)

Dashboard service with a Flask API and React frontend. The API reads the
pipeline's PostgreSQL `cities` and `gold_air_quality` tables.

## Structure

```
services/dashboard/
├── server.py          # Flask API over PostgreSQL dashboard tables
└── frontend/           # Vite + React + TypeScript + Tailwind v4
    └── src/
        ├── api/client.ts          # fetch functions the frontend uses
        ├── components/
        │   ├── charts/
        │   │   ├── TrendChart.tsx        # hourly trend, recharts (line)
        │   │   ├── AggregatesChart.tsx   # daily/weekly AQI history, recharts (bar)
        │   │   └── ComparisonChart.tsx   # multi-city AQI comparison, recharts (line)
        │   ├── city/
        │   │   ├── CitySummary.tsx       # selected city's current AQI
        │   │   ├── AqiBadge.tsx          # icon + label for AQI 1-5
        │   │   ├── CitySelector.tsx      # dropdown (single city)
        │   │   ├── CityMultiSelect.tsx   # chip toggles for picking cities to compare
        │   │   └── CityOverviewGrid.tsx  # all cities at a glance, clickable
        │   ├── layout/
        │   │   ├── Header.tsx
        │   │   ├── Footer.tsx
        │   │   └── Tabs.tsx              # generic tab switcher
        │   └── status/
        │       ├── LoadingState.tsx      # skeleton shown while fetching
        │       └── ErrorState.tsx        # error card with a "Try again" button
        └── App.tsx      # wires everything together, fetches on load
```

## Running it locally

You need both servers running at the same time, in two terminals.

**Backend (Flask):**
```bash
cd services/dashboard
source ../../.venv/bin/activate   # or wherever your venv lives
pip install -r ../../requirements.txt
python server.py
```
Runs on `http://localhost:8000`.

**Frontend (Vite):**
```bash
cd services/dashboard/frontend
npm install                        # first time only
npm run dev
```
Runs on `http://localhost:5173`.

## API endpoints

| Endpoint | Returns |
|---|---|
| `GET /api/cities` | `[{ id, cityName }]` — active cities with available readings |
| `GET /api/cities/overview` | `[{ id, cityName, aqi, observedAt }]` — latest reading for each active city |
| `GET /api/cities/<id>/trend` | `{ id, cityName, aqi, trend: [{ observedAt, aqi }] }` — last 24 hours, ordered by UTC timestamp |
| `GET /api/cities/<id>/aggregates?period=daily\|weekly` | `[{ date, aqi }]` — 14-day daily averages or seven-day grouped averages |

## UI layout

The main view has three tabs above the chart area:

- **Hourly** — `TrendChart`, the selected city's recent hourly AQI (line)
- **History** — `AggregatesChart`, daily or weekly AQI (bar), with a
  Daily/Weekly toggle built into the component itself
- **Compare** — `CityMultiSelect` (chip toggles) + `ComparisonChart`, one
  line per selected city

Only one tab's chart renders at a time, controlled by `activeTab` state in
`App.tsx`.

## Data shape (the contract to build against)

```ts
type CityListItem = { id: string; cityName: string };
type CityOverview = { id: string; cityName: string; aqi: number; observedAt: string };
type CityTrend = {
  id: string;
  cityName: string;
  aqi: number | null;
  trend: { observedAt: string; aqi: number }[];
};
type AggregatePoint = { date: string; aqi: number };
```

`aqi` is OpenWeather's 1-5 scale (1 = Good, 5 = Very Poor) — not the US EPA
0-500 scale.

## Loading / error handling

`App.tsx` shows `LoadingState` (a pulsing skeleton) while the initial fetch
is in flight, and `ErrorState` (a card with a "Try again" button that
re-triggers the fetch) if it fails — for example, if the Flask server isn't
running. Both replace the earlier plain-text placeholders.

## Configuration

- Set `DATABASE_URL` in the repository `.env` file. It uses the same
  SQLAlchemy PostgreSQL URL as the pipeline, for example:
  `postgresql+psycopg://cityair:cityair@localhost:5432/cityair`.
- The database must have the pipeline migrations applied and contain active
  cities with rows in `gold_air_quality` before the dashboard has data to show.
- No environment variable for the frontend API base URL — it's hardcoded in
  `src/api/client.ts` (`http://localhost:8000/api`)
- `CitySummary` and `CityOverviewGrid` currently show overlapping info
  (both display the selected city's AQI) — left in on purpose so the team
  can decide whether to drop one
- `ComparisonChart` merges city readings by their UTC `observedAt` timestamp,
  so a missing reading appears as a gap rather than being matched to a
  display label

## Known redundancy / open decisions

- `CitySelector` (dropdown) and `CityOverviewGrid` (clickable cards) both
  let you pick a city — both are wired to the same state, so removing
  either one is a one-line change in `App.tsx` if we want to simplify
