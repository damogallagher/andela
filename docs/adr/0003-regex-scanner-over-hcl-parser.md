# ADR 0003: Use Focused Text And JSON Scanning Instead Of A Full HCL Parser

Status: Accepted

Date: 2026-06-23

## Context

The scanner needs to identify a small, explicit set of risky infrastructure patterns in Terraform and JSON CloudFormation-style files:

- Public SSH ingress
- Hardcoded credentials and AWS access key patterns
- Public S3 ACLs
- Wildcard IAM policies
- Disabled database encryption
- Suspended or disabled S3 versioning

The challenge rewards a working guardrail auditor and documented tradeoffs, not exhaustive Terraform language support.

## Decision

Use deterministic JSON parsing for JSON and focused text pattern scanning for Terraform.

Avoid adding a full HCL parser for the current scope.

## Consequences

- The scanner is small, easy to inspect, and easy to test with synthetic fixtures.
- Unit tests can cover each intended rule and severity category without a heavy dependency.
- The implementation is appropriate for a challenge MVP and presentation deck.
- Terraform support is intentionally limited and may miss complex expressions, modules, variables, dynamic blocks, or generated values.

## Alternatives Considered

- Full HCL parser. Deferred because it would add dependency and integration complexity for a small rule catalog.
- Shelling out to tools such as Checkov, tfsec, or Terrascan. Rejected for the core app because this project should demonstrate its own API, persistence, SARIF, and CI integration behavior.

## Follow-Up

If the scanner grows beyond simple deterministic patterns, replace or supplement the text scanner with a real HCL parser and add rule tests for variables, modules, and dynamic blocks.
