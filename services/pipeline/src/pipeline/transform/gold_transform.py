from __future__ import annotations

from pipeline.db.gold import GoldUpsertResult, upsert_gold
from pipeline.transform.raw_response_reader import read_gold_ready_rows


def transform_and_load_gold(pipeline_run_id: int, engine=None) -> GoldUpsertResult:
    """Read raw_responses for a pipeline run, flatten to gold-ready rows, and upsert.

    No error handling here by design — any failure (a bad DB connection, a
    malformed row that slips past flatten_raw_response, etc.) propagates to
    the caller, so the pipeline's existing run-tracking try/except is the
    single place that decides how to record a failed run.
    """
    rows = read_gold_ready_rows(pipeline_run_id=pipeline_run_id, engine=engine)
    return upsert_gold(rows, engine=engine)