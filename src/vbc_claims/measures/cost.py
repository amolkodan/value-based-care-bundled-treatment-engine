from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pandas as pd
from sqlalchemy import text

from vbc_claims.io.db import db_connection


@dataclass(frozen=True)
class PmpmResult:
    month_start: date
    payer: str
    product: str
    member_months: int
    total_allowed: float
    pmpm: float


def compute_pmpm(start_month: date, end_month: date) -> pd.DataFrame:
    sql = text(
        """
        WITH member_month AS (
          SELECT member_id, month_start, payer, product
          FROM vbc.member_month
          WHERE month_start >= :start_month AND month_start <= :end_month
        ), allowed AS (
          SELECT
            ch.member_id,
            date_trunc('month', ch.service_start)::date AS month_start,
            SUM(cl.allowed_amount) AS allowed_amount
          FROM vbc.claim_header ch
          JOIN vbc.claim_line cl ON cl.claim_id = ch.claim_id
          GROUP BY ch.member_id, date_trunc('month', ch.service_start)::date
        )
        SELECT
          m.month_start,
          m.payer,
          m.product,
          COUNT(DISTINCT m.member_id) AS member_months,
          COALESCE(SUM(a.allowed_amount), 0) AS total_allowed,
          CASE WHEN COUNT(DISTINCT m.member_id) > 0 THEN COALESCE(SUM(a.allowed_amount), 0) / COUNT(DISTINCT m.member_id) ELSE 0 END AS pmpm
        FROM member_month m
        LEFT JOIN allowed a
          ON a.member_id = m.member_id
          AND a.month_start = m.month_start
        GROUP BY m.month_start, m.payer, m.product
        ORDER BY m.month_start, m.payer, m.product
        """
    )

    with db_connection() as conn:
        return pd.read_sql(sql, conn, params={"start_month": start_month, "end_month": end_month})
