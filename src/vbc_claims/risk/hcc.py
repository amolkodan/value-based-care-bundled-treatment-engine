from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
from sqlalchemy import text

from vbc_claims.io.db import db_connection


@dataclass(frozen=True)
class SimpleHccWeight:
    hcc_code: str
    weight: float


DX_TO_HCC = {
    "E11.9": "HCC19",
    "I10": "HCC85",
    "N18.3": "HCC138",
    "I25.10": "HCC88",
}

HCC_WEIGHT = {
    "HCC19": 0.118,
    "HCC85": 0.03,
    "HCC138": 0.265,
    "HCC88": 0.09,
}


def compute_member_simple_risk_scores(performance_year: int) -> pd.DataFrame:
    sql = text(
        """
        SELECT
          ch.member_id,
          d.icd10_dx
        FROM vbc.claim_header ch
        JOIN vbc.diagnosis d ON d.claim_id = ch.claim_id
        WHERE EXTRACT(YEAR FROM ch.service_start) = :performance_year
        """
    )

    with db_connection() as conn:
        df = pd.read_sql(sql, conn, params={"performance_year": performance_year})

    df["hcc_code"] = df["icd10_dx"].map(DX_TO_HCC)
    df = df.dropna(subset=["hcc_code"])
    df["weight"] = df["hcc_code"].map(HCC_WEIGHT).fillna(0.0)

    risk = df.groupby("member_id", as_index=False)["weight"].sum().rename(columns={"weight": "risk_score"})
    return risk
