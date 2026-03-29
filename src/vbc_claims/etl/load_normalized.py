from __future__ import annotations

from pathlib import Path

import pandas as pd
from sqlalchemy import text

from vbc_claims.etl.validate import coerce_null_strings, validate_medical_claims, validate_pharmacy
from vbc_claims.io.db import db_connection


def _append_df(df: pd.DataFrame, table: str) -> None:
    with db_connection() as conn:
        df.to_sql(table, conn, schema="vbc", if_exists="append", index=False, method="multi", chunksize=5000)


def load_normalized_medical_claims(
    claim_header_csv: str,
    claim_line_csv: str,
    diagnosis_csv: str,
    truncate: bool = False,
) -> int:
    """Load normalized medical claims CSVs into vbc.claim_* tables."""
    header_df = pd.read_csv(claim_header_csv)
    lines_df = pd.read_csv(claim_line_csv)
    dx_df = pd.read_csv(diagnosis_csv)
    validate_medical_claims(header_df, lines_df, dx_df)

    with db_connection() as conn:
        if truncate:
            conn.execute(text("TRUNCATE TABLE vbc.diagnosis, vbc.claim_line, vbc.claim_header RESTART IDENTITY CASCADE"))

    _append_df(header_df, "claim_header")
    _append_df(lines_df, "claim_line")
    _append_df(dx_df, "diagnosis")
    return len(header_df)


def load_normalized_pharmacy_claims(
    rx_header_csv: str,
    rx_line_csv: str,
    truncate: bool = False,
) -> int:
    rx_h = pd.read_csv(rx_header_csv)
    rx_l = pd.read_csv(rx_line_csv)
    rx_h = coerce_null_strings(rx_h, ["pharmacy_npi", "prescriber_npi"])
    validate_pharmacy(rx_h, rx_l)

    with db_connection() as conn:
        if truncate:
            conn.execute(text("TRUNCATE TABLE vbc.rx_claim_line, vbc.rx_claim_header RESTART IDENTITY CASCADE"))

    _append_df(rx_h, "rx_claim_header")
    _append_df(rx_l, "rx_claim_line")
    return len(rx_h)


def load_normalized_dataset_dir(
    dataset_dir: str,
    *,
    load_medical: bool = True,
    truncate_medical: bool = True,
    load_rx: bool = True,
    truncate_rx: bool = True,
) -> dict[str, int]:
    """Load from a directory containing standard CSV filenames."""
    base = Path(dataset_dir)
    counts: dict[str, int] = {}
    if load_medical:
        counts["medical_headers"] = load_normalized_medical_claims(
            str(base / "claim_header.csv"),
            str(base / "claim_line.csv"),
            str(base / "diagnosis.csv"),
            truncate=truncate_medical,
        )
    rx_h = base / "rx_claim_header.csv"
    rx_l = base / "rx_claim_line.csv"
    if load_rx and rx_h.exists() and rx_l.exists():
        counts["rx_headers"] = load_normalized_pharmacy_claims(str(rx_h), str(rx_l), truncate=truncate_rx)
    return counts
