"""Shared local DuckDB connection for the flood_watch project.

Bronze/silver/gold data lives as Parquet under data/; DuckDB reads it
directly via read_parquet() rather than duplicating storage.
"""

from pathlib import Path

import duckdb

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = DATA_DIR / "flood_watch.duckdb"


def get_connection() -> duckdb.DuckDBPyConnection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(DB_PATH))


def bronze_path(source: str) -> Path:
    path = DATA_DIR / "bronze" / source
    path.mkdir(parents=True, exist_ok=True)
    return path


def silver_path(table: str) -> Path:
    path = DATA_DIR / "silver" / table
    path.mkdir(parents=True, exist_ok=True)
    return path


def gold_path(table: str) -> Path:
    path = DATA_DIR / "gold" / table
    path.mkdir(parents=True, exist_ok=True)
    return path
