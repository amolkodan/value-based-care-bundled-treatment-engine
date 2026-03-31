from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import Engine, create_engine, text

from vbc_claims.config import settings


def get_engine() -> Engine:
    return create_engine(settings.resolved_database_url(), pool_pre_ping=True)


@contextmanager
def db_connection() -> Iterator:
    engine = get_engine()
    with engine.begin() as conn:
        yield conn


def execute_sql_file(sql_file_path: str) -> None:
    with open(sql_file_path, "r", encoding="utf-8") as f:
        sql = f.read()

    # Remove line comments before statement splitting so semicolons inside comments
    # don't produce invalid pseudo-statements.
    uncommented_lines = []
    for line in sql.splitlines():
        uncommented_lines.append(line.split("--", 1)[0])
    sql_no_comments = "\n".join(uncommented_lines)

    statements = []
    for chunk in sql_no_comments.split(";"):
        stripped = chunk.strip()
        if not stripped:
            continue
        statements.append(stripped)

    with db_connection() as conn:
        for stmt in statements:
            conn.execute(text(stmt))
