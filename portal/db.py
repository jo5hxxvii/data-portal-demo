"""Database access through SQLAlchemy. SQLite by default; set DATABASE_URL to swap engines."""
from contextlib import contextmanager
from pathlib import Path

import re

import pandas as pd
from sqlalchemy import bindparam, create_engine, inspect, text
from sqlalchemy.engine import make_url

from . import config
from .auth import hash_password, verify_password
from .datagen import generate
from .pages_registry import DEFAULT_ACCESS, DEFAULT_REPORTS, PAGES, ROLES

DATA_TABLES = ["customers", "wallets", "transactions", "ledger_entries", "processor_entries",
               "maturities", "savings_plans", "equity_holdings"]

_engine = None


def engine():
    global _engine
    if _engine is None:
        url = make_url(config.DATABASE_URL)
        if url.get_backend_name() == "sqlite" and url.database and url.database != ":memory:":
            db_path = Path(url.database)
            if not db_path.is_absolute():
                db_path = config.ROOT / db_path  # relative paths resolve from the project root
                url = url.set(database=str(db_path))
            db_path.parent.mkdir(parents=True, exist_ok=True)
        _engine = create_engine(url, pool_pre_ping=True)
    return _engine


@contextmanager
def connect():
    """Transactional connection: commits on success, rolls back on error."""
    with engine().begin() as con:
        yield con


def query(sql: str, params: dict | None = None) -> pd.DataFrame:
    """Run a SELECT with :named parameters. A list value works with IN :name."""
    stmt = text(sql)
    lists = [k for k, v in (params or {}).items() if isinstance(v, (list, tuple))]
    if lists:
        stmt = stmt.bindparams(*[bindparam(k, expanding=True) for k in lists])
    with connect() as con:
        return pd.read_sql_query(stmt, con, params=params)


def run_select(sql: str, limit: int) -> pd.DataFrame:
    """Run SQL as written and return at most `limit` rows. Only for text that passed query_guard."""
    with connect() as con:
        result = con.exec_driver_sql(sql)
        return pd.DataFrame(result.fetchmany(limit), columns=list(result.keys()))


def dialect() -> str:
    """Engine name in the form sqlglot expects."""
    name = make_url(config.DATABASE_URL).get_backend_name()
    return "postgres" if name == "postgresql" else name


def data_date():
    """Date of the newest transaction. The demo treats this as today."""
    return pd.to_datetime(query("SELECT MAX(created_at) AS d FROM transactions")["d"][0]).date()


def read_table(name: str) -> pd.DataFrame:
    if name not in DATA_TABLES + ["users", "page_access", "roles", "reports"]:
        raise ValueError(f"Unknown table: {name}")
    return query(f"SELECT * FROM {name}")


def _run_schema(con) -> None:
    for stmt in config.SCHEMA_FILE.read_text().split(";"):
        # drop comment-only lines, skip empty statements
        body = "\n".join(l for l in stmt.splitlines() if not l.strip().startswith("--")).strip()
        if body:
            con.execute(text(body))


def _count(con, table: str) -> int:
    return con.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()


def _seed_data(con) -> None:
    """Fill every data table that is empty."""
    empty = [t for t in DATA_TABLES if _count(con, t) == 0]
    if not empty:
        return
    for name, df in generate().items():
        if name in empty:
            df.to_sql(name, con, if_exists="append", index=False, method="multi", chunksize=1000)


def _clear_data(con) -> None:
    for name in reversed(DATA_TABLES):
        con.execute(text(f"DELETE FROM {name}"))


def init_db(reset_data: bool = False) -> None:
    """Create tables, seed synthetic data, roles, reports and demo users where missing."""
    with connect() as con:
        _run_schema(con)
        if "active" not in [c["name"] for c in inspect(con).get_columns("users")]:  # older databases
            con.execute(text("ALTER TABLE users ADD COLUMN active INTEGER NOT NULL DEFAULT 1"))
        if reset_data:
            _clear_data(con)
        _seed_data(con)
        if _count(con, "roles") == 0:
            con.execute(text("INSERT INTO roles (name, description, is_super) VALUES (:n, :d, :s)"),
                        [{"n": n, "d": d, "s": s} for n, d, s in ROLES])
        if _count(con, "reports") == 0:
            con.execute(text("INSERT INTO reports (slug, title, url, active) VALUES (:s, :t, :u, :a)"),
                        [{"s": s, "t": t, "u": u, "a": a} for s, t, u, a in DEFAULT_REPORTS])
        if _count(con, "page_access") == 0:
            con.execute(text("INSERT INTO page_access (role, page_key) VALUES (:r, :p)"),
                        [{"r": r, "p": p} for r, pages in DEFAULT_ACCESS.items() for p in pages])
        for user, role, pw in config.demo_users():  # only created when missing, so Admin edits stick
            if con.execute(text("SELECT 1 FROM users WHERE username = :u"), {"u": user}).fetchone() is None:
                con.execute(
                    text("INSERT INTO users (username, role, password_hash, active) VALUES (:u, :r, :h, 1)"),
                    {"u": user, "r": role, "h": hash_password(pw)},
                )


def authenticate(username: str, password: str) -> str | None:
    """Return the role if credentials are valid, else None."""
    with connect() as con:
        row = con.execute(
            text("SELECT role, password_hash FROM users WHERE username = :u AND active = 1"),
            {"u": username.strip().lower()},
        ).fetchone()
    if row and verify_password(password, row[1]):
        return row[0]
    return None


