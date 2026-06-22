# Prompt Audit Log

This file is maintained by the AI agent as part of the challenge workflow.

Times are recorded in Europe/Dublin local time. Entries 001-010 were originally date-only, so their times were backfilled from the nearest available repository and session activity timestamps.

## 2026-06-22 22:38 IST - Prompt 001 - Required Initial Execution Prompt

```text
Lead Architect mode: ON. We are building a Python-based, API-first Enterprise Security Guardrail Auditor using a free database and a dashboard.

Rules:
- No Manual Edits: You provide all logic and fixes. I will not edit any code.
- Audit Log: You must maintain a file named prompts.md. After every turn, update that file with the prompt I just used.
- Time-Check: Start a timer. Goal is an MVP in 4-6 hours (Max window: 16h). Report "Elapsed Time" at the end of every response.

Acknowledge and let's start.
```

Agent action: Established the project direction and challenge rules.

## 2026-06-22 22:39 IST - Prompt 002 - User Implementation Directives

```text
1. Start project in /Users/damien/Development/sourceControl/Personal/andela
2. Yes, create an AGENTS.md file to state this exact point
3. Yes please, make the AI manage ALL prompts for me
4. Sounds good, insetad of SQLite, use a postgres database, laod up the database and the application using a docker-compose.yaml file. Maintain a README.md file with details on running locally. Add it to AGENTS.md that this file needs to be kep up to date
5. Yes this is a last step, we will generate the presentation deck based on the code content
6. Yes create a repo in github.com/damogallagher/andela
7. For this exercise I want to go local build only
```

Agent action: Scaffolded the local-only FastAPI/Postgres project, Docker Compose setup, README, AGENTS.md, prompt audit log, sample IaC fixtures, and scanner tests.

## 2026-06-22 22:45 IST - Prompt 003 - Verification Fix

```text
Verify the local Python test environment, fix dependency issues found during installation, and keep prompts.md updated as the AI-managed audit log.
```

Agent action: Updated the psycopg binary dependency from 3.2.3 to 3.2.13 because the earlier patch version was not available for the local Python environment.

## 2026-06-22 22:46 IST - Prompt 004 - Test Import Fix

```text
Run the project tests, fix local test configuration issues, and keep the prompt audit log current.
```

Agent action: Added pytest configuration in pyproject.toml so tests can import the local app package from the repository root.

## 2026-06-22 22:52 IST - Prompt 005 - Result Ordering Polish

```text
Verify the running app output, fix any presentation issues that reduce dashboard clarity, and keep prompts.md current.
```

Agent action: Sorted findings by operational severity so critical results appear before high, medium, and low findings in API and dashboard output.

## 2026-06-22 22:52 IST - Prompt 006 - Global Severity Sort Fix

```text
Rerun tests after the severity ordering change, correct any failing behavior, and keep prompts.md current.
```

Agent action: Moved severity sorting to the full scan aggregation so findings are ordered correctly across all scanned files.

## 2026-06-22 22:54 IST - Prompt 007 - README Agent And Model Details

```text
Include details in the README on the coding agent used and the model used
```

Agent action: Added README details for the coding agent, model, and AI-managed workflow.

## 2026-06-22 22:58 IST - Prompt 008 - Expanded Sample IaC And Tests

```text
Can you add sample Terraform and JSON infrastructure files. Some show risky patterns in both, some in 1 set of files, others show good files. Use these files to generate unit tests and functional tests for the application
```

Agent action: Added Terraform and JSON sample scenarios for both-risky, Terraform-only, JSON-only, and clean infrastructure; expanded scanner unit tests; added FastAPI functional tests; and documented the fixture/test coverage in README.md.

## 2026-06-22 23:00 IST - Prompt 009 - Verification Warning Cleanup

```text
Run the expanded test suite, clean up framework deprecation warnings found during verification, and keep prompts.md current.
```

Agent action: Migrated FastAPI startup to a lifespan handler, updated template rendering to the current signature, and replaced Pydantic class Config usage with ConfigDict.

## 2026-06-22 23:03 IST - Prompt 010 - Test Runner Scripts

```text
Create a scripts directory, add scripts to run the unit tests, the functional tests and finallu all tests
```

Agent action: Added executable scripts for unit tests, functional tests, and the full test suite; updated README.md with the script commands.

## 2026-06-22 23:03 IST - Prompt 011 - Prompt Timestamp Backfill

