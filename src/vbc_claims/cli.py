from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
import typer

from vbc_claims.analytics.reporting import build_bundle_episode_report, build_performance_report
from vbc_claims.episodes.engine import assign_episodes_for_all_members
from vbc_claims.etl.init_db import init_db
from vbc_claims.etl.load_episodes import load_episodes_from_dir
from vbc_claims.etl.load_normalized import (
    load_normalized_medical_claims,
    load_normalized_pharmacy_claims,
)
from vbc_claims.etl.load_sample import load_synthetic_dataset
from vbc_claims.etl.pipeline import run_full_pipeline
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
    typer.echo("Synthetic dataset loaded (medical and pharmacy when CSVs exist)")


@app.command("load-medical-claims")
def load_medical_claims(
    header: str = typer.Option(..., "--header", help="claim_header.csv path"),
    lines: str = typer.Option(..., "--lines", help="claim_line.csv path"),
    diagnosis: str = typer.Option(..., "--diagnosis", help="diagnosis.csv path"),
    truncate: bool = typer.Option(False, "--truncate", help="Truncate medical claim tables before load"),
) -> None:
    n = load_normalized_medical_claims(header, lines, diagnosis, truncate=truncate)
    typer.echo(f"Loaded {n} medical claim headers")


@app.command("load-pharmacy-claims")
def load_pharmacy_claims(
    header: str = typer.Option(..., "--header", help="rx_claim_header.csv path"),
    lines: str = typer.Option(..., "--lines", help="rx_claim_line.csv path"),
    truncate: bool = typer.Option(False, "--truncate", help="Truncate pharmacy tables before load"),
) -> None:
    n = load_normalized_pharmacy_claims(header, lines, truncate=truncate)
    typer.echo(f"Loaded {n} pharmacy claim headers")


@app.command("load-episodes")
def load_episodes(
    catalog_dir: str = typer.Option(
        str(_repo_root() / "data" / "sample" / "bundled"),
        "--catalog-dir",
        help="Directory with episode_definition.csv, episode_rule.csv, episode_rule_window.csv",
    ),
    truncate: bool = typer.Option(True, "--truncate/--no-truncate"),
) -> None:
    load_episodes_from_dir(catalog_dir, truncate=truncate)
    typer.echo(f"Episode catalog loaded from {catalog_dir}")


@app.command("assign-episodes")
def assign_episodes() -> None:
    inst_n, asg_n = assign_episodes_for_all_members()
    typer.echo(f"Episode instances: {inst_n}; claim assignments: {asg_n}")


@app.command("run-pipeline")
def run_pipeline(
    data_dir: str = typer.Option(str(_repo_root() / "data" / "synthetic")),
    bundled_dir: str = typer.Option(str(_repo_root() / "data" / "sample" / "bundled")),
    skip_load: bool = typer.Option(False, "--skip-load", help="Skip synthetic CSV load (use DB as-is)"),
) -> None:
    result = run_full_pipeline(
        data_dir=data_dir,
        bundled_catalog_dir=bundled_dir,
        skip_synthetic_load=skip_load,
    )
    typer.echo(str(result))


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


@app.command("report-bundles")
def report_bundles(month: str = typer.Option("2025-12")) -> None:
    month_start = date.fromisoformat(f"{month}-01")
    month_end = (pd.Timestamp(month_start) + pd.offsets.MonthEnd(0)).date()
    rep = build_bundle_episode_report(month_start=month_start, month_end=month_end)
    typer.echo("Episode catalog summary")
    typer.echo(rep.episode_catalog_summary.to_string(index=False))
    typer.echo("\nEpisode spend in period (assigned claims)")
    typer.echo(rep.episode_spend.to_string(index=False))


if __name__ == "__main__":
    app()
