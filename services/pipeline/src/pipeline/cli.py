from __future__ import annotations

import argparse

from pipeline.orchestration.flow import run_pipeline_flow


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the City Air Tracker ETL pipeline.")
    parser.add_argument(
        "--history-hours",
        type=int,
        default=24,
        help="Hours of air quality history to extract per city (default: 24).",
    )
    args = parser.parse_args(argv)

    results = run_pipeline_flow(history_hours=args.history_hours)
    print(f"Extract stage complete: {len(results)} cities extracted.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
