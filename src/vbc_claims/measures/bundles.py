from __future__ import annotations

from datetime import date

import pandas as pd
from sqlalchemy import text

from vbc_claims.io.db import db_connection


def compute_episode_spend_in_period(month_start: date, month_end: date) -> pd.DataFrame:
    """
    Roll up allowed amounts for medical and pharmacy claims assigned to episodes,
    filtered by service/fill date within the reporting period.
    """
    sql = text(
        """
        WITH med AS (
          SELECT
            i.episode_id,
            SUM(cl.allowed_amount) AS medical_allowed
          FROM vbc.claim_episode_assignment a
          JOIN vbc.member_episode_instance i ON i.instance_id = a.instance_id
          JOIN vbc.claim_header ch ON ch.claim_id = a.medical_claim_id
          JOIN vbc.claim_line cl ON cl.claim_id = ch.claim_id
          WHERE a.claim_source = 'medical'
            AND ch.service_start >= :ms
            AND ch.service_start <= :me
          GROUP BY i.episode_id
        ),
        rx AS (
          SELECT
            i.episode_id,
            SUM(rl.allowed_amount) AS pharmacy_allowed
          FROM vbc.claim_episode_assignment a
          JOIN vbc.member_episode_instance i ON i.instance_id = a.instance_id
          JOIN vbc.rx_claim_line rl ON rl.rx_line_id = a.rx_line_id
          JOIN vbc.rx_claim_header rh ON rh.rx_claim_id = rl.rx_claim_id
          WHERE a.claim_source = 'pharmacy'
            AND rh.fill_date >= :ms
            AND rh.fill_date <= :me
          GROUP BY i.episode_id
        ),
        inst AS (
          SELECT episode_id, COUNT(*)::bigint AS instance_count
          FROM vbc.member_episode_instance
          GROUP BY episode_id
        )
        SELECT
          e.episode_id,
          e.display_name,
          COALESCE(inst.instance_count, 0) AS open_instances,
          COALESCE(med.medical_allowed, 0) AS medical_allowed_in_period,
          COALESCE(rx.pharmacy_allowed, 0) AS pharmacy_allowed_in_period
        FROM vbc.episode_definition e
        LEFT JOIN inst ON inst.episode_id = e.episode_id
        LEFT JOIN med ON med.episode_id = e.episode_id
        LEFT JOIN rx ON rx.episode_id = e.episode_id
        ORDER BY e.episode_id
        """
    )

    with db_connection() as conn:
        return pd.read_sql(sql, conn, params={"ms": month_start, "me": month_end})
