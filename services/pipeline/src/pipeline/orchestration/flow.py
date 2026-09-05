from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from prefect import flow, task

from pipeline.db.cities import load_cities_from_db
from pipeline.extract.pipeline import extract_cities
from pipeline.run_tracking import PipelineRunStatusUpdate, create_pipeline_run, update_pipeline_run_status

log = logging.getLogger(__name__)


@task(name="load-cities")
def load_cities_task() -> list[dict[str, str]]:
    return load_cities_from_db(active_only=True)


@task(name="extract")
def extract_task(cities: list[dict[str, str]], history_hours: int) -> list[dict]:
    return extract_cities(cities, history_hours=history_hours)

# Runs the pipeline's ETL stages in order.
@flow(name="city-air-tracker-pipeline")
def run_pipeline_flow(history_hours: int = 24, source: str = "openweather") -> list[dict]:
    window_end = datetime.now(timezone.utc)
    window_start = window_end - timedelta(hours=history_hours)
    run_id = window_end.strftime("%Y%m%dT%H%M%SZ")
    pipeline_run_id = create_pipeline_run(
        run_id=run_id,
        source=source,
        history_hours=history_hours,
        window_start_utc=window_start,
        window_end_utc=window_end,
    )
    log.info("Pipeline run %s started (pipeline_run_id=%s)", run_id, pipeline_run_id)

    try:
        cities = load_cities_task()
        results = extract_task(cities, history_hours)
        log.info("Extract stage complete: %d/%d cities", len(results), len(cities))

        update_pipeline_run_status(
            run_id,
            PipelineRunStatusUpdate(
                status="succeeded",
                city_count=len(cities),
                raw_response_count=len(results),
                finished_at=datetime.now(timezone.utc),
            ),
        )
        return results
    except Exception as exc:
        log.exception("Pipeline run %s failed", run_id)
        update_pipeline_run_status(
            run_id,
            PipelineRunStatusUpdate(
                status="failed",
                error_message=str(exc),
                finished_at=datetime.now(timezone.utc),
            ),
        )
        raise
