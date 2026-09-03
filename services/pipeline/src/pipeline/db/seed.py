"""Seed/import city records from the configured city CSV into PostgreSQL."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from pipeline.db.cities import CityImportResult, import_cities

PIPELINE_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CITIES_FILE = PIPELINE_ROOT / "config" / "cities.csv"


def get_cities_file(path: str | None = None) -> Path:
    if path:
        return Path(path)
    configured = os.getenv("CITIES_FILE", "").strip()
    if configured:
        return Path(configured)
    return DEFAULT_CITIES_FILE


def seed_cities(path: str | None = None) -> CityImportResult:
    cities_file = get_cities_file(path)
    if not cities_file.is_file():
        raise FileNotFoundError(
            f"City file not found: {cities_file}. "
            "Pass a path or set CITIES_FILE to the configured cities.csv."
        )
    return import_cities(cities_file)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Import validated city records from CSV into PostgreSQL."
    )
    parser.add_argument(
        "cities_file",
        nargs="?",
        help="Path to cities.csv. Defaults to CITIES_FILE or services/pipeline/config/cities.csv.",
    )
    args = parser.parse_args(argv)
    result = seed_cities(args.cities_file)
    print(
        f"Imported {result.stored} cities from {result.path} "
        f"({result.active} active, {result.inactive} inactive)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
