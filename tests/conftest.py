import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# app.database builds DATABASE_URL at import time; provide safe defaults for tests.
os.environ.setdefault("DB_USER", "postgres")
os.environ.setdefault("DB_PASS", "postgres")
os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_PORT", "5432")
os.environ.setdefault("DB_NAME", "tt4d_test")
