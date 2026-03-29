# VBC Bundled Treatment Platform (open source)

Production-scaffold open-source platform for **value-based care (VBC) bundled episodes**: normalized **medical and pharmacy** claims in PostgreSQL, a **versioned episode catalog** (ICD-10 / CPT / HCPCS / NDC), **deterministic multi-episode assignment** (one claim can belong to multiple episodes), and reporting for **PMPM, risk, shared savings, and bundle spend**.

Use it to prototype bundled payment models, teach episode grouping, or fork into your own ingestion and orchestration stack.

## Features

- **Core claims model**: members, eligibility, providers, professional/facility claims (`claim_header` / `claim_line` / `diagnosis`), and **pharmacy** (`rx_claim_header` / `rx_claim_line`).
- **Episode catalog**: `episode_definition`, `episode_rule`, optional `code_set` / `code_set_member`, per-episode **anchor windows** (`episode_rule_window`).
- **Assignment engine**: builds `member_episode_instance` from **INDEX** rules, assigns claims in `[anchor − pre, anchor + post]` with optional **INCLUSION** / **EXCLUSION** rules; persists `claim_episode_assignment` with JSON **match_explanation**.
- **Synthetic + sample data**: CSV generator writes medical **and** pharmacy files; `data/sample/bundled/` ships a non-trivial multi-episode catalog (diabetes, CHF, TKA, cath lab, pharmacy carve-in).
- **CLI & orchestration hooks**: Typer CLI (`vbc-claims`), plus `scripts/pipeline_tasks.py` for Airflow/Dagster-style task wrappers.
- **Data quality**: `run_reconciliation_report()` for row counts and orphan line checks.

## Quickstart

```bash
docker compose up -d
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e ".[dev]"

vbc-claims init-db
vbc-claims generate-sample --rows 20000
vbc-claims run-pipeline --data-dir ./data/synthetic --bundled-dir ./data/sample/bundled

vbc-claims report --month 2025-12
vbc-claims report-bundles --month 2025-12
```

Or use the shell demo:

```bash
chmod +x scripts/run_bundled_pipeline.sh
./scripts/run_bundled_pipeline.sh
```

### Environment

- `DATABASE_URL` (default: `postgresql+psycopg2://vbc:vbc@localhost:5432/vbc_claims`)

### Main CLI commands

| Command | Purpose |
|--------|---------|
| `init-db` | Apply `sql/schema/postgres.sql` |
| `generate-sample` | Write synthetic CSVs (medical + pharmacy) under `data/synthetic` |
| `load-sample` | Truncate core tables and load CSVs from a directory |
| `load-medical-claims` | Load normalized medical CSVs (`--header`, `--lines`, `--diagnosis`) |
| `load-pharmacy-claims` | Load `rx_claim_header` / `rx_claim_line` CSVs |
| `load-episodes` | Load episode catalog from `data/sample/bundled` (or `--catalog-dir`) |
| `assign-episodes` | Run deterministic episode assignment |
| `run-pipeline` | Load sample + episode catalog + member-months + assign + reconciliation |
| `build-member-months` | Derive `vbc.member_month` |
| `report` | PMPM, risk, optional shared savings |
| `report-bundles` | Episode instance counts and spend rollups |

## Repository layout

- `src/vbc_claims` — Python package (ETL, episodes engine, measures, contracts, quality)
- `sql/schema` — Postgres DDL (`vbc` schema)
- `sql/queries` — Example analytic SQL
- `data/synthetic` — Default output for `generate-sample`
- `data/sample/bundled` — Episode definitions, rules, code sets (CSV)
- `docs` — Architecture, data dictionary, episode modeling
- `scripts` — Demo pipeline shell script and orchestration task stubs

## Documentation

- [docs/architecture.md](docs/architecture.md) — End-to-end design and deployment notes
- [docs/episodes.md](docs/episodes.md) — Episode rules, windows, and assignment semantics
- [docs/data_dictionary.md](docs/data_dictionary.md) — Table reference

## Integration tests

CI runs Postgres and sets `RUN_INTEGRATION=1` so the full pipeline test executes. Locally:

```bash
export RUN_INTEGRATION=1
docker compose up -d
pytest -q
```

## Data protection

All bundled sample and synthetic data are **fabricated for demonstration**. Do not commit PHI. Use your org’s secrets and access controls for production.

## License

Apache-2.0 (see `pyproject.toml`).
