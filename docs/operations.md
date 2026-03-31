# Operations Playbook

## SLO-Supporting Checks

- API health: `GET /health`
- API readiness: `GET /ready` (DB dependency check)
- Reconciliation snapshot: `run_reconciliation_report()`

Key indicators:

- `episode_assignments` volume trend
- `overlap_claims` trend
- `allocation_conservation_failures` must remain `0`
- `orphan_claim_lines` must remain `0`

## Standard Run Sequence

1. Load data (`load-sample` or normalized loaders).
2. Load bundled catalog (`load-episodes`).
3. Build denominators (`build-member-months`).
4. Assign packages (`assign-episodes`).
5. Validate reconciliation output.

## Rollback Notes

- **App rollback**: redeploy prior ECS task definition revision.
- **Infra rollback**: apply previous Terraform state-compatible config (avoid manual drift).
- **Data rollback**: restore RDS snapshot to recovery instance and cut over.

