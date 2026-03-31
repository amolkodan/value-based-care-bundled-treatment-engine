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

    statements = []
    for chunk in sql.split(";"):
        stripped = chunk.strip()
        if not stripped:
            continue
        # Skip comment-only fragments produced by semicolon splitting.
        non_comment_lines = [
            line for line in stripped.splitlines() if line.strip() and not line.strip().startswith("--")
        ]
        if not non_comment_lines:
            continue
        statements.append(stripped)

    with db_connection() as conn:
        for stmt in statements:
            conn.execute(text(stmt))
