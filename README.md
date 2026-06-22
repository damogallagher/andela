# Andela Enterprise Security Guardrail Auditor

Python-based, API-first security guardrail auditor for the Andela New Hire Challenge. The app scans Terraform and JSON infrastructure files for risky patterns, stores scan results in Postgres, and renders a local dashboard with a visual risk score.

This project is intentionally local-only. It does not create AWS, Azure, or other cloud resources.

## Stack

- FastAPI for the API and dashboard server
- React and Vite for the dashboard frontend
- styled-components for component-scoped styling
- Postgres for scan history and findings
- SQLAlchemy for persistence
- Docker Compose for local app and database startup
- Pytest for scanner tests
- Playwright for frontend browser tests

## Coding Agent And Model

- Coding agent: OpenAI Codex, running in the Codex desktop app.
- Model used: GPT-5.5
- Workflow: the coding agent generated and edited the application code, maintained `prompts.md`, updated documentation, ran verification commands, and published the repository.

## Run Locally

```bash
docker compose up --build
```

Open:

- Dashboard: http://localhost:8000
- API docs: http://localhost:8000/docs
- Health check: http://localhost:8000/health

The dashboard supports severity color coding, clickable severity filters, breadcrumbs for the active severity filter, a clear-filter action, findings search, and paginated result rows.

The default Compose configuration starts:

- `andela-app` on port `8000`
- `andela-postgres` on port `5432`

## Frontend Development

The React dashboard source lives in `frontend/src`. FastAPI serves the compiled Vite output from `app/static/frontend`.

Build the frontend:

```bash
./scripts/build-frontend.sh
```

Run the Vite dev server while the FastAPI app is running:

```bash
npm --prefix frontend run dev
```

## Run A Sample Scan

Use the dashboard button, or call the API:

```bash
curl -X POST http://localhost:8000/api/scans/sample
```

List scan history:

```bash
curl http://localhost:8000/api/scans
```

Scan a path under the configured local scan root:

```bash
curl -X POST http://localhost:8000/api/scans \
  -H "Content-Type: application/json" \
  -d '{"path":"sample_iac","label":"Sample IaC scan"}'
```

Upload one or more infrastructure files and scan them without writing them to disk:

```bash
curl -X POST http://localhost:8000/api/scans/upload \
  -F "label=Uploaded IaC scan" \
  -F "files=@sample_iac/scenarios/both_risky/terraform/main.tf" \
  -F "files=@sample_iac/scenarios/json_only/risky_cloudformation.json"
```

## Sample Infrastructure Fixtures

The `sample_iac/scenarios` folder contains Terraform and JSON CloudFormation-style files used by the scanner and tests:

- `both_risky`: Terraform and JSON files both contain risky patterns.
- `terraform_only`: Terraform contains risky patterns; JSON is clean.
- `json_only`: JSON contains risky patterns; Terraform is clean.
- `clean`: Terraform and JSON files are both configured safely.
- `large_violations`: Terraform and JSON contain a large synthetic finding set for search, filtering, and pagination testing.

The sample findings cover public SSH ingress, public S3 ACLs, wildcard IAM policies, disabled database encryption, and suspended S3 versioning.

## Run Tests

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```

Use the scripts directory to run the test scopes:

```bash
./scripts/test-unit.sh
./scripts/test-functional.sh
./scripts/test-playwright.sh
./scripts/test-all.sh
```

The functional and full test scripts build the React frontend before running FastAPI tests. `test-all.sh` also runs the Playwright browser suite after the Python tests. The test suite includes scanner unit tests for each fixture scenario, FastAPI functional tests for scan creation, scan history, scan detail lookup, dashboard serving, rules metadata, missing paths, and scan-root path safety, plus Playwright coverage for the React dashboard empty/loading/error states, sample scan, severity filtering, breadcrumbs, search, pagination, uploads, scan history, and mobile-width usability.

The Playwright config uses the local Vite dev server and mocked API responses for deterministic frontend coverage. It uses system Chrome by default; set `PLAYWRIGHT_USE_SYSTEM_CHROME=0` if you want to run with Playwright-managed browsers after installing them.

## Challenge Submission Notes

Include these artifacts in the final submission:

- Tagle output summary: Connector - Foundation Operator
- Public GitHub repository link
- `prompts.md` audit log
- AI-generated presentation deck, created after the code is complete
- Cloud cleanup confirmation: no cloud resources were created; this was a local-only Docker Compose build
