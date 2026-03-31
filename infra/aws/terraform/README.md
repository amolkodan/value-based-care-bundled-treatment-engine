# AWS Terraform Baseline

This directory provides an AWS-first infrastructure baseline for the bundled treatment engine.

## What it provisions

- VPC with public/private subnets
- ALB + ECS/Fargate service for `vbc-claims-api`
- RDS PostgreSQL
- S3 data/artifacts bucket
- CloudWatch log group
- IAM task execution and runtime roles

## Usage

```bash
cd infra/aws/terraform
terraform init
terraform plan -var-file=env/dev.tfvars
terraform apply -var-file=env/dev.tfvars
```

## Notes

- Replace placeholder values in `env/*.tfvars` before apply.
- Use secret managers or secure CI variables for `db_password`.
- For production, add WAF, TLS certificates, and tighter IAM boundaries.

