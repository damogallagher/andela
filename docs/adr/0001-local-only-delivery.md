# ADR 0001: Keep Development And Verification Local-Only

Status: Accepted

Date: 2026-06-23

## Context

The challenge requires a working product, prompt log, public repository, generated deck, and cloud cleanup confirmation. The candidate is responsible for any cloud resources and costs created during the exercise.

The application needs to demonstrate realistic security guardrail workflows without requiring live AWS accounts, cloud credentials, or paid services during development.

## Decision

Keep implementation, development, and agent verification local-only.

Use Docker Compose to run the app, Postgres, and React development server locally. Keep AWS deployment artifacts in Terraform and GitHub Actions, but require explicit GitHub repository variables and credentials before any deployment can run.

## Consequences

- Reviewers can run the application locally without cloud access.
- Verification is deterministic and cheap because sample infrastructure fixtures live in the repository.
- Cloud cleanup risk is reduced because the agent workspace does not create live cloud resources.
- The repository still demonstrates cloud deployment judgment through Terraform and CI/CD artifacts.

## Alternatives Considered

- Deploy every change to AWS during development. Rejected because it creates cost, cleanup, and credential risk for a challenge submission.
- Build a fully static demo with no backend. Rejected because the project needs API, persistence, uploads, SARIF export, and CI guardrail behavior.
