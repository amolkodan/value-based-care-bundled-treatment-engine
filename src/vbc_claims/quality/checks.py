from __future__ import annotations

from typing import Any

from sqlalchemy import text

from vbc_claims.io.db import db_connection


def run_reconciliation_report() -> dict[str, Any]:
    """
    Lightweight reconciliation suitable for orchestration hooks (Airflow/Dagster).
    Returns row counts and simple integrity signals.
    """
    checks: dict[str, Any] = {}
    stmts = {
        "members": "SELECT COUNT(*) AS n FROM vbc.member",
        "claim_headers": "SELECT COUNT(*) AS n FROM vbc.claim_header",
        "claim_lines": "SELECT COUNT(*) AS n FROM vbc.claim_line",
        "rx_headers": "SELECT COUNT(*) AS n FROM vbc.rx_claim_header",
        "rx_lines": "SELECT COUNT(*) AS n FROM vbc.rx_claim_line",
        "episodes": "SELECT COUNT(*) AS n FROM vbc.episode_definition",
        "episode_rules": "SELECT COUNT(*) AS n FROM vbc.episode_rule",
        "episode_instances": "SELECT COUNT(*) AS n FROM vbc.member_episode_instance",
        "episode_assignments": "SELECT COUNT(*) AS n FROM vbc.claim_episode_assignment",
    }
    with db_connection() as conn:
        for k, sql in stmts.items():
            try:
                row = conn.execute(text(sql)).fetchone()
                checks[k] = int(row[0]) if row else 0
            except Exception as e:  # noqa: BLE001 - surface missing tables in dev
                checks[k] = f"error: {e}"

    orphan_sql = text(
        """
        SELECT COUNT(*) AS n
        FROM vbc.claim_line cl
        LEFT JOIN vbc.claim_header ch ON ch.claim_id = cl.claim_id
        WHERE ch.claim_id IS NULL
        """
    )
    with db_connection() as conn:
        try:
            r = conn.execute(orphan_sql).fetchone()
            checks["orphan_claim_lines"] = int(r[0]) if r else 0
        except Exception as e:  # noqa: BLE001
            checks["orphan_claim_lines"] = f"error: {e}"

    checks["status"] = "ok"
    return checks
