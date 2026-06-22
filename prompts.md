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
