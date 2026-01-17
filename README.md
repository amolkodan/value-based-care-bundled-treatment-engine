# Medical Claims Analytics for Value Based Care

Starter repository for medical claims analytics in value based care. Includes a Postgres schema, synthetic sample data, Python ETL utilities, and example performance reporting for cost, utilization, quality, and shared savings.

## Quickstart

```bash
docker compose up -d
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e ".[dev]"
vbc-claims init-db
vbc-claims generate-sample --rows 20000
vbc-claims load-sample
vbc-claims report --month 2025-12
```

## Repository layout

- src/vbc_claims: Python package with ETL and reporting utilities
- sql/schema: Postgres DDL
- sql/queries: Example reporting queries
- data/synthetic: Synthetic data generator outputs
- docs: Architecture and data dictionary

## Data protection

The included dataset is synthetic and generated for demonstration. Do not commit PHI to this repository.
