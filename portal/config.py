"""Settings read from environment variables (and a local .env file if present)."""
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")


def _int(name: str, default: int) -> int:
    return int(os.getenv(name, default))


def _float(name: str, default: float) -> float:
    return float(os.getenv(name, default))


# Any SQLAlchemy URL works. SQLite (a local file, no server) is the default; see README for other engines.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///data/demo_capital.db")
SCHEMA_FILE = ROOT / "db" / "schema.sql"

FAKER_SEED = _int("FAKER_SEED", 2026)
NUM_CUSTOMERS = _int("NUM_CUSTOMERS", 300)
NUM_TRANSACTIONS = _int("NUM_TRANSACTIONS", 6000)

MAX_RANGE_DAYS = 5  # longest date range allowed on lookup pages
QUERY_MAX_ROWS = 20  # rows shown by the Execute Query page
IDLE_TIMEOUT_MINUTES = _int("IDLE_TIMEOUT_MINUTES", 60)

LARGE_TXN_THRESHOLD = _float("LARGE_TXN_THRESHOLD", 50000)
DUPLICATE_WINDOW_MINUTES = _int("DUPLICATE_WINDOW_MINUTES", 10)
RETRY_WINDOW_MINUTES = _int("RETRY_WINDOW_MINUTES", 60)
RECON_AMOUNT_TOLERANCE = _float("RECON_AMOUNT_TOLERANCE", 0.01)

COMPANY = "Demo Capital"

# (username, role, env var for the password, default password)
DEMO_USERS = [
    ("admin", "Admin", "DEMO_ADMIN_PASSWORD", "admin-demo-1"),
    ("finance", "Finance", "DEMO_FINANCE_PASSWORD", "finance-demo-1"),
    ("operations", "Operations", "DEMO_OPERATIONS_PASSWORD", "ops-demo-1"),
]


def demo_users() -> list[tuple[str, str, str]]:
    """Return (username, role, password) for each demo login."""
    return [(u, r, os.getenv(env, default)) for u, r, env, default in DEMO_USERS]
