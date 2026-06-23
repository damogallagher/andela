#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

if [[ -f ".env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source ".env"
  set +a
fi

if [[ -x ".venv/bin/python" ]]; then
  PYTHON=".venv/bin/python"
else
  PYTHON="python3"
fi

if [[ -z "${DATABASE_URL:-}" ]]; then
  if [[ -n "${POSTGRES_PASSWORD:-}" ]]; then
    export DATABASE_URL="postgresql+psycopg://andela:${POSTGRES_PASSWORD}@localhost:5432/andela_guardrails_test"
  else
    export DATABASE_URL="postgresql+psycopg://andela@localhost:5432/andela_guardrails_test"
  fi
fi

"${PYTHON}" - <<'PY'
import os
import time

import psycopg
from psycopg import sql
from sqlalchemy.engine import make_url

database_url = os.environ["DATABASE_URL"]
url = make_url(database_url)
if not url.drivername.startswith("postgresql"):
    raise SystemExit("Only PostgreSQL test database URLs are supported.")
if not url.database:
    raise SystemExit("DATABASE_URL must include a test database name.")

admin_url = url.set(drivername="postgresql", database="postgres")
conninfo = admin_url.render_as_string(hide_password=False)
last_error = None

for _ in range(30):
    try:
        with psycopg.connect(conninfo, autocommit=True) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (url.database,))
                if cursor.fetchone() is None:
                    cursor.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(url.database)))
        break
    except Exception as exc:
        last_error = exc
        time.sleep(1)
else:
    raise SystemExit(f"Postgres test database is unavailable: {last_error}")
PY
