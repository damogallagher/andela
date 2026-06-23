#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

"${REPO_ROOT}/scripts/build-frontend.sh"
"${REPO_ROOT}/scripts/ensure-test-db.sh"

if [[ -x ".venv/bin/python" ]]; then
  PYTHON=".venv/bin/python"
else
  PYTHON="python3"
fi

"${PYTHON}" -m pytest "$@"
"${REPO_ROOT}/scripts/test-playwright.sh"
