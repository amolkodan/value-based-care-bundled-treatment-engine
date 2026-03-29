from __future__ import annotations

import os
from pathlib import Path

import pytest

from vbc_claims.etl.init_db import init_db
from vbc_claims.etl.pipeline import run_full_pipeline
from vbc_claims.etl.synthetic import generate_synthetic_claims_dataset

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_INTEGRATION") != "1",
    reason="Set RUN_INTEGRATION=1 and start Postgres to run integration tests",
)


def test_full_pipeline_creates_episode_assignments(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[1]
    bundled = repo / "data" / "sample" / "bundled"
    init_db()
    generate_synthetic_claims_dataset(
        output_dir=str(tmp_path),
        rows=400,
        members=60,
        providers=12,
        seed=7,
    )
    out = run_full_pipeline(
        data_dir=str(tmp_path),
        bundled_catalog_dir=str(bundled),
        skip_synthetic_load=False,
        assign_episodes=True,
    )
    assert int(out.get("episode_instances", 0)) > 0
    assert int(out.get("episode_assignments", 0)) > 0
    assert out.get("reconciliation", {}).get("status") == "ok"
