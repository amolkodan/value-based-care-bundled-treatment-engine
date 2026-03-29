# VBC Bundled Treatment Platform (Open Source)

Open-source technical foundation for building **Value-Based Care (VBC)** bundled payment engines using normalized **medical claims** and **pharmacy claims**. The platform includes a versioned **Bundled Treatment Package ** catalog, deterministic and explainable package assignment, weighted overlap allocation (one claim split across multiple packages), API/CLI execution paths, and analytics outputs suitable for contracting, actuarial review, and care management operations.

This repository is designed as a serious starter for organizations implementing bundled treatment package payment models (for example, BPCI-like bundles, specialty package programs, payer-provider risk arrangements, and internal cost-accounting bundles).

## Clinical and Business Context

In bundled payment models, a clinically-related set of services across a pre-defined care window (for example, index hospitalization + post-acute follow-up) is grouped into a **Bundled Treatment Package **. Financial accountability requires:

- A robust mapping between raw claim activity and bundled treatment package definitions.
- Support for medical and pharmacy cost integration.
- Explainable assignment and adjudication logic.
- Allocation policy when a single claim is relevant to multiple conditions/bundles.

This platform provides those core technical primitives while remaining implementation-neutral so payers, providers, MSOs, ACOs, TPAs, and analytics vendors can adapt it to local policy.

## Core Capabilities

- **Normalized claims domain model**
  - Eligibility, members, providers, medical headers/lines/diagnoses, and pharmacy fills.
  - SQL schema in `vbc` namespace for reproducible local/CI deployment.
- **Bundled Treatment Package catalog model**
  - Package metadata, rule catalog, code sets, and temporal windows.
  - Supports ICD-10-CM/PCS context (diagnosis matching), CPT/HCPCS (professional/facility procedures), and NDC (drug exposures).
- **Deterministic assignment engine**
  - `INDEX` rules create anchor events.
  - `INCLUSION`/`EXCLUSION` rules refine assignment.
  - Multi-package membership is native.
- **Weighted overlap allocation**
  - Claim overlap is split across matched bundles using rule-derived scoring.
  - Stores `allocation_weight`, `allocation_pct`, and allocated dollar fields per assignment.
- **Reporting and quality**
  - PMPM and risk outputs preserved.
  - Bundle reporting includes gross vs allocated spend and overlap diagnostics.
  - Reconciliation checks for operational monitoring.
- **Execution surfaces**
  - CLI orchestration for local runs.
  - FastAPI service endpoints for integration into enterprise systems.

## Reference Architecture

```mermaid
flowchart LR
  rawMed[RawMedicalClaims] --> normIngest[NormalizedIngestion]
  rawRx[RawPharmacyClaims] --> normIngest
  normIngest --> pg[(Postgres_vbc)]
  catalog[BundledTreatmentPackageCatalogAndCodeSets] --> pg
  pg --> assigner[DeterministicPackageAssigner]
  assigner --> overlap[WeightedOverlapAllocator]
  overlap --> assignTbl[claim_episode_assignment]
  assignTbl --> reports[BundleAndFinanceReports]
  assignTbl --> api[FastAPIService]
```

## Data Model Highlights

Primary tables (see also `docs/data_dictionary.md`):

- **Medical claims**
  - `vbc.claim_header`, `vbc.claim_line`, `vbc.diagnosis`
- **Pharmacy claims**
  - `vbc.rx_claim_header`, `vbc.rx_claim_line`
- **Bundled treatment package catalog (internal table names keep `episode_*`)**
  - `vbc.episode_definition`
  - `vbc.episode_rule` (`rule_role`, `code_system`, `match_operator`, `rule_weight`, `specificity_score`)
  - `vbc.episode_rule_window`
  - `vbc.code_set`, `vbc.code_set_member`
- **Assignment outputs**
  - `vbc.member_episode_instance`
  - `vbc.claim_episode_assignment`
  - `vbc.allocation_run`

### Weighted Split Logic (Technical)

When a claim matches multiple bundled treatment package instances, the engine computes a per-match score:

`score = rule_weight * specificity_score * (1 + 1/rule_order)`

Then for each unique claim key (`medical_claim_id` or `rx_line_id`):

`allocation_pct_i = score_i / sum(score_all_matches_for_claim)`

Allocated amounts are persisted:

- `allocated_allowed_amount = base_allowed * allocation_pct`
- `allocated_paid_amount = base_paid * allocation_pct`

This produces deterministic, auditable, and financially reconcilable overlap handling.

## Quickstart (Local)

