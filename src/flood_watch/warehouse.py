"""Shared path helpers for the flood_watch project's bronze/silver/gold
Parquet layout under data/."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"


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
