"""Database access through SQLAlchemy. Postgres by default; set DATABASE_URL to swap engines."""
from contextlib import contextmanager

import pandas as pd
from sqlalchemy import create_engine, text

from . import config
from .auth import hash_password, verify_password
from .datagen import generate
from .pages_registry import DEFAULT_ACCESS, LOCKED, PAGES

DATA_TABLES = ["customers", "wallets", "transactions", "ledger_entries", "processor_entries"]

_engine = None


def engine():
    global _engine
    if _engine is None:
        _engine = create_engine(config.DATABASE_URL, pool_pre_ping=True)
    return _engine


@contextmanager
def connect():
    """Transactional connection: commits on success, rolls back on error."""
    with engine().begin() as con:
        yield con


def query(sql: str, params: dict | None = None) -> pd.DataFrame:
    with connect() as con:
        return pd.read_sql_query(text(sql), con, params=params)


def read_table(name: str) -> pd.DataFrame:
    if name not in DATA_TABLES + ["users", "page_access"]:
        raise ValueError(f"Unknown table: {name}")
    return query(f"SELECT * FROM {name}")


def _run_schema(con) -> None:
    for stmt in config.SCHEMA_FILE.read_text().split(";"):
        # drop comment-only lines, skip empty statements
        body = "\n".join(l for l in stmt.splitlines() if not l.strip().startswith("--")).strip()
        if body:
            con.execute(text(body))


def _seed_data(con) -> None:
    for name, df in generate().items():
        df.to_sql(name, con, if_exists="append", index=False, method="multi", chunksize=1000)


def _clear_data(con) -> None:
    for name in reversed(DATA_TABLES):
        con.execute(text(f"DELETE FROM {name}"))


def init_db(reset_data: bool = False) -> None:
    """Create tables, seed synthetic data when empty, and sync demo users."""
    with connect() as con:
        _run_schema(con)
        empty = con.execute(text("SELECT COUNT(*) FROM transactions")).scalar() == 0
        if reset_data or empty:
            _clear_data(con)
            _seed_data(con)
        for user, role, pw in config.demo_users():
            row = con.execute(
                text("SELECT password_hash FROM users WHERE username = :u"), {"u": user}
            ).fetchone()
            if row is None or not verify_password(pw, row[0]):
                con.execute(
                    text(
                        "INSERT INTO users (username, role, password_hash) VALUES (:u, :r, :h) "
                        "ON CONFLICT (username) DO UPDATE SET role = EXCLUDED.role, "
                        "password_hash = EXCLUDED.password_hash"
                    ),
                    {"u": user, "r": role, "h": hash_password(pw)},
                )
        if con.execute(text("SELECT COUNT(*) FROM page_access")).scalar() == 0:
            con.execute(
                text("INSERT INTO page_access (role, page_key) VALUES (:r, :p)"),
                [{"r": r, "p": p} for r, pages in DEFAULT_ACCESS.items() for p in pages],
            )


def authenticate(username: str, password: str) -> str | None:
    """Return the role if credentials are valid, else None."""
    with connect() as con:
        row = con.execute(
            text("SELECT role, password_hash FROM users WHERE username = :u"),
            {"u": username.strip().lower()},
        ).fetchone()
    if row and verify_password(password, row[1]):
        return row[0]
    return None


def get_access() -> dict[str, set[str]]:
    with connect() as con:
        rows = con.execute(text("SELECT role, page_key FROM page_access")).fetchall()
    access: dict[str, set[str]] = {}
    for role, page in rows:
        access.setdefault(role, set()).add(page)
    for role, page in LOCKED:
        access.setdefault(role, set()).add(page)
    return access


def allowed_pages(role: str) -> list[str]:
    allowed = get_access().get(role, set())
    return [k for k in PAGES if k in allowed]


def save_access(matrix: dict[str, set[str]]) -> None:
    with connect() as con:
        con.execute(text("DELETE FROM page_access"))
        rows = [{"r": r, "p": p} for r, pages in matrix.items() for p in pages]
        if rows:
            con.execute(text("INSERT INTO page_access (role, page_key) VALUES (:r, :p)"), rows)


def table_counts() -> dict[str, int]:
    with connect() as con:
        return {t: con.execute(text(f"SELECT COUNT(*) FROM {t}")).scalar() for t in DATA_TABLES}
