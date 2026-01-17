# Architecture

## Objectives

- Standardize medical claims data into a consistent analytic model
- Support attribution and contract configuration for multiple value based care programs
- Produce reproducible performance reporting with audit friendly lineage

## Reference workflow

1. Land raw eligibility, provider, and claims extracts in a file store
2. Load standardized tables in Postgres schema vbc
3. Generate member months and attribution spans
4. Run reporting jobs for cost, utilization, quality, risk, and contract performance

## Modules

- vbc_claims.io: database and file I O utilities
- vbc_claims.etl: loaders and validators
- vbc_claims.transforms: normalization and derived tables
- vbc_claims.measures: quality and utilization measures
- vbc_claims.contracts: benchmark and shared savings calculations

## Deployment notes

This starter repository uses Postgres for demonstration. In production, typical patterns include:

- A lakehouse for raw storage
- A warehouse for curated star schema
- Orchestration with Airflow, Dagster, or Prefect
- Observability with data quality checks, row count and cost drift, and contract reconciliation
