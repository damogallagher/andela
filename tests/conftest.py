import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

os.environ["APP_SCAN_ROOT"] = str(PROJECT_ROOT)
os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"

