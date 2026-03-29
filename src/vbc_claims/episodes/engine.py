from __future__ import annotations

import json
from datetime import date, timedelta
import pandas as pd
from sqlalchemy import text

from vbc_claims.io.db import db_connection


def clear_assignments() -> None:
    with db_connection() as conn:
        conn.execute(text("TRUNCATE TABLE vbc.claim_episode_assignment RESTART IDENTITY CASCADE"))
        conn.execute(text("TRUNCATE TABLE vbc.member_episode_instance RESTART IDENTITY CASCADE"))


def _code_matches(value: str, pattern: str, op: str) -> bool:
    v = (value or "").strip().upper().replace(".", "")
    p = (pattern or "").strip().upper().replace(".", "")
    if not v or not p:
        return False
    if op == "PREFIX":
        return v.startswith(p)
    return v == p


def _normalize_icd(s: str) -> str:
    return (s or "").strip().upper().replace(".", "")


def assign_episodes_for_all_members() -> tuple[int, int]:
    """
    Deterministic episode assignment:
    1) INDEX rules create member_episode_instance rows (anchor = claim date).
    2) Claims in [window_start, window_end] are assigned; EXCLUSION wins; INCLUSION filters if any exist.
    Returns (instance_count, assignment_count).
    """
    clear_assignments()

    with db_connection() as conn:
        rules = pd.read_sql(
            text(
                """
                SELECT r.rule_id, r.episode_id, r.rule_order, r.rule_role, r.code_system,
                       r.code_set_id, r.code_value, r.match_operator, r.rule_weight, r.specificity_score
                FROM vbc.episode_rule r
                ORDER BY r.episode_id, r.rule_order, r.rule_id
                """
            ),
            conn,
        )
        windows = pd.read_sql(
            text(
                """
                SELECT episode_id, anchor_offset_days_pre, anchor_offset_days_post
                FROM vbc.episode_rule_window
                """
            ),
            conn,
        )
        code_set_members = pd.read_sql(
            text(
                """
                SELECT code_set_id, UPPER(REPLACE(code_value, '.', '')) AS code_norm, code_value
                FROM vbc.code_set_member
                """
            ),
            conn,
        )

        headers = pd.read_sql(
            text(
                """
                SELECT claim_id, member_id, service_start, service_end, primary_dx, admitting_dx
                FROM vbc.claim_header
                """
            ),
            conn,
        )
        dx = pd.read_sql(
            text(
                """
                SELECT claim_id, UPPER(REPLACE(icd10_dx, '.', '')) AS icd_norm, icd10_dx
                FROM vbc.diagnosis
                """
            ),
            conn,
        )
        lines = pd.read_sql(
            text(
                """
                SELECT claim_id, UPPER(TRIM(hcpcs)) AS hcpcs_norm, hcpcs
                FROM vbc.claim_line
                WHERE hcpcs IS NOT NULL AND TRIM(hcpcs) <> ''
                """
            ),
            conn,
        )
        rx_headers = pd.read_sql(
            text(
                """
                SELECT rx_claim_id, member_id, fill_date
                FROM vbc.rx_claim_header
                """
            ),
            conn,
        )
        rx_lines = pd.read_sql(
            text(
                """
                SELECT rx_line_id, rx_claim_id, UPPER(REPLACE(ndc11, '-', '')) AS ndc_norm, ndc11
                FROM vbc.rx_claim_line
                """
            ),
            conn,
        )

    if rules.empty:
        return (0, 0)

    # Expand rules with code_set_id into virtual rows (code_value list)
    expanded_rules: list[dict[str, object]] = []
    for _, row in rules.iterrows():
        rid = int(row["rule_id"])
        eid = str(row["episode_id"])
        rorder = int(row["rule_order"])
        role = str(row["rule_role"])
        csys = str(row["code_system"])
        op = str(row["match_operator"] or "EQUALS")
        cset = row["code_set_id"]
        cval = row["code_value"]
        if pd.notna(cset) and str(cset):
            members = code_set_members[code_set_members["code_set_id"] == str(cset)]
            if members.empty:
                continue
            for _, m in members.iterrows():
                expanded_rules.append(
                    {
                        "rule_id": rid,
                        "episode_id": eid,
                        "rule_order": rorder,
                        "rule_role": role,
                        "code_system": csys,
                        "code_value": str(m["code_value"]),
                        "match_operator": op,
                        "rule_weight": float(row.get("rule_weight") or 1.0),
                        "specificity_score": float(row.get("specificity_score") or 1.0),
                    }
                )
        elif pd.notna(cval) and str(cval):
            expanded_rules.append(
                {
                    "rule_id": rid,
                    "episode_id": eid,
                    "rule_order": rorder,
                    "rule_role": role,
                    "code_system": csys,
                    "code_value": str(cval),
                    "match_operator": op,
                    "rule_weight": float(row.get("rule_weight") or 1.0),
                    "specificity_score": float(row.get("specificity_score") or 1.0),
                }
            )

    rules_df = pd.DataFrame(expanded_rules)
    if rules_df.empty:
        return (0, 0)

    def window_for(episode_id: str) -> tuple[int, int]:
        w = windows[windows["episode_id"] == episode_id]
        if w.empty:
            return (0, 90)
        return (int(w.iloc[0]["anchor_offset_days_pre"]), int(w.iloc[0]["anchor_offset_days_post"]))

    # Build claim -> codes maps
    icd_by_claim: dict[str, set[str]] = {}
    for _, r in dx.iterrows():
        cid = str(r["claim_id"])
        icd_by_claim.setdefault(cid, set()).add(str(r["icd_norm"]))

    for _, r in headers.iterrows():
        cid = str(r["claim_id"])
        for col in ("primary_dx", "admitting_dx"):
            if pd.notna(r.get(col)) and str(r[col]).strip():
                icd_by_claim.setdefault(cid, set()).add(_normalize_icd(str(r[col])))

    hcpcs_by_claim: dict[str, set[str]] = {}
    for _, r in lines.iterrows():
        cid = str(r["claim_id"])
        hcpcs_by_claim.setdefault(cid, set()).add(str(r["hcpcs_norm"]))

    ndc_by_rx_line: dict[int, str] = {}
    rx_line_to_claim: dict[int, str] = {}
    for _, r in rx_lines.iterrows():
        lid = int(r["rx_line_id"])
        ndc_by_rx_line[lid] = str(r["ndc_norm"])
        rx_line_to_claim[lid] = str(r["rx_claim_id"])

    rx_claim_fill: dict[str, date] = {}
    rx_claim_member: dict[str, str] = {}
    for _, r in rx_headers.iterrows():
        rcid = str(r["rx_claim_id"])
        rx_claim_fill[rcid] = pd.Timestamp(r["fill_date"]).date()
        rx_claim_member[rcid] = str(r["member_id"])

    def medical_claim_matches_rule(claim_id: str, code_system: str, code_value: str, match_op: str) -> bool:
        if code_system == "ICD10":
            codes = icd_by_claim.get(claim_id, set())
            return any(_code_matches(c, code_value, match_op) for c in codes)
        if code_system in ("CPT", "HCPCS"):
            codes = hcpcs_by_claim.get(claim_id, set())
            return any(_code_matches(c, code_value, match_op) for c in codes)
        return False

    def rx_line_matches_rule(rx_line_id: int, code_system: str, code_value: str, match_op: str) -> bool:
        if code_system != "NDC":
            return False
        ndc = ndc_by_rx_line.get(rx_line_id, "")
        return _code_matches(ndc, code_value.replace("-", ""), match_op)

    instances: list[dict[str, object]] = []

    for eid in rules_df["episode_id"].unique():
        sub = rules_df[rules_df["episode_id"] == eid]
        index_rules = sub[sub["rule_role"] == "INDEX"]
        if index_rules.empty:
            continue
        pre_d, post_d = window_for(str(eid))

        # Medical index events
        for _, h in headers.iterrows():
            claim_id = str(h["claim_id"])
            member_id = str(h["member_id"])
            svc = pd.Timestamp(h["service_start"]).date()
            for _, rr in index_rules.iterrows():
                csys = str(rr["code_system"])
                if csys == "NDC":
                    continue
                if medical_claim_matches_rule(claim_id, csys, str(rr["code_value"]), str(rr["match_operator"])):
                    anchor = svc
                    instances.append(
                        {
                            "episode_id": str(eid),
                            "member_id": member_id,
                            "anchor_date": anchor,
                            "window_start": anchor - timedelta(days=pre_d),
                            "window_end": anchor + timedelta(days=post_d),
                            "anchor_medical_claim_id": claim_id,
                            "anchor_rx_claim_id": None,
                            "anchor_rule_id": int(rr["rule_id"]),
                        }
                    )

        # Pharmacy index events
        for _, rl in rx_lines.iterrows():
            rx_line_id = int(rl["rx_line_id"])
            rx_cid = str(rl["rx_claim_id"])
            member_id = rx_claim_member.get(rx_cid, "")
            fill_d = rx_claim_fill.get(rx_cid)
            if fill_d is None:
                continue
            for _, rr in index_rules.iterrows():
                if str(rr["code_system"]) != "NDC":
                    continue
                if rx_line_matches_rule(rx_line_id, "NDC", str(rr["code_value"]), str(rr["match_operator"])):
                    instances.append(
                        {
                            "episode_id": str(eid),
                            "member_id": member_id,
                            "anchor_date": fill_d,
                            "window_start": fill_d - timedelta(days=pre_d),
                            "window_end": fill_d + timedelta(days=post_d),
                            "anchor_medical_claim_id": None,
                            "anchor_rx_claim_id": rx_cid,
                            "anchor_rule_id": int(rr["rule_id"]),
                        }
                    )

    if not instances:
        return (0, 0)

    inst_df = pd.DataFrame(instances)
    # Dedupe episode + member + anchor_date (deterministic: first row wins)
    inst_df = inst_df.drop_duplicates(subset=["episode_id", "member_id", "anchor_date"], keep="first")
    inst_df["anchor_rule_id"] = inst_df["anchor_rule_id"].astype("Int64")

    inst_df = inst_df[
        [
            "episode_id",
            "member_id",
            "anchor_date",
            "window_start",
            "window_end",
            "anchor_medical_claim_id",
            "anchor_rx_claim_id",
            "anchor_rule_id",
        ]
    ]

    with db_connection() as conn:
        inst_df.to_sql(
            "member_episode_instance",
            conn,
            schema="vbc",
            if_exists="append",
            index=False,
            method="multi",
            chunksize=1000,
        )

        inst_loaded = pd.read_sql(
            text(
                """
                SELECT instance_id, episode_id, member_id, window_start, window_end
                FROM vbc.member_episode_instance
                """
            ),
            conn,
        )

    instance_count = len(inst_loaded)

    def rules_for_episode_role(eid: str, role: str) -> pd.DataFrame:
        return rules_df[(rules_df["episode_id"] == eid) & (rules_df["rule_role"] == role)]

    assignments: list[dict[str, object]] = []

    def _score_rule(rr: pd.Series) -> float:
        # Higher specificity and explicit weight increase contribution, lower rule_order preferred.
        order_penalty = 1.0 / max(1.0, float(rr["rule_order"]))
        return float(rr.get("rule_weight") or 1.0) * float(rr.get("specificity_score") or 1.0) * (1.0 + order_penalty)

    for _, ins in inst_loaded.iterrows():
        iid = int(ins["instance_id"])
        eid = str(ins["episode_id"])
        mid = str(ins["member_id"])
        w0 = pd.Timestamp(ins["window_start"]).date()
        w1 = pd.Timestamp(ins["window_end"]).date()

        incl = rules_for_episode_role(eid, "INCLUSION")
        excl = rules_for_episode_role(eid, "EXCLUSION")
        has_inclusion = not incl.empty

        # Medical claims in window
        for _, h in headers.iterrows():
            if str(h["member_id"]) != mid:
                continue
            claim_id = str(h["claim_id"])
            svc = pd.Timestamp(h["service_start"]).date()
            if svc < w0 or svc > w1:
                continue

            excluded = False
            for _, rr in excl.iterrows():
                csys = str(rr["code_system"])
                if csys == "NDC":
                    continue
                if medical_claim_matches_rule(claim_id, csys, str(rr["code_value"]), str(rr["match_operator"])):
                    excluded = True
                    break
            if excluded:
                continue

            med_best_rule_id: int | None = None
            med_best_weight = 1.0
            if has_inclusion:
                matched = False
                best_order = 999999
                best_rule: int | None = None
                best_score = -1.0
                for _, rr in incl.iterrows():
                    csys = str(rr["code_system"])
                    if csys == "NDC":
                        continue
                    if medical_claim_matches_rule(claim_id, csys, str(rr["code_value"]), str(rr["match_operator"])):
                        matched = True
                        ro = int(rr["rule_order"])
                        sc = _score_rule(rr)
                        if ro < best_order:
                            best_order = ro
                            best_rule = int(rr["rule_id"])
                        if sc > best_score:
                            best_score = sc
                if not matched:
                    continue
                med_best_rule_id = best_rule
                med_best_weight = max(0.000001, best_score)
                expl = json.dumps(
                    {"type": "inclusion", "rule_id": best_rule, "rule_order": best_order, "weighted": True},
                    sort_keys=True,
                )
            else:
                # No inclusion: claims in window are eligible. Use deterministic baseline weight.
                med_best_weight = 1.0
                expl = json.dumps({"type": "window_only", "weighted": True}, sort_keys=True)

            assignments.append(
                {
                    "instance_id": iid,
                    "claim_source": "medical",
                    "medical_claim_id": claim_id,
                    "rx_line_id": None,
                    "rule_priority": 0,
                    "matched_rule_id": med_best_rule_id,
                    "allocation_weight": med_best_weight,
                    "match_explanation": expl,
                }
            )

        # Pharmacy lines in window
        for _, rl in rx_lines.iterrows():
            lid = int(rl["rx_line_id"])
            rx_cid = str(rl["rx_claim_id"])
            if rx_claim_member.get(rx_cid) != mid:
                continue
            fill_d = rx_claim_fill.get(rx_cid)
            if fill_d is None or fill_d < w0 or fill_d > w1:
                continue

            excluded = False
            for _, rr in excl.iterrows():
                if str(rr["code_system"]) != "NDC":
                    continue
                if rx_line_matches_rule(lid, "NDC", str(rr["code_value"]), str(rr["match_operator"])):
                    excluded = True
                    break
            if excluded:
                continue

            best_rule_id: int | None = None
            best_weight = 1.0
            if has_inclusion:
                matched_rx = False
                rx_best_order = 999999
                rx_best_rule: int | None = None
                rx_best_score = -1.0
                for _, rr in incl.iterrows():
                    if str(rr["code_system"]) != "NDC":
                        continue
                    if rx_line_matches_rule(lid, "NDC", str(rr["code_value"]), str(rr["match_operator"])):
                        matched_rx = True
                        ro = int(rr["rule_order"])
                        sc = _score_rule(rr)
                        if ro < rx_best_order:
                            rx_best_order = ro
                            rx_best_rule = int(rr["rule_id"])
                        if sc > rx_best_score:
                            rx_best_score = sc
                if not matched_rx:
                    continue
                best_rule_id = rx_best_rule
                best_weight = max(0.000001, rx_best_score)
                expl = json.dumps(
                    {"type": "inclusion", "rule_id": rx_best_rule, "rule_order": rx_best_order, "weighted": True},
                    sort_keys=True,
                )
            else:
                best_weight = 1.0
                expl = json.dumps({"type": "window_only", "weighted": True}, sort_keys=True)

            assignments.append(
                {
                    "instance_id": iid,
                    "claim_source": "pharmacy",
                    "medical_claim_id": None,
                    "rx_line_id": lid,
                    "rule_priority": 0,
                    "matched_rule_id": best_rule_id,
                    "allocation_weight": best_weight,
                    "match_explanation": expl,
                }
            )

    if not assignments:
        return (instance_count, 0)

    asg_df = pd.DataFrame(assignments)
    asg_df["rx_line_id"] = asg_df["rx_line_id"].astype("Int64")
    asg_df["medical_claim_id"] = asg_df["medical_claim_id"].astype("string")
    asg_med = asg_df[asg_df["claim_source"] == "medical"].drop_duplicates(subset=["instance_id", "medical_claim_id"])
    asg_rx = asg_df[asg_df["claim_source"] == "pharmacy"].drop_duplicates(subset=["instance_id", "rx_line_id"])
    asg_parts = [df for df in (asg_med, asg_rx) if not df.empty]
    asg_df = pd.concat(asg_parts, ignore_index=True) if asg_parts else pd.DataFrame()

    if asg_df.empty:
        return (instance_count, 0)

    with db_connection() as conn:
        run_row = conn.execute(
            text(
                """
                INSERT INTO vbc.allocation_run (strategy_name, strategy_version, note)
                VALUES ('weighted_rules', '1.0', 'Deterministic weighted split by matched rules')
                RETURNING allocation_run_id
                """
            )
        ).fetchone()
    allocation_run_id = int(run_row[0]) if run_row else 0

    # Compute normalized allocation percentages per source claim and assign allocated amounts.
    with db_connection() as conn:
        med_amt_all = pd.read_sql(
            text(
                """
                SELECT ch.claim_id AS medical_claim_id,
                       SUM(cl.allowed_amount) AS allowed_amount,
                       SUM(cl.paid_amount) AS paid_amount
                FROM vbc.claim_header ch
                JOIN vbc.claim_line cl ON cl.claim_id = ch.claim_id
                GROUP BY ch.claim_id
                """
            ),
            conn,
        )
        rx_amt_all = pd.read_sql(
            text(
                """
                SELECT rl.rx_line_id, rl.allowed_amount, rl.paid_amount
                FROM vbc.rx_claim_line rl
                """
            ),
            conn,
        )

    med_amt = (
        pd.merge(
            asg_df[asg_df["claim_source"] == "medical"][["medical_claim_id"]].drop_duplicates(),
            med_amt_all,
            on="medical_claim_id",
            how="left",
        )
        if not asg_df[asg_df["claim_source"] == "medical"].empty
        else pd.DataFrame(columns=["medical_claim_id", "allowed_amount", "paid_amount"])
    )
    rx_amt = (
        pd.merge(
            asg_df[asg_df["claim_source"] == "pharmacy"][["rx_line_id"]].drop_duplicates(),
            rx_amt_all,
            on="rx_line_id",
            how="left",
        )
        if not asg_df[asg_df["claim_source"] == "pharmacy"].empty
        else pd.DataFrame(columns=["rx_line_id", "allowed_amount", "paid_amount"])
    )

    asg_df["allocation_weight"] = asg_df["allocation_weight"].astype(float)
    asg_df["allocation_run_id"] = allocation_run_id
    asg_df["claim_key"] = asg_df.apply(
        lambda r: f"medical::{r['medical_claim_id']}" if r["claim_source"] == "medical" else f"pharmacy::{int(r['rx_line_id'])}",
        axis=1,
    )
    weight_sum = asg_df.groupby("claim_key")["allocation_weight"].transform("sum")
    asg_df["allocation_pct"] = asg_df["allocation_weight"] / weight_sum.replace({0: 1.0})

    med_map: dict[str, tuple[float, float]] = {}
    if not med_amt.empty:
        med_map = {
            str(r["medical_claim_id"]): (float(r["allowed_amount"] or 0.0), float(r["paid_amount"] or 0.0))
            for _, r in med_amt.iterrows()
        }
    rx_map: dict[int, tuple[float, float]] = {}
    if not rx_amt.empty:
        rx_map = {
            int(r["rx_line_id"]): (float(r["allowed_amount"] or 0.0), float(r["paid_amount"] or 0.0))
            for _, r in rx_amt.iterrows()
        }

    def _alloc_allowed(row: pd.Series) -> float:
        if row["claim_source"] == "medical":
            base = med_map.get(str(row["medical_claim_id"]), (0.0, 0.0))[0]
        else:
            base = rx_map.get(int(row["rx_line_id"]), (0.0, 0.0))[0]
        return round(base * float(row["allocation_pct"]), 2)

    def _alloc_paid(row: pd.Series) -> float:
        if row["claim_source"] == "medical":
            base = med_map.get(str(row["medical_claim_id"]), (0.0, 0.0))[1]
        else:
            base = rx_map.get(int(row["rx_line_id"]), (0.0, 0.0))[1]
        return round(base * float(row["allocation_pct"]), 2)

    asg_df["allocated_allowed_amount"] = asg_df.apply(_alloc_allowed, axis=1)
    asg_df["allocated_paid_amount"] = asg_df.apply(_alloc_paid, axis=1)
    asg_df = asg_df.drop(columns=["claim_key"])

    with db_connection() as conn:
        asg_df.to_sql(
            "claim_episode_assignment",
            conn,
            schema="vbc",
            if_exists="append",
            index=False,
            method="multi",
            chunksize=5000,
        )
        conn.execute(
            text(
                """
                UPDATE vbc.allocation_run
                SET completed_at = NOW()
                WHERE allocation_run_id = :rid
                """
            ),
            {"rid": allocation_run_id},
        )

    assignment_count = len(asg_df)
    return (instance_count, assignment_count)


def episode_summary_by_episode() -> pd.DataFrame:
    sql = text(
        """
        SELECT
          e.episode_id,
          e.display_name,
          COUNT(DISTINCT i.instance_id) AS episode_instances,
          COUNT(DISTINCT a.assignment_id) AS claim_assignments
        FROM vbc.episode_definition e
        LEFT JOIN vbc.member_episode_instance i ON i.episode_id = e.episode_id
        LEFT JOIN vbc.claim_episode_assignment a ON a.instance_id = i.instance_id
        GROUP BY e.episode_id, e.display_name
        ORDER BY e.episode_id
        """
    )
    with db_connection() as conn:
        return pd.read_sql(sql, conn)
