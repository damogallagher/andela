# Terraform AWS Deployment

This folder defines the optional AWS deployment for the Andela guardrail auditor.

Terraform state is stored in S3 via the backend declared in `versions.tf`. The S3 bucket and DynamoDB lock table must exist before `terraform init` runs. Use `backend.example.hcl` as the template for local initialization.

GitHub Actions passes backend settings from repository variables:

- `TF_STATE_BUCKET`
- `TF_STATE_KEY`
- `AWS_REGION`
- `TF_STATE_LOCK_TABLE`

The default deployment target is ECS Fargate behind an Application Load Balancer with RDS Postgres for persistence.
