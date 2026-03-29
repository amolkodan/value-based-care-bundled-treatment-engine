from __future__ import annotations

from pathlib import Path

import pandas as pd
from sqlalchemy import text

from vbc_claims.etl.validate import coerce_null_strings, validate_episode_catalog
from vbc_claims.io.db import db_connection


def _append_df(df: pd.DataFrame, table: str) -> None:
    with db_connection() as conn:
        df.to_sql(table, conn, schema="vbc", if_exists="append", index=False, method="multi", chunksize=2000)


def load_episode_catalog(
    definitions_csv: str,
    rules_csv: str,
    windows_csv: str,
    code_set_csv: str | None = None,
    code_set_member_csv: str | None = None,
    truncate: bool = False,
) -> None:
    definitions = pd.read_csv(definitions_csv)
    rules = pd.read_csv(rules_csv)
    windows = pd.read_csv(windows_csv)
    rules = coerce_null_strings(rules, ["code_set_id", "code_value"])

    validate_episode_catalog(definitions, rules, windows)

    rule_eps = set(rules["episode_id"].astype(str))
    win_eps = set(windows["episode_id"].astype(str))
    missing = rule_eps - win_eps
    if missing:
        extra = pd.DataFrame(
            [{"episode_id": eid, "anchor_offset_days_pre": 0, "anchor_offset_days_post": 90} for eid in sorted(missing)]
        )
        windows = pd.concat([windows, extra], ignore_index=True)

    with db_connection() as conn:
        if truncate:
            conn.execute(
                text(
                    """
                    TRUNCATE TABLE vbc.claim_episode_assignment,
                    vbc.member_episode_instance,
                    vbc.episode_rule_window,
                    vbc.episode_rule,
                    vbc.episode_definition,
                    vbc.code_set_member,
                    vbc.code_set
                    RESTART IDENTITY CASCADE
                    """
                )
            )

    if code_set_csv and Path(code_set_csv).exists():
        cs = pd.read_csv(code_set_csv)
        csm = pd.read_csv(code_set_member_csv or str(Path(code_set_csv).parent / "code_set_member.csv"))
        _append_df(cs, "code_set")
        _append_df(csm, "code_set_member")

    _append_df(definitions, "episode_definition")
    # Omit rule_id so serial applies
    rule_cols = [
        "episode_id",
        "rule_order",
        "rule_role",
        "code_system",
        "code_set_id",
        "code_value",
        "match_operator",
    ]
    for c in rule_cols:
        if c not in rules.columns:
            if c == "match_operator":
                rules[c] = "EQUALS"
            elif c in ("code_set_id", "code_value"):
                rules[c] = pd.NA
            else:
                raise ValueError(f"episode_rule missing column {c}")
    _append_df(rules[rule_cols], "episode_rule")
    _append_df(windows, "episode_rule_window")


def load_episodes_from_dir(catalog_dir: str, truncate: bool = True) -> None:
    base = Path(catalog_dir)
    load_episode_catalog(
        str(base / "episode_definition.csv"),
        str(base / "episode_rule.csv"),
        str(base / "episode_rule_window.csv"),
        code_set_csv=str(base / "code_set.csv") if (base / "code_set.csv").exists() else None,
        code_set_member_csv=str(base / "code_set_member.csv") if (base / "code_set_member.csv").exists() else None,
        truncate=truncate,
    )