```text
Update prompts.md and add the times the prompts were issues. Currently its only the date
```

Agent action: Added Europe/Dublin local issue times to every prompt heading and documented the source of backfilled times for earlier entries.

## 2026-06-22 23:06 IST - Prompt 012 - Upload Scan API And Frontend

```text
Expand the api and frontend, allow the user to upload a file / files and then scan said files and show results on screen
```

Agent action: Added upload scanning support for one or more infrastructure files, expanded the dashboard with upload controls, and documented the upload API workflow.

## 2026-06-22 23:09 IST - Prompt 013 - Severity Filtering And Findings Table Controls

```text
Update the UI to use color coding for the issue severity. Also allow a user to click on a severity box and only show those issues. If there are alot of issues, also have pagination, searchign and filtering on the table of results. If a box is selected, have breadcrumbs to show if critical / low / medium is selected and a clear button to re show ALL severity isues
```

Agent action: Added color-coded clickable severity cards, active filter breadcrumbs, a clear severity action, client-side search, and findings pagination.

## 2026-06-22 23:24 IST - Prompt 014 - Synthetic Large Fixtures

```text
Generate synthetic terraform files and json fiels for the tests but include a LARGE number of violations for each category. This will be useful when testing searching and pagination.
```

Agent action: Added large synthetic Terraform and JSON fixtures and introduced a low-severity S3 versioning rule to exercise all severity categories during search and pagination testing.

## 2026-06-22 23:24 IST - Prompt 015 - React Frontend Conversion

```text
In the app folder we have a very simple css and html file, is it possible to convert this to a react application with individual styled components? This would make the application easier to extend in the future
```

Agent action: Converted the dashboard from a simple HTML/CSS template into a Vite React application with individual styled-components, updated FastAPI to serve the compiled frontend bundle, and updated build/test documentation.

## 2026-06-22 23:34 IST - Prompt 016 - Playwright Frontend Coverage And Test Policy

```text
Updte the code to have fully functional playwright tests to ALL of the frontend code. Update AGENTS.md, for any functionality that is touched, the unit tests and playwright tests are fully updated. Always make sure that all tests are running
```

Agent action: Added Playwright browser tests for the React dashboard, added a Playwright test script, wired Playwright into the full test runner, and updated AGENTS.md with the test-update and full-suite verification rule.

## 2026-06-22 23:35 IST - Prompt 017 - React Prompt Log Correction

```text
the react upgrade is not listed in prompts.md
```

Agent action: Split the previous combined prompt-log entry so the React frontend conversion is listed explicitly as its own prompt.

## 2026-06-22 23:40 IST - Prompt 018 - GitHub Actions And AWS Terraform Deployment

```text
Create github actions for linting the code both ui and backend, building the code and deploying the code to AWS. For deploying to AWS, we also need a terraform folder with all of the infrastructure to run the application. For terraform, ensure state is stored in an S3 bucket. Include this terraform build step as part of the github actions. Also include unit tests and playwright tests as part of the github actions to ensure they run.
```

Agent action: Added backend and frontend lint tooling, GitHub Actions CI/CD for linting, build, tests, Terraform validation, Docker build, and conditional AWS deployment from dev; added Terraform infrastructure for ECR, ECS Fargate, ALB, RDS Postgres, Secrets Manager, IAM, networking, and S3-backed state configuration.

## 2026-06-22 23:41 IST - Prompt 019 - Claude Code Idea Review Provenance

```text
When the project goto a certain stage, I ran the current cdoe throuh claude code to get ideas. Add this to the AGENTS.md and include it in prompts.md
```

Agent action: Updated AGENTS.md and prompts.md to record that Claude Code was used for external idea review while Codex remains the agent of record for repository edits and verification.

## 2026-06-22 23:42 IST - Prompt 020 - Dev Branch Workflow

```text
From now on, make all changes in the dev branch and push that branch to github
```

Agent action: Switched active work to the dev branch, fast-forwarded dev to the latest implementation baseline, and updated AGENTS.md to require future changes and pushes on dev.

## 2026-06-22 23:48 IST - Prompt 021 - Static Frontend Build Output Clarification

```text
app/static/frontend still exists - is this folder still being used now that we have a react frontend?
```

Agent action: Clarified that `app/static/frontend` is generated React build output served by FastAPI, while source code lives in `frontend/src`; the generated output remains ignored by Git.

## 2026-06-22 23:52 IST - Prompt 022 - Clickable Recent Scans

