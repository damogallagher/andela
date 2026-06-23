#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

PYTHON="$(bash "${REPO_ROOT}/scripts/python-bin.sh")"

"${PYTHON}" -m ruff check app tests alembic
"${PYTHON}" -m compileall -q app tests alembic
