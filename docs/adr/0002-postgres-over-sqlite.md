# ADR 0002: Use Postgres For Scan History

Status: Accepted

Date: 2026-06-23

## Context

Scan results need to survive application restarts, support recent scan history, and model realistic audit-trail behavior. The app runs locally with Docker Compose and has optional AWS deployment infrastructure.

SQLite would be simpler for local development, but it is less representative of how an enterprise guardrail service would be deployed.

## Decision

Use Postgres as the application database and run it through Docker Compose for local development.

Use SQLAlchemy as the persistence layer so the FastAPI application can store scan runs and findings in a relational schema.

## Consequences

- Local behavior is closer to the AWS RDS deployment shape.
- Recent scans and findings persist across app restarts through a Docker volume.
- The project demonstrates operational judgment around database-backed audit trails.
- Local setup requires Docker Compose rather than a single Python process.

## Alternatives Considered

- SQLite. Rejected for the final implementation because the user requested Postgres and because Postgres better matches the deployed architecture.
- In-memory storage. Rejected because scan history and audit trail behavior would disappear on restart.
