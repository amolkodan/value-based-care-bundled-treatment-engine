from __future__ import annotations

from sqlalchemy import text

from vbc_claims.io.db import db_connection


def seed_example_contract(contract_id: str = "CONTRACT01", performance_year: int = 2025) -> None:
    with db_connection() as conn:
        conn.execute(
            text(
                """
                INSERT INTO vbc.contract (contract_id, contract_name, contract_type, start_date, end_date)
                VALUES (:contract_id, 'Example Shared Savings', 'shared_savings', make_date(:year, 1, 1), make_date(:year, 12, 31))
                ON CONFLICT (contract_id) DO UPDATE SET
                  contract_name = EXCLUDED.contract_name,
                  contract_type = EXCLUDED.contract_type,
                  start_date = EXCLUDED.start_date,
                  end_date = EXCLUDED.end_date
                """
            ),
            {"contract_id": contract_id, "year": performance_year},
        )

        conn.execute(
            text(
                """
                INSERT INTO vbc.contract_benchmark (
                  contract_id,
                  performance_year,
                  benchmark_pmpm,
                  min_savings_rate,
                  shared_savings_rate,
                  quality_withhold_rate
                )
                VALUES (:contract_id, :year, 450.00, 0.02, 0.50, 0.10)
                ON CONFLICT (contract_id, performance_year) DO UPDATE SET
                  benchmark_pmpm = EXCLUDED.benchmark_pmpm,
                  min_savings_rate = EXCLUDED.min_savings_rate,
                  shared_savings_rate = EXCLUDED.shared_savings_rate,
                  quality_withhold_rate = EXCLUDED.quality_withhold_rate
                """
            ),
            {"contract_id": contract_id, "year": performance_year},
        )
