from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from prefect import flow, task

from pipeline.db.cities import load_cities_from_db
from pipeline.db.models import RawAirPollutionResponse
from pipeline.db.gold import GoldUpsertResult
from pipeline.extract.pipeline import extract_cities
from pipeline.run_tracking import PipelineRunStatusUpdate, create_pipeline_run, update_pipeline_run_status
from pipeline.transform.air_quality import run_transform_stage

log = logging.getLogger(__name__)


@task(name="load-cities")
def load_cities_task() -> list[dict[str, str]]:
    return load_cities_from_db(active_only=True)


@task(name="extract")
def extract_task(
    cities: list[dict[str, str]],
    window_start: datetime,
    window_end: datetime,
    run_id: int,
) -> list[RawAirPollutionResponse]:
    return extract_cities(cities, window_start=window_start, window_end=window_end, run_id=run_id)


@task(name="transform")
def transform_task(run_id: int) -> GoldUpsertResult:
    return run_transform_stage(run_id=run_id)


# Runs the pipeline's ETL stages in order: load cities, extract raw responses, transform to gold.
@flow(name="city-air-tracker-pipeline")
def run_pipeline_flow(history_hours: int = 24, source: str = "openweather") -> GoldUpsertResult:
    window_end = datetime.now(timezone.utc)
    window_start = window_end - timedelta(hours=history_hours)
    run_label = window_end.strftime("%Y%m%dT%H%M%SZ")
    pipeline_run_id = create_pipeline_run(run_type="full", triggered_by=source, run_label=run_label)
    log.info("Pipeline run %s started (pipeline_run_id=%s)", run_label, pipeline_run_id)

    try:
        cities = load_cities_task()
        raw_responses = extract_task(cities, window_start, window_end, pipeline_run_id)
        log.info("Extract stage complete: %d/%d cities", len(raw_responses), len(cities))

        gold_result = transform_task(pipeline_run_id)
        log.info("Transform stage complete: %d gold rows stored", gold_result.stored)

        update_pipeline_run_status(
            pipeline_run_id,
            PipelineRunStatusUpdate(
                status="success",
                city_count=len(cities),
                raw_response_count=len(raw_responses),
                gold_row_count=gold_result.stored,
                finished_at=datetime.now(timezone.utc),
            ),
        )
        return gold_result
    except Exception as exc:
        log.exception("Pipeline run %s failed", run_label)
        update_pipeline_run_status(
            pipeline_run_id,
            PipelineRunStatusUpdate(
                status="failed",
                error_summary=str(exc),
                finished_at=datetime.now(timezone.utc),
            ),
        )
        raise
