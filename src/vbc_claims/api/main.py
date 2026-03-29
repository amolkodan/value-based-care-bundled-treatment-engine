from __future__ import annotations

from datetime import date

import pandas as pd
import uvicorn
from fastapi import FastAPI
from sqlalchemy import text

from vbc_claims.analytics.reporting import build_bundle_episode_report
from vbc_claims.api.schemas import AssignEpisodesRequest, AssignEpisodesResponse
from vbc_claims.episodes.engine import assign_episodes_for_all_members
from vbc_claims.io.db import db_connection
from vbc_claims.quality.checks import run_reconciliation_report
from vbc_claims.transforms.member_months import build_member_months

app = FastAPI(
    title="VBC Bundled Claims API",
    version="0.1.0",
    description="API service for episode catalog, assignment runs, and bundle reporting.",
)


@app.get("/health")
def health() -> dict[str, object]:
    return {"status": "ok", "service": "vbc-claims-api"}


@app.get("/episodes/catalog")
def episode_catalog(limit: int = 200) -> list[dict[str, object]]:
    sql = text(
        """
        SELECT episode_id, display_name, clinical_domain, bundle_type, model_version, effective_start, effective_end
        FROM vbc.episode_definition
        ORDER BY episode_id
        LIMIT :lim
        """
    )
    with db_connection() as conn:
        rows = conn.execute(sql, {"lim": limit}).mappings().all()
    return [dict(r) for r in rows]


@app.post("/episodes/assign/run", response_model=AssignEpisodesResponse)
def run_episode_assignment(req: AssignEpisodesRequest) -> AssignEpisodesResponse:
    if req.run_member_months:
        build_member_months(date.fromisoformat(req.start_month), date.fromisoformat(req.end_month))
    inst_n, asg_n = assign_episodes_for_all_members()
    return AssignEpisodesResponse(episode_instances=inst_n, episode_assignments=asg_n)


@app.get("/episodes/assignments")
def assignments(limit: int = 500) -> list[dict[str, object]]:
    sql = text(
        """
        SELECT
          a.assignment_id,
          i.episode_id,
          i.member_id,
          a.claim_source,
          a.medical_claim_id,
          a.rx_line_id,
          a.allocation_weight,
          a.allocation_pct,
          a.allocated_allowed_amount,
          a.allocated_paid_amount,
          a.match_explanation
        FROM vbc.claim_episode_assignment a
        JOIN vbc.member_episode_instance i ON i.instance_id = a.instance_id
        ORDER BY a.assignment_id DESC
        LIMIT :lim
        """
    )
    with db_connection() as conn:
        rows = conn.execute(sql, {"lim": limit}).mappings().all()
    return [dict(r) for r in rows]


@app.get("/reports/bundles")
def report_bundles(month: str = "2025-12") -> dict[str, object]:
    month_start = date.fromisoformat(f"{month}-01")
    month_end = (pd.Timestamp(month_start) + pd.offsets.MonthEnd(0)).date()
    rep = build_bundle_episode_report(month_start=month_start, month_end=month_end)
    return {
        "episode_catalog_summary": rep.episode_catalog_summary.to_dict(orient="records"),
        "episode_spend": rep.episode_spend.to_dict(orient="records"),
        "reconciliation": run_reconciliation_report(),
    }


def run() -> None:
    uvicorn.run("vbc_claims.api.main:app", host="0.0.0.0", port=8001, reload=False)


if __name__ == "__main__":
    run()