```bash
docker compose up -d
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e ".[dev]"

# Initialize schema
vbc-claims init-db

# Generate synthetic normalized medical+pharmacy sample files
vbc-claims generate-sample --rows 20000

# End-to-end pipeline: load claims + load bundled treatment package catalog + build member months + assign packages + reconciliation
vbc-claims run-pipeline --data-dir ./data/synthetic --bundled-dir ./data/sample/bundled

# Operational outputs
vbc-claims report --month 2025-12
vbc-claims report-bundles --month 2025-12
```

Alternative:

```bash
chmod +x scripts/run_bundled_pipeline.sh
./scripts/run_bundled_pipeline.sh
```

## API Service

Start service:

```bash
vbc-claims-api
```

Or via compose (`api` service included in `docker-compose.yml`).

Key endpoints:

- `GET /health`
- `GET /episodes/catalog`
- `POST /episodes/assign/run`
- `GET /episodes/assignments`
- `GET /reports/bundles?month=YYYY-MM`

Use `/docs` for interactive OpenAPI (Swagger UI).

## CLI Commands (Operational)

| Command | Purpose |
|---|---|
| `init-db` | Apply DDL from `sql/schema/postgres.sql` |
| `generate-sample` | Generate synthetic medical + pharmacy claim data |
| `load-sample` | Truncate/reload core sample tables |
| `load-medical-claims` | Load normalized medical files |
| `load-pharmacy-claims` | Load normalized pharmacy files |
| `load-episodes` | Load bundled treatment package catalog and code sets |
| `assign-episodes` | Build bundled treatment package instances and claim assignments |
| `run-pipeline` | Execute integrated reference pipeline |
| `build-member-months` | Build member-month denominator table |
| `report` | PMPM/risk/shared savings outputs |
| `report-bundles` | Bundled treatment package-level gross + allocated spend outputs |

## Healthcare Terminology Mapping

- **Bundled Treatment Package **: Grouped clinical/financial services tied to an index event and a temporal window.
- **Index Event**: Triggering claim event that opens an bundled-package instance.
- **Lookback/Lookforward Window**: Days before/after anchor date used for bundled-package capture.
- **Allowed Amount**: Payer-adjudicated allowed reimbursement amount.
- **Paid Amount**: Actual paid amount after cost sharing and contract effects.
- **PMPM**: Per Member Per Month total allowed cost normalized by covered lives.
- **Attribution**: Assignment of members to accountable providers/entities.
- **NDC**: National Drug Code for pharmacy products.
- **HCPCS/CPT**: Procedure coding systems used for professional/facility services.
- **ICD-10**: Diagnosis/procedure classification used for clinical condition grouping.

## Repository Structure

- `src/vbc_claims/`
  - `etl/` ingestion, catalog loading, pipeline orchestration
  - `episodes/` assignment and overlap allocation engine
  - `measures/` bundle and cost measures
  - `analytics/` report composition layer
  - `api/` FastAPI service module
  - `quality/` reconciliation checks
- `sql/schema/` PostgreSQL schema
- `data/sample/bundled/` bundled treatment package definitions + rules + code sets
- `data/synthetic/` generated synthetic datasets
- `docs/` architecture, bundled treatment package semantics, data dictionary
- `scripts/` runnable demo and orchestration stubs

## Configuration

- `DATABASE_URL` (default `postgresql+psycopg2://vbc:vbc@localhost:5432/vbc_claims`)

For production forks, add:

- secrets manager integration,
- API authN/authZ,
- PHI-safe structured logging/redaction,
- tenant-aware data partitioning and access controls.

## Testing and CI

- Lint: `ruff check src tests`
- Type checks: `mypy src`
- Unit/integration: `pytest -q`

CI runs PostgreSQL service and enables integration mode with `RUN_INTEGRATION=1`.

## Productionization Guidance

Recommended hardening for enterprise use:

- Version-lock bundled treatment package catalogs with formal release governance.
- Implement validation contracts for inbound claim feeds (schema, domain, and conformance checks).
- Add policy modules for payer/program-specific overlap allocation and precedence.
- Add reconciliation packs for:
  - institutional vs professional claim balance checks,
  - pharmacy rebate adjustment extensions,
  - bundled treatment package-level financial conservation assertions.
- Add deployment artifacts for Kubernetes, ingress policy, and workload identity.
- Add RBAC and auditing for catalog/rule changes and assignment reruns.

## Data Privacy and Compliance Notice

Included datasets are synthetic and de-identified for demonstration only. Do not commit PHI. This project is a technical framework and does not itself establish HIPAA compliance, coding accuracy certification, or payer program compliance; implement organizational controls and validation before production use.

## License

Apache-2.0.
