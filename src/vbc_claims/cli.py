from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
import typer

from vbc_claims.analytics.reporting import build_performance_report
from vbc_claims.etl.init_db import init_db
from vbc_claims.etl.load_sample import load_synthetic_dataset
from vbc_claims.etl.seed_contract import seed_example_contract
from vbc_claims.etl.synthetic import generate_synthetic_claims_dataset
from vbc_claims.transforms.member_months import build_member_months

app = typer.Typer(add_completion=False)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


@app.command("init-db")
def init_db_command(schema_sql_path: str | None = typer.Option(None, "--schema")) -> None:
    init_db(schema_sql_path=schema_sql_path)
    typer.echo("Database schema initialized")


@app.command("generate-sample")
def generate_sample(
    output_dir: str = typer.Option(str(_repo_root() / "data" / "synthetic")),
    rows: int = typer.Option(20000),
    members: int = typer.Option(2000),
    providers: int = typer.Option(200),
) -> None:
    paths = generate_synthetic_claims_dataset(output_dir=output_dir, rows=rows, members=members, providers=providers)
    typer.echo(f"Synthetic dataset written to {paths.base_dir}")


@app.command("load-sample")
def load_sample(dataset_dir: str = typer.Option(str(_repo_root() / "data" / "synthetic"))) -> None:
    load_synthetic_dataset(dataset_dir)
    typer.echo("Synthetic dataset loaded")


@app.command("build-member-months")
def build_member_months_command(
    start_month: str = typer.Option("2025-01-01"),
    end_month: str = typer.Option("2025-12-01"),
) -> None:
    build_member_months(date.fromisoformat(start_month), date.fromisoformat(end_month))
    typer.echo("Member months built")


@app.command("seed-contract")
def seed_contract(contract_id: str = typer.Option("CONTRACT01"), year: int = typer.Option(2025)) -> None:
    seed_example_contract(contract_id=contract_id, performance_year=year)
    typer.echo("Contract and benchmark seeded")


@app.command("report")
def report(
    month: str = typer.Option("2025-12"),
    contract_id: str | None = typer.Option(None),
    output_csv: str | None = typer.Option(None),
) -> None:
    month_start = date.fromisoformat(f"{month}-01")
    month_end = (pd.Timestamp(month_start) + pd.offsets.MonthEnd(0)).date()

    report_obj = build_performance_report(month_start=month_start, month_end=month_end, contract_id=contract_id)

    typer.echo("PMPM")
    typer.echo(report_obj.pmpm.to_string(index=False))

    typer.echo("\nRisk (first 10 members)")
    typer.echo(report_obj.risk.head(10).to_string(index=False))

    if contract_id is not None and not report_obj.shared_savings.empty:
        typer.echo("\nShared savings")
        typer.echo(report_obj.shared_savings.to_string(index=False))

    if output_csv is not None:
        output_path = Path(output_csv)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        report_obj.pmpm.to_csv(output_path, index=False)
        typer.echo(f"PMPM written to {output_path}")


if __name__ == "__main__":
    app()
