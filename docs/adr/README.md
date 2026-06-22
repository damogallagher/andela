# Architecture Decision Records

This directory records the main technical decisions for the Andela Enterprise Security Guardrail Auditor.

| ADR | Decision |
| --- | --- |
| [0001](0001-local-only-delivery.md) | Keep development and verification local-only |
| [0002](0002-postgres-over-sqlite.md) | Use Postgres for scan history |
| [0003](0003-regex-scanner-over-hcl-parser.md) | Use focused text and JSON scanning instead of a full HCL parser |
| [0004](0004-api-cli-and-sarif-interfaces.md) | Expose scanner results through API, CLI, dashboard, and SARIF |
| [0005](0005-normalized-risk-score.md) | Use a normalized weighted risk score |