def is_super(role: str) -> bool:
    with connect() as con:
        row = con.execute(text("SELECT is_super FROM roles WHERE name = :n"), {"n": role}).fetchone()
    return bool(row and row[0])


def get_access() -> dict[str, set[str]]:
    """Page keys per role. Super roles get every page. Only super roles ever get Admin."""
    with connect() as con:
        rows = con.execute(text("SELECT role, page_key FROM page_access")).fetchall()
        supers = [r[0] for r in con.execute(text("SELECT name FROM roles WHERE is_super = 1"))]
    access: dict[str, set[str]] = {}
    for role, page in rows:
        if page != "admin":
            access.setdefault(role, set()).add(page)
    for role in supers:
        access[role] = set(PAGES)
    return access


def allowed_pages(role: str) -> list[str]:
    allowed = get_access().get(role, set())
    return [k for k in PAGES if k in allowed]


def allowed_reports(role: str) -> pd.DataFrame:
    reports = query("SELECT slug, title, url FROM reports WHERE active = 1 ORDER BY title")
    if is_super(role):
        return reports
    granted = get_access().get(role, set())
    return reports[reports.slug.map(lambda s: f"report:{s}" in granted)]


def save_access(matrix: dict[str, set[str]]) -> None:
    """Replace the page grants of the roles in `matrix`. Other roles are untouched."""
    with connect() as con:
        for role, pages in matrix.items():
            con.execute(text("DELETE FROM page_access WHERE role = :r"), {"r": role})
            if pages:
                con.execute(text("INSERT INTO page_access (role, page_key) VALUES (:r, :p)"),
                            [{"r": role, "p": p} for p in pages])


# Admin changes. Each raises ValueError with a plain message when the input is not acceptable.
USERNAME_OK = re.compile(r"^[a-z0-9._-]{3,30}$")


def add_user(username: str, role: str, password: str) -> None:
    username = username.strip().lower()
    if not USERNAME_OK.match(username):
        raise ValueError("Username needs 3 to 30 letters, numbers, dots, dashes or underscores.")
    if len(password) < 8:
        raise ValueError("Password needs at least 8 characters.")
    with connect() as con:
        if con.execute(text("SELECT 1 FROM users WHERE username = :u"), {"u": username}).fetchone():
            raise ValueError("That username already exists.")
        con.execute(text("INSERT INTO users (username, role, password_hash, active) VALUES (:u, :r, :h, 1)"),
                    {"u": username, "r": role, "h": hash_password(password)})


def update_user(username: str, role: str, active: bool) -> None:
    with connect() as con:
        con.execute(text("UPDATE users SET role = :r, active = :a WHERE username = :u"),
                    {"r": role, "a": int(active), "u": username})


def set_password(username: str, password: str) -> None:
    if len(password) < 8:
        raise ValueError("Password needs at least 8 characters.")
    with connect() as con:
        con.execute(text("UPDATE users SET password_hash = :h WHERE username = :u"),
                    {"h": hash_password(password), "u": username})


def add_role(name: str, description: str, super_role: bool) -> None:
    name = name.strip()
    if not 2 <= len(name) <= 30:
        raise ValueError("Role name needs 2 to 30 characters.")
    with connect() as con:
        if con.execute(text("SELECT 1 FROM roles WHERE name = :n"), {"n": name}).fetchone():
            raise ValueError("That role already exists.")
        con.execute(text("INSERT INTO roles (name, description, is_super) VALUES (:n, :d, :s)"),
                    {"n": name, "d": description.strip(), "s": int(super_role)})


def delete_role(name: str) -> None:
    with connect() as con:
        if con.execute(text("SELECT 1 FROM users WHERE role = :n"), {"n": name}).fetchone():
            raise ValueError("This role still has users. Move them to another role first.")
        supers = [r[0] for r in con.execute(text("SELECT name FROM roles WHERE is_super = 1"))]
        if supers == [name]:
            raise ValueError("You cannot delete the only Super role.")
        con.execute(text("DELETE FROM page_access WHERE role = :n"), {"n": name})
        con.execute(text("DELETE FROM roles WHERE name = :n"), {"n": name})


def save_reports(df: pd.DataFrame) -> None:
    """Replace the report list. Only https links are accepted."""
    clean = lambda v: "" if pd.isna(v) else str(v).strip()
    rows = []
    for r in df.itertuples(index=False):
        slug, title, url = clean(r.slug).lower(), clean(r.title), clean(r.url)
        if not (slug or title or url):
            continue
        if not re.match(r"^[a-z0-9-]+$", slug):
            raise ValueError(f"Slug '{slug}' needs lower case letters, numbers and dashes only.")
        if not title or not url.startswith("https://"):
            raise ValueError(f"Report '{slug}' needs a title and a link that starts with https://")
        rows.append({"s": slug, "t": title, "u": url, "a": 0 if (not pd.isna(r.active) and not r.active) else 1})
    if len({r["s"] for r in rows}) != len(rows):
        raise ValueError("Each report needs its own slug.")
    with connect() as con:
        con.execute(text("DELETE FROM reports"))
        if rows:
            con.execute(text("INSERT INTO reports (slug, title, url, active) VALUES (:s, :t, :u, :a)"), rows)


def table_counts() -> dict[str, int]:
    with connect() as con:
        return {t: con.execute(text(f"SELECT COUNT(*) FROM {t}")).scalar() for t in DATA_TABLES}
