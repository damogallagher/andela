# ADR 0004: Expose Scanner Results Through API, CLI, Dashboard, And SARIF

Status: Accepted

Date: 2026-06-23

## Context

A guardrail auditor has several audiences:

- Developers need a dashboard to inspect findings and previous scans.
- CI pipelines need a command that can fail builds.
- GitHub users need SARIF so findings can appear in code scanning and PR annotations.
- API consumers need structured scan results for automation.

Keeping findings only in the dashboard would make the tool less useful as a guardrail.

## Decision

Keep the scanner core independent of FastAPI and expose it through four interfaces:

- FastAPI scan endpoints for programmatic use and dashboard data.
- React dashboard for upload, filtering, search, sorting, pagination, scan history, and SARIF download.
- `python -m app.cli scan <path> --fail-on <severity>` for CI pipeline gates.
- SARIF 2.1.0 export for GitHub Code Scanning upload.

## Consequences

- The same scanner rules are reused across dashboard, API, CLI, tests, and CI.
- CI can fail a build without requiring the database or web server.
- GitHub code scanning can consume findings through SARIF.
- There are more interfaces to test and document.

## Alternatives Considered

- Dashboard-only findings. Rejected because it does not behave like a real guardrail tool.
- API-only findings. Rejected because CI pipelines should not need a running web service to fail a build.
- SARIF-only output. Rejected because the dashboard and API are useful for local review and challenge presentation.