```text
allow user to click recent scans to see those results. Also incldue the date and time the scan was conducted
```

Agent action: Made recent scans selectable, displayed each scan timestamp in the audit trail, and updated Playwright coverage for switching the dashboard to a selected historical scan.

## 2026-06-22 23:53 IST - Prompt 023 - Wider Dashboard Layout

```text
the page is very squased, update it to use more screen real estate
```

Agent action: Widened the dashboard content area, expanded findings to a full-width row, and changed recent scans into a wider responsive audit-trail band to reduce table crowding.

## 2026-06-22 23:55 IST - Prompt 024 - Docker Compose React Auto Refresh

```text
Update the docker-compose.yaml file, if the frontend react code changes, make sure the browser screen auto refreshes
```

Agent action: Added a Docker Compose Vite frontend service with hot reload on port 5173, configured Docker-friendly API proxying, and documented the auto-refresh development workflow.

## 2026-06-23 00:01 IST - Prompt 025 - Sortable Scrollable Findings Table

```text
Make the results table scrollable horizontally. Also let users sort on teh table headers. Move the recent scans to the right hand side of the screen.
```

Agent action: Made the findings table a horizontally scrollable region with fixed-width columns, added sortable table headers for all findings columns, moved recent scans into a desktop right-side history rail, and expanded Playwright coverage for sorting, table overflow, and desktop history placement.

## 2026-06-23 00:05 IST - Prompt 026 - Score Threshold Colors

```text
If score is above 90, show the final score in greeen, come up with different thresholds to show the percentage score in amber or red
```

Agent action: Updated the React score panel to display the score as a percentage, color it green above 90, amber from 70 to 90, and red below 70, and added Playwright coverage for the threshold boundaries.

## 2026-06-23 00:08 IST - Prompt 027 - Project Lint Scripts

```text
create scripts in the scripts dir to run linting on the project
```

Agent action: Added a project-level lint wrapper script in `scripts/lint-project.sh`, kept the backend/frontend lint scripts as the scoped lint entry points, and documented the lint commands in README.

## 2026-06-23 00:12 IST - Prompt 028 - Weekly Dependabot Grouped PRs

```text
Create a github action to run dependbot on the project. Create 1 PR weekly against the dev branch
```

Agent action: Added `.github/dependabot.yml` with a weekly multi-ecosystem Dependabot group targeting `dev`, consolidating npm, pip, Docker, Terraform, and GitHub Actions dependency updates into one scheduled pull request, and documented the behavior in README.

## 2026-06-23 00:15 IST - Prompt 029 - Postgres 17 Compose Runtime

```text
update docker-compose.yaml to use postgres 17 instead of 16
```

Agent action: Updated the Docker Compose database service from `postgres:16-alpine` to `postgres:17-alpine` and documented the local Postgres 17 service in README.

## 2026-06-23 00:17 IST - Prompt 030 - GitHub Actions Node Runtime Updates

```text
The github actions are making the following complaints. [Terraform format and validate](https://github.com/damogallagher/andela/actions/runs/27990411036/job/82841371598#step:13:2)
Node.js 20 is deprecated. The following actions target Node.js 20 but are being forced to run on Node.js 24: actions/checkout@v4, hashicorp/setup-terraform@v3. For more information see: [https://github.blog/changelog/2025-09-19-deprecation-of-node-20-on-github-actions-runners/](https://github.blog/changelog/2025-09-19-deprecation-of-node-20-on-github-actions-runners/)
[Backend lint and tests](https://github.com/damogallagher/andela/actions/runs/27990411036/job/82841371583#step:17:2)
Node.js 20 is deprecated. The following actions target Node.js 20 but are being forced to run on Node.js 24: actions/checkout@v4, actions/setup-node@v4, actions/setup-python@v5. For more information see: [https://github.blog/changelog/2025-09-19-deprecation-of-node-20-on-github-actions-runners/](https://github.blog/changelog/2025-09-19-deprecation-of-node-20-on-github-actions-runners/)
[UI lint, build, and Playwright](https://github.com/damogallagher/andela/actions/runs/27990411036/job/82841371485#step:17:2)
Node.js 20 is deprecated. The following actions target Node.js 20 but are being forced to run on Node.js 24: actions/checkout@v4, actions/setup-node@v4. For more information see: [https://github.blog/changelog/2025-09-19-deprecation-of-node-20-on-github-actions-runners/](https://github.blog/changelog/2025-09-19-deprecation-of-node-20-on-github-actions-runners/)
[Docker build](https://github.com/damogallagher/andela/actions/runs/27990411036/job/82841474314#step:9:2)
Node.js 20 is deprecated. The following actions target Node.js 20 but are being forced to run on Node.js 24: actions/checkout@v4, docker/build-push-action@v6, docker/setup-buildx-action@v3. For more information see: [https://github.blog/changelog/2025-09-19-deprecation-of-node-20-on-github-actions-runners/](https://github.blog/changelog/2025-09-19-deprecation-of-node-20-on-github-actions-runners/) Update the versions appropriately. Make sure dependabot is setup to also update the github actions
```

