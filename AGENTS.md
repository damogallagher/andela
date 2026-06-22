# Agent Operating Instructions

This repository is for the Andela New Hire Challenge.

## Required Workflow

- The candidate does not manually write or edit application code.
- The AI agent owns all code changes, fixes, tests, documentation updates, and prompt logging.
- Use the same AI agent workflow end-to-end to preserve architectural consistency.
- Claude Code was used at one project stage as an external idea-review pass over the current code; Codex remains the agent of record for repository edits, tests, documentation, and verification.
- Make all repository changes on the `dev` branch and push completed work to `origin/dev`.
- Maintain `prompts.md` after every user instruction or implementation turn.
- `prompts.md` must record the prompt/instruction used, the date, and the agent action taken.
- Keep `README.md` up to date whenever setup, run, test, architecture, or submission details change.
- For any functionality touched, update the relevant unit or functional tests and the Playwright frontend tests before handoff.
- Always run the complete test suite before handoff and report any command that could not run.

## Technical Direction

- Build a Python-based, API-first Enterprise Security Guardrail Auditor.
- Use Postgres as the database.
- Load the database and application locally with `docker-compose.yaml`.
- Provide a local dashboard for scan results and risk scoring.
- Keep development and agent verification local-only. Do not create AWS, Azure, or other cloud resources from the local agent workspace.
- AWS deployment artifacts are maintained through Terraform and GitHub Actions only; actual deployment requires explicitly configured AWS credentials in GitHub Actions.
- Generate the presentation deck only after the code content is stable.

## Safety And Scope

- Do not execute remediation commands against real cloud accounts.
- Sample infrastructure files are safe local fixtures for scanner demonstration.
- Any new scanner rule must include a clear recommendation and a deterministic test where practical.
