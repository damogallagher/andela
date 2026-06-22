# Andela Enterprise Security Guardrail Auditor

Python-based, API-first security guardrail auditor for the Andela New Hire Challenge. The app scans Terraform and JSON infrastructure files for risky patterns, stores scan results in Postgres, and renders a local dashboard with a visual risk score.

This project is intentionally local-only. It does not create AWS, Azure, or other cloud resources.

## Stack

- FastAPI for the API and dashboard server
- Postgres for scan history and findings
- SQLAlchemy for persistence
- Docker Compose for local app and database startup
- Pytest for scanner tests

## Coding Agent And Model

- Coding agent: OpenAI Codex, running in the Codex desktop app.
- Model used: GPT-5.
- Workflow: the coding agent generated and edited the application code, maintained `prompts.md`, updated documentation, ran verification commands, and published the repository.

## Run Locally

```bash
docker compose up --build
```

Open:

- Dashboard: http://localhost:8000
- API docs: http://localhost:8000/docs
- Health check: http://localhost:8000/health

The default Compose configuration starts:

- `andela-app` on port `8000`
- `andela-postgres` on port `5432`

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

## Run Tests

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
pytest
```

## Challenge Submission Notes

Include these artifacts in the final submission:

- Tagle output summary: Connector - Foundation Operator
- Public GitHub repository link
- `prompts.md` audit log
- AI-generated presentation deck, created after the code is complete
- Cloud cleanup confirmation: no cloud resources were created; this was a local-only Docker Compose build
