# Agent Operating Instructions

This repository is for the Andela New Hire Challenge.

## Required Workflow

- The candidate does not manually write or edit application code.
- The AI agent owns all code changes, fixes, tests, documentation updates, and prompt logging.
- Use the same AI agent workflow end-to-end to preserve architectural consistency.
- Maintain `prompts.md` after every user instruction or implementation turn.
- `prompts.md` must record the prompt/instruction used, the date, and the agent action taken.
- Keep `README.md` up to date whenever setup, run, test, architecture, or submission details change.

## Technical Direction

- Build a Python-based, API-first Enterprise Security Guardrail Auditor.
- Use Postgres as the database.
- Load the database and application with `docker-compose.yaml`.
- Provide a local dashboard for scan results and risk scoring.
- Keep the build local-only. Do not create AWS, Azure, or other cloud resources.
- Generate the presentation deck only after the code content is stable.

## Safety And Scope

- Do not execute remediation commands against real cloud accounts.
- Sample infrastructure files are safe local fixtures for scanner demonstration.
- Any new scanner rule must include a clear recommendation and a deterministic test where practical.

