from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pandas as pd

from vbc_claims.contracts.shared_savings import compute_shared_savings
from vbc_claims.measures.cost import compute_pmpm
from vbc_claims.risk.hcc import compute_member_simple_risk_scores


@dataclass(frozen=True)
class PerformanceReport:
    pmpm: pd.DataFrame
    risk: pd.DataFrame
    shared_savings: pd.DataFrame


def build_performance_report(month_start: date, month_end: date, contract_id: str | None = None) -> PerformanceReport:
    pmpm_df = compute_pmpm(month_start, month_end)

    performance_year = int(month_start.year)
    risk_df = compute_member_simple_risk_scores(performance_year)

    if contract_id is None:
        shared_df = pd.DataFrame()
    else:
        shared_df = compute_shared_savings(contract_id, performance_year)

    return PerformanceReport(pmpm=pmpm_df, risk=risk_df, shared_savings=shared_df)
