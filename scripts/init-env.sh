#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

if [[ -x ".venv/bin/python" ]]; then
  PYTHON=".venv/bin/python"
else
  PYTHON="python3"
fi

"${PYTHON}" - <<'PY'
from pathlib import Path
from secrets import token_urlsafe

env_path = Path(".env")
password_key = "POSTGRES_PASSWORD"
generated_password = token_urlsafe(32)

if env_path.exists():
    lines = env_path.read_text(encoding="utf-8").splitlines()
else:
    lines = []

updated = False
found = False
next_lines = []

for line in lines:
    if line.startswith(f"{password_key}="):
        found = True
        current_value = line.split("=", 1)[1].strip()
        if current_value:
            next_lines.append(line)
        else:
            next_lines.append(f"{password_key}={generated_password}")
            updated = True
        continue
    next_lines.append(line)

if not found:
    if next_lines and next_lines[-1].strip():
        next_lines.append("")
    next_lines.append(f"{password_key}={generated_password}")
    updated = True

if updated or not env_path.exists():
    env_path.write_text("\n".join(next_lines).rstrip() + "\n", encoding="utf-8")
    print("Created or updated .env with a generated local POSTGRES_PASSWORD.")
else:
    print(".env already has POSTGRES_PASSWORD set; leaving it unchanged.")
PY
