# Security Baseline (AWS-First)

This document defines minimum security posture for deploying the bundled treatment engine in regulated healthcare contexts.

## IAM and Access

- Use OIDC-based GitHub Actions role assumption (`aws-actions/configure-aws-credentials`) and avoid long-lived AWS keys.
- Separate IAM roles for:
  - ECS task execution (image pull/log write),
  - ECS runtime (app-level data access),
  - Terraform deployment role.
- Scope runtime role to exact S3 bucket ARN and required prefixes.

## Network Segmentation

- Place RDS in private subnets only.
- Allow Postgres ingress only from ECS task SG.
- Keep ECS tasks in private subnets behind ALB.
- Restrict admin/database access through approved bastion or SSM session mechanisms.

## Secrets and Config

- Store DB credentials and API secrets in AWS Secrets Manager or SSM Parameter Store.
- Rotate DB credentials on a scheduled cadence and after incident response.
- Do not commit credentials in tfvars; use secure variable injection in CI.

## Logging and PHI Safety

- Enable JSON structured logs (`LOG_JSON=true`) in cloud deployments.
- Avoid PHI in logs; treat claim IDs and member identifiers as sensitive metadata.
- Set CloudWatch retention and export policy according to governance policy.

## CI Scanning

- Dependency scan in CI (`pip-audit`) with exception process.
- Add container image scanning in ECR and/or CI stage.
- Add IaC checks (`terraform validate`, optional `tflint`, `checkov`) before apply.

## Incident and Recovery

- Enable automated DB backups with retention aligned to policy.
- Document rollback for:
  - ECS service deployments,
  - Terraform applies,
  - schema changes (`init-db`/migration path).

