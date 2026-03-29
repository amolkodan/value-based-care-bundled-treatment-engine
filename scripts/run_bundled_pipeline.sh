#!/usr/bin/env bash
# Local demo: Postgres must be running (see docker-compose.yml).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
export DATABASE_URL="${DATABASE_URL:-postgresql+psycopg2://vbc:vbc@localhost:5432/vbc_claims}"

python -m vbc_claims.cli init-db
python -m vbc_claims.cli generate-sample --rows 5000 --members 500 --providers 80
python -m vbc_claims.cli run-pipeline --data-dir "$ROOT/data/synthetic" --bundled-dir "$ROOT/data/sample/bundled"
python -m vbc_claims.cli report-bundles --month 2025-12
python -m vbc_claims.cli report --month 2025-12
