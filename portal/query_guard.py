"""Safety net for the Execute Query page: one plain SELECT on the data tables, nothing sensitive.

check() returns None when the SQL is fine, or a short reason when it is not.
This is a second line of defence. With a real database, also run the page with a read only login.
"""
import sqlglot
from sqlglot import exp

ALLOWED_TABLES = {"customers", "wallets", "transactions", "ledger_entries", "processor_entries",
                  "maturities", "savings_plans", "equity_holdings"}
RESTRICTED_COLUMNS = {"email", "password_hash"}
NO_STAR_TABLES = {"customers"}  # SELECT * would pull the restricted columns
BLOCKED_FUNCTIONS = {"load_extension", "readfile", "writefile", "edit", "sleep", "randomblob", "zeroblob"}
BLOCKED_PREFIXES = ("pg_", "lo_", "dblink", "sqlite_", "pragma_")
WRITES = (exp.Insert, exp.Update, exp.Delete, exp.Merge, exp.Create, exp.Drop, exp.Alter, exp.Command, exp.Into)


def check(sql: str, dialect: str = "sqlite") -> str | None:
    if not sql.strip():
        return "Type a query first."
    if len(sql) > 5000:
        return "That query is too long."
    try:
        statements = [s for s in sqlglot.parse(sql, read=dialect) if s is not None]
    except sqlglot.errors.SqlglotError:
        return "I could not read that SQL. Check the syntax."
    if len(statements) != 1 or not isinstance(statements[0], exp.Select):
        return "Only one SELECT statement is allowed."
    root = statements[0]
    if root.find(*WRITES):
        return "Only reading data is allowed."

    ctes = {c.alias_or_name.lower() for c in root.find_all(exp.CTE)}
    tables = set()
    for t in root.find_all(exp.Table):
        if not isinstance(t.this, exp.Identifier) or t.args.get("db"):
            return "Only the portal data tables can be queried."
        name = t.name.lower()
        if name not in ctes:
            tables.add(name)
    unknown = tables - ALLOWED_TABLES
    if unknown:
        return f"Table not available: {sorted(unknown)[0]}"

    for col in root.find_all(exp.Column):
        if col.name.lower() in RESTRICTED_COLUMNS:
            return f"The column '{col.name}' is restricted."
    stars = [s for s in root.find_all(exp.Star) if not isinstance(s.parent, exp.Count)]
    if stars and tables & NO_STAR_TABLES:
        return "SELECT * is not allowed on customers. List the columns you need."

    for fn in root.find_all(exp.Anonymous):
        name = fn.name.lower()
        if name in BLOCKED_FUNCTIONS or name.startswith(BLOCKED_PREFIXES):
            return f"The function '{fn.name}' is not allowed."
    return None
