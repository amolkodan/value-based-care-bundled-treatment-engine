from __future__ import annotations

from pathlib import Path

import pandas as pd
from sqlalchemy import text

from vbc_claims.io.db import db_connection


def _copy_dataframe(df: pd.DataFrame, table: str) -> None:
    with db_connection() as conn:
        df.to_sql(table, conn, schema="vbc", if_exists="append", index=False, method="multi", chunksize=5000)


def load_synthetic_dataset(dataset_dir: str) -> None:
    base = Path(dataset_dir)
    mapping = [
        ("member.csv", "member"),
        ("provider.csv", "provider"),
        ("member_eligibility.csv", "member_eligibility"),
        ("claim_header.csv", "claim_header"),
        ("claim_line.csv", "claim_line"),
        ("diagnosis.csv", "diagnosis"),
    ]

    with db_connection() as conn:
        conn.execute(
            text(
                """
                TRUNCATE TABLE
                  vbc.claim_episode_assignment,
                  vbc.member_episode_instance,
                  vbc.diagnosis,
                  vbc.claim_line,
                  vbc.claim_header,
                  vbc.rx_claim_line,
                  vbc.rx_claim_header,
                  vbc.attribution,
                  vbc.quality_event,
                  vbc.member_month,
                  vbc.member_eligibility,
                  vbc.provider,
                  vbc.member
                RESTART IDENTITY CASCADE
                """
            )
        )

    for filename, table in mapping:
        df = pd.read_csv(base / filename)
        _copy_dataframe(df, table)

    rx_h = base / "rx_claim_header.csv"
    rx_l = base / "rx_claim_line.csv"
    if rx_h.exists() and rx_l.exists():
        _copy_dataframe(pd.read_csv(rx_h), "rx_claim_header")
        _copy_dataframe(pd.read_csv(rx_l), "rx_claim_line")
