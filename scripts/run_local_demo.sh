#!/usr/bin/env bash
set -euo pipefail

export PYTHONUNBUFFERED=1

if [ -f .env ]; then
  set -a
  . ./.env
  set +a
fi

vbc-claims init-db
vbc-claims generate-sample --rows 20000 --members 2000 --providers 200
vbc-claims load-sample
vbc-claims build-mm --start-month 2025-01-01 --end-month 2025-12-01
vbc-claims seed-contract --contract-id CONTRACT01 --year 2025
vbc-claims report --month 2025-12 --contract-id CONTRACT01
