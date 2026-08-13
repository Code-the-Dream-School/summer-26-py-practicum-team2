import csv
from pathlib import Path

REQUIRED_FIELDS = {"city_id", "city_name", "country", "is_active"}


def normalize_city_row(row: dict[str, str]) -> dict[str, str]:
    return {
        "city_id": row["city_id"].strip(),
        "city_name": row["city_name"].strip(),
        "state": row.get("state", "").strip(),
        "country": row["country"].strip().upper(),
        "is_active": row["is_active"].strip().upper(),
    }


def has_required_values(row: dict[str, str]) -> bool:
    return all(row.get(field, "").strip() for field in REQUIRED_FIELDS)


def is_valid_active_value(value: str) -> bool:
    cleaned = value.strip().upper()
    return cleaned in ("TRUE", "FALSE")


def is_valid_country_code(value: str) -> bool:
    cleaned = value.strip().upper()
    return len(cleaned) == 2 and cleaned.isalpha()


def is_active_city(row: dict[str, str]) -> bool:
    return row.get("is_active", "").strip().upper() == "TRUE"


def is_valid_city_row(row: dict[str, str]) -> bool:
    return (
        has_required_values(row)
        and is_valid_country_code(row.get("country", ""))
        and is_valid_active_value(row.get("is_active", ""))
    )


def has_required_columns(fieldnames: list[str] | None) -> bool:
    if fieldnames is None:
        return False
    return all(field in fieldnames for field in REQUIRED_FIELDS)

# Load, validate, normalize, and return active cities from a CSV file.
def load_cities(file_path: str | Path) -> list[dict[str, str]]:
    result = []
    with open(file_path, mode='r', encoding='utf-8') as file:
        reader = csv.DictReader(file)

        if not has_required_columns(reader.fieldnames):
            raise ValueError("CSV file is missing required columns")

        for row in reader:
            if not is_valid_city_row(row):
                continue

            normalized = normalize_city_row(row)

            if not is_active_city(normalized):
                continue

            result.append(normalized)

    return result
