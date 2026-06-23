#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
REQUIRED_PYTHON_VERSION="${REQUIRED_PYTHON_VERSION:-3.14}"

candidates=()

if [[ -n "${PYTHON:-}" ]]; then
  candidates+=("${PYTHON}")
fi

if [[ -x "${REPO_ROOT}/.venv/bin/python" ]]; then
  candidates+=("${REPO_ROOT}/.venv/bin/python")
fi

if command -v pyenv >/dev/null 2>&1; then
  pyenv_root="$(pyenv root 2>/dev/null || true)"
  if [[ -n "${pyenv_root}" ]]; then
    shopt -s nullglob
    for python_path in "${pyenv_root}/versions/${REQUIRED_PYTHON_VERSION}"*/bin/python; do
      candidates+=("${python_path}")
    done
    shopt -u nullglob
  fi
fi

for command_name in "python${REQUIRED_PYTHON_VERSION}" python3 python; do
  if command -v "${command_name}" >/dev/null 2>&1; then
    candidates+=("$(command -v "${command_name}")")
  fi
done

for candidate in "${candidates[@]}"; do
  if ! command -v "${candidate}" >/dev/null 2>&1 && [[ ! -x "${candidate}" ]]; then
    continue
  fi

  version="$("${candidate}" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null || true)"
  gil_disabled="$("${candidate}" -c 'import sysconfig; print(sysconfig.get_config_var("Py_GIL_DISABLED") or 0)' 2>/dev/null || true)"
  if [[ "${ALLOW_FREE_THREADED_PYTHON:-0}" != "1" && "${gil_disabled}" == "1" ]]; then
    continue
  fi

  if [[ "${version}" == "${REQUIRED_PYTHON_VERSION}" ]]; then
    echo "${candidate}"
    exit 0
  fi
done

cat >&2 <<EOF
Standard CPython ${REQUIRED_PYTHON_VERSION} is required for this project.
Free-threaded Python builds are skipped by default because pinned binary dependencies
may not publish wheels for the free-threaded ABI.
Create a local environment with:

  python${REQUIRED_PYTHON_VERSION} -m venv .venv
  source .venv/bin/activate
  pip install -r requirements-lock.txt

Or set PYTHON to a Python ${REQUIRED_PYTHON_VERSION} interpreter.
Set ALLOW_FREE_THREADED_PYTHON=1 only if you have verified dependency support.
EOF
exit 1
