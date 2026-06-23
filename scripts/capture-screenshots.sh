#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

mkdir -p screenshots
npm --prefix frontend ci
CAPTURE_PRESENTATION_SCREENSHOTS=1 npm --prefix frontend run test:e2e -- tests/e2e/presentation-screenshots.spec.js --project=chromium "$@"
