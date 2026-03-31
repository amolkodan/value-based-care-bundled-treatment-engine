#!/usr/bin/env sh
set -eu

cmd="${1:-api}"

if [ "${MIGRATE_ON_STARTUP:-false}" = "true" ]; then
  echo "Running DB init migration..."
  python -m vbc_claims.cli init-db
fi

if [ "$cmd" = "api" ]; then
  exec vbc-claims-api
fi

exec "$@"

