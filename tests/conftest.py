import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def load_local_env() -> None:
    env_file = PROJECT_ROOT / ".env"
    if not env_file.exists():
        return

    for raw_line in env_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_local_env()
os.environ["APP_SCAN_ROOT"] = str(PROJECT_ROOT)
postgres_password = os.environ.get("POSTGRES_PASSWORD")
postgres_auth = f"andela:{postgres_password}" if postgres_password else "andela"
os.environ.setdefault(
    "DATABASE_URL",
    f"postgresql+psycopg://{postgres_auth}@localhost:5432/andela_guardrails_test",
)
