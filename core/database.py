"""CSV-backed repository. Swap loaders later for PostgreSQL/PostGIS."""

from __future__ import annotations

import csv
from copy import deepcopy
from pathlib import Path
from typing import Any

from core.config import DATA_DIR


TABLES = ("incidents", "resources", "hospitals", "shelters", "roads")


def _read_csv(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def coerce_row(table: str, row: dict[str, Any]) -> dict[str, Any]:
    out = dict(row)
    float_keys = {"lat", "lon", "from_lat", "from_lon", "to_lat", "to_lon", "priority_score"}
    int_keys = {
        "severity",
        "people_affected",
        "vulnerable_population",
        "capacity",
        "total_beds",
        "available_beds",
        "occupied",
    }
    bool_keys = {"medical_emergency", "emergency_capability"}
    for key in float_keys:
        if key in out and out[key] not in ("", None):
            try:
                out[key] = float(out[key])
            except (TypeError, ValueError):
                pass
    for key in int_keys:
        if key in out and out[key] not in ("", None):
            try:
                out[key] = int(float(out[key]))
            except (TypeError, ValueError):
                pass
    for key in bool_keys:
        if key in out:
            val = out[key]
            if isinstance(val, bool):
                continue
            text = str(val).strip().lower()
            out[key] = text in {"1", "true", "yes", "y"}
    if table == "incidents":
        out.setdefault("status", "Active")
        out.setdefault("accessibility", "Open")
        out.setdefault("priority_score", 0)
        out.setdefault("vulnerable_population", 0)
        out.setdefault("breakdown_json", "")
    return out


class CsvRepository:
    def __init__(self, data_dir: Path | None = None) -> None:
        self.data_dir = Path(data_dir) if data_dir else DATA_DIR

    def load_all(self) -> dict[str, list[dict[str, Any]]]:
        bundle: dict[str, list[dict[str, Any]]] = {}
        for table in TABLES:
            rows = _read_csv(self.data_dir / f"{table}.csv")
            bundle[table] = [coerce_row(table, r) for r in rows]
        return bundle

    def save_table(self, table: str, rows: list[dict[str, Any]]) -> None:
        if table not in TABLES:
            raise ValueError(f"Unknown table {table}")
        _write_csv(self.data_dir / f"{table}.csv", rows)

    def snapshot(self, bundle: dict[str, list[dict[str, Any]]]) -> dict[str, list[dict[str, Any]]]:
        return deepcopy(bundle)


def load_demo_bundle(data_dir: Path | None = None) -> dict[str, list[dict[str, Any]]]:
    repo = CsvRepository(data_dir)
    data = repo.load_all()
    # Safe defaults if a CSV is missing.
    for table in TABLES:
        data.setdefault(table, [])
    return data
