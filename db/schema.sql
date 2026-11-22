-- Demo Capital Data Portal: schema
-- Written for PostgreSQL. Plain SQL types only, so it also runs on SQLite.

CREATE TABLE IF NOT EXISTS customers (
    customer_id  TEXT PRIMARY KEY,
    name         TEXT NOT NULL,
    email        TEXT NOT NULL,
    country      TEXT NOT NULL,
    segment      TEXT NOT NULL,
    joined_at    DATE NOT NULL
);

CREATE TABLE IF NOT EXISTS wallets (
    customer_id      TEXT PRIMARY KEY REFERENCES customers (customer_id),
    opening_balance  NUMERIC(16, 2) NOT NULL,
    balance          NUMERIC(16, 2) NOT NULL,
    currency         TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS transactions (
    txn_id       TEXT PRIMARY KEY,
    reference    TEXT NOT NULL UNIQUE,
    customer_id  TEXT NOT NULL REFERENCES customers (customer_id),
    type         TEXT NOT NULL,
    amount       NUMERIC(16, 2) NOT NULL,
    currency     TEXT NOT NULL,
    channel      TEXT NOT NULL,
    status       TEXT NOT NULL,
    created_at   TIMESTAMP NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_transactions_customer ON transactions (customer_id);
CREATE INDEX IF NOT EXISTS ix_transactions_created  ON transactions (created_at);

-- Internal ledger (source A for reconciliation)
CREATE TABLE IF NOT EXISTS ledger_entries (
    ledger_id    TEXT PRIMARY KEY,
    reference    TEXT NOT NULL,
    customer_id  TEXT NOT NULL,
    type         TEXT NOT NULL,
    amount       NUMERIC(16, 2) NOT NULL,
    posted_at    TIMESTAMP NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_ledger_reference ON ledger_entries (reference);

-- Payment processor feed (source B for reconciliation)
CREATE TABLE IF NOT EXISTS processor_entries (
    processor_id TEXT PRIMARY KEY,
    reference    TEXT NOT NULL,
    type         TEXT NOT NULL,
    amount       NUMERIC(16, 2) NOT NULL,
    settled_at   TIMESTAMP NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_processor_reference ON processor_entries (reference);

-- Portal access control
CREATE TABLE IF NOT EXISTS users (
    username       TEXT PRIMARY KEY,
    role           TEXT NOT NULL,
    password_hash  TEXT NOT NULL,
    active         INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS roles (
    name         TEXT PRIMARY KEY,
    description  TEXT NOT NULL,
    is_super     INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS page_access (
    role      TEXT NOT NULL,
    page_key  TEXT NOT NULL,
    PRIMARY KEY (role, page_key)
);

-- Activity log: who did what, and when (times are UTC)
CREATE TABLE IF NOT EXISTS audit_log (
    ts         TIMESTAMP NOT NULL,
    username   TEXT NOT NULL,
    role       TEXT NOT NULL,
    level      TEXT NOT NULL,
    area       TEXT NOT NULL,
    action     TEXT NOT NULL,
    detail     TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_audit_ts ON audit_log (ts);

-- Power BI style report links shown on the Reports page
CREATE TABLE IF NOT EXISTS reports (
    slug    TEXT PRIMARY KEY,
    title   TEXT NOT NULL,
    url     TEXT NOT NULL,
    active  INTEGER NOT NULL DEFAULT 1
);

-- Product data (synthetic)
CREATE TABLE IF NOT EXISTS maturities (
    maturity_id    TEXT PRIMARY KEY,
    customer_id    TEXT NOT NULL,
    product        TEXT NOT NULL,
    principal      NUMERIC(16, 2) NOT NULL,
    rate_pct       NUMERIC(5, 2) NOT NULL,
    start_date     DATE NOT NULL,
    maturity_date  DATE NOT NULL,
    status         TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_maturities_date ON maturities (maturity_date);

CREATE TABLE IF NOT EXISTS savings_plans (
    plan_id        TEXT PRIMARY KEY,
    customer_id    TEXT NOT NULL,
    plan_name      TEXT NOT NULL,
    frequency      TEXT NOT NULL,
    target_amount  NUMERIC(16, 2) NOT NULL,
    saved_amount   NUMERIC(16, 2) NOT NULL,
    start_date     DATE NOT NULL,
    status         TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS equity_holdings (
    snapshot_date  DATE NOT NULL,
    customer_id    TEXT NOT NULL,
    ticker         TEXT NOT NULL,
    units          INTEGER NOT NULL,
    price          NUMERIC(16, 2) NOT NULL,
    PRIMARY KEY (snapshot_date, customer_id, ticker)
);
