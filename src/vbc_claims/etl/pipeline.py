from __future__ import annotations

from datetime import date
from pathlib import Path

from vbc_claims.episodes.engine import assign_episodes_for_all_members
from vbc_claims.etl.load_episodes import load_episodes_from_dir
from vbc_claims.etl.load_sample import load_synthetic_dataset
from vbc_claims.transforms.member_months import build_member_months
from vbc_claims.quality.checks import run_reconciliation_report


def run_full_pipeline(
    *,
    data_dir: str | None = None,
    bundled_catalog_dir: str | None = None,
    start_month: date | None = None,
    end_month: date | None = None,
    skip_synthetic_load: bool = False,
    assign_episodes: bool = True,
) -> dict[str, object]:
    """
    End-to-end demo pipeline: load claims (synthetic dir or normalized dir), episode catalog, member months, assignment, DQ.
    """
    root = Path(__file__).resolve().parents[3]
    data_dir = data_dir or str(root / "data" / "synthetic")
    bundled_catalog_dir = bundled_catalog_dir or str(root / "data" / "sample" / "bundled")
    start_month = start_month or date(2025, 1, 1)
    end_month = end_month or date(2025, 12, 1)

    out: dict[str, object] = {}
    if not skip_synthetic_load:
        load_synthetic_dataset(data_dir)
        out["load_synthetic"] = data_dir

    load_episodes_from_dir(bundled_catalog_dir, truncate=True)
    out["episode_catalog"] = bundled_catalog_dir

    build_member_months(start_month, end_month)
    out["member_months"] = f"{start_month}..{end_month}"

    if assign_episodes:
        inst_n, asg_n = assign_episodes_for_all_members()
        out["episode_instances"] = inst_n
        out["episode_assignments"] = asg_n

    out["reconciliation"] = run_reconciliation_report()
    return out
