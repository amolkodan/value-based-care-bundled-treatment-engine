from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
from sqlalchemy import text

from vbc_claims.io.db import db_connection


@dataclass(frozen=True)
class SharedSavingsSummary:
    contract_id: str
    performance_year: int
    benchmark_total: float
    actual_total: float
    gross_savings: float
    min_savings_rate: float
    shared_savings_rate: float
    savings_share: float
    quality_withhold_rate: float
    quality_withhold_amount: float
    payable_shared_savings: float


def compute_shared_savings(contract_id: str, performance_year: int) -> pd.DataFrame:
    sql = text(
        """
        WITH bench AS (
          SELECT contract_id, performance_year, benchmark_pmpm, min_savings_rate, shared_savings_rate, quality_withhold_rate
          FROM vbc.contract_benchmark
          WHERE contract_id = :contract_id AND performance_year = :performance_year
        ), mm AS (
          SELECT month_start, COUNT(DISTINCT member_id) AS member_months
          FROM vbc.member_month
          WHERE EXTRACT(YEAR FROM month_start) = :performance_year
          GROUP BY month_start
        ), actual AS (
          SELECT
            date_trunc('month', ch.service_start)::date AS month_start,
            SUM(cl.allowed_amount) AS allowed_amount
          FROM vbc.claim_header ch
          JOIN vbc.claim_line cl ON cl.claim_id = ch.claim_id
          WHERE EXTRACT(YEAR FROM ch.service_start) = :performance_year
          GROUP BY date_trunc('month', ch.service_start)::date
        ), totals AS (
          SELECT
            SUM(mm.member_months) AS total_member_months,
            COALESCE(SUM(actual.allowed_amount), 0) AS actual_total
          FROM mm
          LEFT JOIN actual ON actual.month_start = mm.month_start
        )
        SELECT
          bench.contract_id,
          bench.performance_year,
          (bench.benchmark_pmpm * totals.total_member_months) AS benchmark_total,
          totals.actual_total AS actual_total,
          ((bench.benchmark_pmpm * totals.total_member_months) - totals.actual_total) AS gross_savings,
          bench.min_savings_rate,
          bench.shared_savings_rate,
          CASE WHEN (bench.benchmark_pmpm * totals.total_member_months) > 0 THEN ((bench.benchmark_pmpm * totals.total_member_months) - totals.actual_total) / (bench.benchmark_pmpm * totals.total_member_months) ELSE 0 END AS savings_share,
          bench.quality_withhold_rate,
          CASE WHEN ((bench.benchmark_pmpm * totals.total_member_months) - totals.actual_total) > 0 THEN ((bench.benchmark_pmpm * totals.total_member_months) - totals.actual_total) * bench.shared_savings_rate * bench.quality_withhold_rate ELSE 0 END AS quality_withhold_amount,
          CASE WHEN ((bench.benchmark_pmpm * totals.total_member_months) - totals.actual_total) > 0 AND (CASE WHEN (bench.benchmark_pmpm * totals.total_member_months) > 0 THEN ((bench.benchmark_pmpm * totals.total_member_months) - totals.actual_total) / (bench.benchmark_pmpm * totals.total_member_months) ELSE 0 END) >= bench.min_savings_rate
            THEN ((bench.benchmark_pmpm * totals.total_member_months) - totals.actual_total) * bench.shared_savings_rate * (1 - bench.quality_withhold_rate)
            ELSE 0
          END AS payable_shared_savings
        FROM bench
        CROSS JOIN totals
        """
    )

    params: dict[str, str | int] = {"contract_id": contract_id, "performance_year": performance_year}
    with db_connection() as conn:
        return pd.read_sql(sql, conn, params=params)
