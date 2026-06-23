# Claude Code Instructions

This repository is for the Andela New Hire Challenge. Codex remains the agent of record for repository edits, tests, documentation, and verification, but this file gives Claude CoWork/Claude Code the same project constraints when reviewing or generating presentation material.

## Project Rules

- Treat the candidate as human-in-the-loop architect and the AI agent as implementation owner.
- Do not make manual code edits outside the agent workflow.
- Keep `prompts.md` current after user instructions.
- Keep `README.md`, `AGENTS.md`, and this `CLAUDE.md` aligned when setup, runtime, testing, architecture, branch, or submission details change.
- Make repository changes on `dev`, then sync `main` to the same verified commit.

## Runtime And Tests

- Target standard CPython 3.14 for local verification, GitHub Actions, and the Docker runtime.
- Do not use free-threaded Python builds unless dependency wheel support has been explicitly verified.
- Use Postgres only; do not add SQLite or alternate database paths.
- Keep Python dependency changes reflected in `requirements.txt`, `requirements-dev.txt`, and `requirements-lock.txt`.
- Run the complete gate before handoff:

```bash
./scripts/lint-all.sh
./scripts/test-all.sh
```

- `./scripts/test-coverage.sh` must keep Python `app` package statement coverage at 100%.
- Playwright tests must stay current for touched frontend functionality.

## Scope

- Keep local development and agent verification local-only.
- Do not create, modify, or delete real cloud resources from the local workspace.
- AWS deployment is represented through Terraform and GitHub Actions only, and requires explicit GitHub repository variables.
- Sample IaC files are local scanner fixtures and are safe to use in tests and presentation material.
