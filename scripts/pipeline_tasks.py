"""
Orchestrator-friendly task entrypoints (Airflow / Dagster / Prefect).

Each function is side-effecting against the configured DATABASE_URL.
"""

from __future__ import annotations

from datetime import date

from vbc_claims.episodes.engine import assign_episodes_for_all_members
from vbc_claims.etl.init_db import init_db
from vbc_claims.etl.load_episodes import load_episodes_from_dir
from vbc_claims.etl.load_sample import load_synthetic_dataset
from vbc_claims.quality.checks import run_reconciliation_report
from vbc_claims.transforms.member_months import build_member_months


def task_init_db() -> None:
    init_db()


def task_load_synthetic_claims(dataset_dir: str) -> None:
    load_synthetic_dataset(dataset_dir)


def task_load_episode_catalog(catalog_dir: str, *, truncate: bool = True) -> None:
    load_episodes_from_dir(catalog_dir, truncate=truncate)


def task_build_member_months(start_month: date, end_month: date) -> None:
    build_member_months(start_month, end_month)


def task_assign_episodes() -> tuple[int, int]:
    return assign_episodes_for_all_members()


def task_reconciliation() -> dict[str, object]:
    return run_reconciliation_report()
