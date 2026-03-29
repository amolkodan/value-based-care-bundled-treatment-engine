from __future__ import annotations

import re

import pandas as pd


def _require_columns(df: pd.DataFrame, name: str, cols: list[str]) -> None:
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise ValueError(f"{name}: missing columns {missing}")


def validate_medical_claims(header: pd.DataFrame, lines: pd.DataFrame, diagnosis: pd.DataFrame) -> None:
    _require_columns(
        header,
        "claim_header",
        [
            "claim_id",
            "member_id",
            "service_start",
            "service_end",
            "claim_type",
        ],
    )
    _require_columns(lines, "claim_line", ["claim_line_id", "claim_id", "line_number", "units", "charge_amount", "allowed_amount", "paid_amount"])
    _require_columns(diagnosis, "diagnosis", ["claim_id", "dx_position", "icd10_dx"])

    bad = header[header["service_end"] < header["service_start"]]
    if not bad.empty:
        raise ValueError(f"claim_header: {len(bad)} rows have service_end < service_start")

    line_claims = set(lines["claim_id"].astype(str))
    header_claims = set(header["claim_id"].astype(str))
    orphan = line_claims - header_claims
    if orphan:
        raise ValueError(f"claim_line: orphan claim_id values not in header: {sorted(orphan)[:5]}...")


def validate_pharmacy(rx_header: pd.DataFrame, rx_line: pd.DataFrame) -> None:
    _require_columns(rx_header, "rx_claim_header", ["rx_claim_id", "member_id", "fill_date"])
    _require_columns(rx_line, "rx_claim_line", ["rx_claim_id", "line_number", "ndc11"])

    ndc_re = re.compile(r"^\d{11}$")
    for v in rx_line["ndc11"].astype(str).str.replace("-", "", regex=False):
        if not ndc_re.match(v):
            raise ValueError(f"rx_claim_line: invalid ndc11 (expect 11 digits): {v}")

    line_rx = set(rx_line["rx_claim_id"].astype(str))
    hdr_rx = set(rx_header["rx_claim_id"].astype(str))
    orphan = line_rx - hdr_rx
    if orphan:
        raise ValueError(f"rx_claim_line: orphan rx_claim_id not in header: {sorted(orphan)[:5]}...")


def validate_episode_catalog(
    definitions: pd.DataFrame,
    rules: pd.DataFrame,
    windows: pd.DataFrame,
) -> None:
    _require_columns(
        definitions,
        "episode_definition",
        ["episode_id", "display_name", "bundle_type", "effective_start"],
    )
    _require_columns(
        rules,
        "episode_rule",
        ["episode_id", "rule_order", "rule_role", "code_system", "match_operator"],
    )
    _require_columns(windows, "episode_rule_window", ["episode_id", "anchor_offset_days_pre", "anchor_offset_days_post"])

    for role in rules["rule_role"].unique():
        if str(role) not in ("INDEX", "INCLUSION", "EXCLUSION"):
            raise ValueError(f"episode_rule: invalid rule_role {role!r}")

    for cs in rules["code_system"].unique():
        if str(cs) not in ("ICD10", "CPT", "HCPCS", "NDC"):
            raise ValueError(f"episode_rule: invalid code_system {cs!r}")

    for _, r in rules.iterrows():
        has_set = pd.notna(r.get("code_set_id")) and str(r.get("code_set_id") or "").strip()
        has_val = pd.notna(r.get("code_value")) and str(r.get("code_value") or "").strip()
        if has_set == has_val:
            raise ValueError(
                "episode_rule: each row must have exactly one of code_set_id or code_value set "
                f"(episode_id={r.get('episode_id')}, rule_order={r.get('rule_order')})"
            )


def coerce_null_strings(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    out = df.copy()
    for c in cols:
        if c in out.columns:
            out[c] = out[c].replace("", pd.NA)
    return out
