#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

PYTHON="$(bash "${REPO_ROOT}/scripts/python-bin.sh")"

if [[ -z "${DATABASE_URL:-}" ]]; then
  TEST_POSTGRES_CONTAINER="${TEST_POSTGRES_CONTAINER:-andela-test-postgres}"
  TEST_POSTGRES_PORT="${TEST_POSTGRES_PORT:-55432}"

  if ! docker container inspect "${TEST_POSTGRES_CONTAINER}" >/dev/null 2>&1; then
    docker run -d \
      --name "${TEST_POSTGRES_CONTAINER}" \
      -e POSTGRES_DB=andela_guardrails_test \
      -e POSTGRES_USER=andela \
      -e POSTGRES_HOST_AUTH_METHOD=trust \
      -p "${TEST_POSTGRES_PORT}:5432" \
      postgres:17-alpine >/dev/null
  else
    docker start "${TEST_POSTGRES_CONTAINER}" >/dev/null
  fi

  export DATABASE_URL="postgresql+psycopg://andela@localhost:${TEST_POSTGRES_PORT}/andela_guardrails_test"
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
