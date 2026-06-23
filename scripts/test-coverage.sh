#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

"${REPO_ROOT}/scripts/ensure-test-db.sh"

PYTHON="$(bash "${REPO_ROOT}/scripts/python-bin.sh")"

"${PYTHON}" -m coverage erase
"${PYTHON}" -m coverage run --source=app -m pytest tests "$@"
"${PYTHON}" -m coverage report --fail-under=100 -m
