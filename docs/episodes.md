# Episode catalog and assignment

This platform implements a **deterministic, explainable** episode grouper suitable for **bundled payment prototypes** and education. It is not a certified grouper for any specific payer program; extend the catalog and rules for your contracts.

## Tables

| Table | Role |
|-------|------|
| `vbc.episode_definition` | Episode metadata: id, clinical domain, bundle type, effective dates |
| `vbc.episode_rule` | Rules with `rule_role` **INDEX**, **INCLUSION**, or **EXCLUSION**, `code_system` ICD10 / CPT / HCPCS / NDC, and weighting (`rule_weight`, `specificity_score`) |
| `vbc.code_set` / `vbc.code_set_member` | Reusable code lists referenced by `episode_rule.code_set_id` |
| `vbc.episode_rule_window` | Per-episode `anchor_offset_days_pre` / `anchor_offset_days_post` (defaults to 0 / 90 if omitted at load time) |
| `vbc.member_episode_instance` | One row per (`episode_id`, `member_id`, `anchor_date`) after INDEX detection |
| `vbc.claim_episode_assignment` | Many-to-many link from medical claim or pharmacy line to an instance, including `allocation_pct` and allocated amounts |

## Rule semantics

1. **INDEX** rules identify **anchor events** on a claim:
   - Medical: ICD-10 from `diagnosis` plus `primary_dx` / `admitting_dx` on `claim_header`; CPT/HCPCS from `claim_line.hcpcs`.
   - Pharmacy: NDC on `rx_claim_line` with fill date from `rx_claim_header.fill_date`.
2. For each anchor, an instance is created with `window_start = anchor_date − pre` and `window_end = anchor_date + post`.
3. **Assignment** scans all medical claims and pharmacy lines for that member whose service/fill date falls in the window.
4. **EXCLUSION**: if the claim matches any exclusion rule for that episode, it is **not** assigned.
5. **INCLUSION**: if the episode has **any** inclusion rules, the claim must match **at least one** inclusion rule (by code system). If there are **no** inclusion rules, **all** claims in the window are eligible (after exclusions).
6. **Multi-episode**: the same claim line can appear in multiple `claim_episode_assignment` rows for different `instance_id` values.
7. **Weighted split**: overlapping claim matches are split across bundles by normalized weight:
   - Base score uses `rule_weight * specificity_score * (1 + 1/rule_order)`.
   - For each unique claim-source claim, scores are normalized to `allocation_pct` that sums to 1.
   - Allocated financial fields are persisted (`allocated_allowed_amount`, `allocated_paid_amount`).

`match_explanation` stores JSON such as `{"type": "window_only"}` or inclusion metadata.

## Authoring catalogs

Ship CSVs under `data/sample/bundled/`:

- `episode_definition.csv`
- `episode_rule.csv` — exactly one of `code_set_id` or `code_value` per row, optional `rule_weight`, `specificity_score`
- `episode_rule_window.csv`
- Optional `code_set.csv`, `code_set_member.csv`

Load with `vbc-claims load-episodes --catalog-dir ...`.

## Orchestration

Use `scripts/pipeline_tasks.py` as thin wrappers for schedulers (Airflow, Dagster, Prefect). Pair with `run_reconciliation_report()` after assignment for row-count and orphan checks.
