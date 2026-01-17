from __future__ import annotations

from datetime import date

import pandas as pd
from sqlalchemy import text

from vbc_claims.io.db import db_connection


def build_member_months(start_month: date, end_month: date) -> None:
    month_starts = pd.date_range(start=start_month, end=end_month, freq="MS").date

    with db_connection() as conn:
        conn.execute(text("TRUNCATE TABLE vbc.member_month"))

        eligibility = pd.read_sql(text("SELECT member_id, coverage_start, coverage_end, payer, product FROM vbc.member_eligibility"), conn)

    rows = []
    for _, r in eligibility.iterrows():
        for m in month_starts:
            month_end = (pd.Timestamp(m) + pd.offsets.MonthEnd(0)).date()
            if r["coverage_start"] <= month_end and r["coverage_end"] >= m:
                rows.append({"member_id": r["member_id"], "month_start": m, "payer": r["payer"], "product": r["product"]})

    member_month_df = pd.DataFrame(rows)
    with db_connection() as conn:
        member_month_df.to_sql("member_month", conn, schema="vbc", if_exists="append", index=False, method="multi", chunksize=5000)
