#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

PYTHON="$(bash "${REPO_ROOT}/scripts/python-bin.sh")"

"${PYTHON}" -m pytest tests/test_scanner.py tests/test_cli.py tests/test_sarif.py tests/test_observability.py "$@"