Agent action: Updated GitHub Actions workflow dependencies to newer major versions for checkout, setup-node, setup-python, setup-terraform, Docker build/setup, and AWS credential configuration, and confirmed Dependabot includes the `github-actions` ecosystem.

## 2026-06-23 00:19 IST - Prompt 031 - Postgres 17 Volume Compatibility

```text
The attached docker-compose output shows Postgres 17 failing to start because the existing Docker volume was initialized by Postgres 16: "database files are incompatible with server".
```

Agent action: Updated Docker Compose to use a new `postgres17-data` volume for Postgres 17, preserving the old Postgres 16 `postgres-data` volume, and documented the local volume migration note in README.

## 2026-06-23 00:25 IST - Prompt 032 - SARIF Export And Code Scanning Upload

```text
Right now findings only live in the dashboard. Real guardrail tools emit [SARIF](https://sariftools.github.io/) so results show up in the GitHub Security tab and PR annotations. Add a GET /api/scans/{id}/sarif endpoint and have your CI upload it via github/codeql-action/upload-sarif
```

Agent action: Added a SARIF 2.1.0 export endpoint for persisted scans, updated API tests and README coverage, and configured GitHub Actions to generate sample scan SARIF and upload it to GitHub Code Scanning with `github/codeql-action/upload-sarif`.

## 2026-06-23 00:28 IST - Prompt 033 - CLI Pipeline Guardrail

```text
The app is "API-first" but a guardrail auditor's primary job is failing a pipeline. Add python -m app.cli scan <path> --fail-on critical that exits non-zero when findings breach a threshold. This pairs directly with your GitHub Actions steer — the workflow runs the scanner against sample_iac/ and blocks the build on criticals.
```

Agent action: Added a DB-free scanner CLI with severity threshold exit codes, unit coverage for pass/fail/missing-path behavior, and a GitHub Actions guardrail job that blocks Docker build when `sample_iac/` contains critical findings.

## 2026-06-23 00:29 IST - Prompt 034 - UI SARIF Export

```text
Can we add a sarif export from the UI
```

Agent action: Added an Export SARIF dashboard action for the selected scan, wired it to the SARIF API endpoint as a browser download, updated Playwright coverage for disabled and successful download states, and documented the UI export in README.

## 2026-06-23 00:32 IST - Prompt 035 - Table Sort Arrow Indicators

```text
on the table, instead of Sort then A-Z, can we have an up and down arrow instead?
```

Agent action: Replaced visible table sort labels with neutral, ascending, and descending arrow indicators while preserving accessible sort button labels, and updated Playwright sorting coverage for the arrow states.

## 2026-06-23 00:35 IST - Prompt 036 - Architecture Decision Records And Diagram

```text
Architecture Decision Records + a diagram. SAs are judged on documented judgment. Add docs/adr/ (e.g. "why regex over a real HCL parser", "why Postgres over SQLite", "why local-only"). A C4 / component diagram in the README feeds straight into your required presentation deck.
```

Agent action: Added architecture decision records for local-only delivery, Postgres over SQLite, focused scanner patterns over a full HCL parser, and API/CLI/SARIF interfaces; added a README component diagram and linked the ADRs from the challenge submission notes.

## 2026-06-23 00:38 IST - Prompt 037 - Rule Registry Refactor

```text
Rule metadata is duplicated: hardcoded check functions in scanner.py and a hand-written list in main.py's /api/rules endpoint. These will drift. Extract a rule registry (id, title, severity, recommendation, check fn) that both the scanner and /api/rules read from.
```

Agent action: Extracted rule metadata and check functions into `app.scanner.RULES`, updated scanner findings, `/api/rules`, and SARIF rule metadata to read from the registry, and added tests to prevent metadata drift.
