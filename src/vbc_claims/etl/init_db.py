from __future__ import annotations

from pathlib import Path

from vbc_claims.io.db import execute_sql_file


def init_db(schema_sql_path: str | None = None) -> None:
    if schema_sql_path is None:
        schema_sql_path = str(Path(__file__).resolve().parents[3] / "sql" / "schema" / "postgres.sql")

    execute_sql_file(schema_sql_path)
