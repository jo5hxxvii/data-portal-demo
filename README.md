# Demo Capital Data Portal

An internal data portal for a fictional investment company, built with Streamlit, SQLite and Plotly. It shows a typical finance operations workflow: reporting, reconciliation, exception review and role-based access.

Everything is synthetic. "Demo Capital" is not a real company. All customers, transactions and balances are generated with [Faker](https://faker.readthedocs.io/). There are no real names, logos or credentials anywhere in this repo.

## Screenshots

| Login | Dashboard |
|---|---|
| ![Login](docs/screenshots/login.png) | ![Dashboard](docs/screenshots/dashboard.png) |

| Reconciliation | Exceptions |
|---|---|
| ![Reconciliation](docs/screenshots/reconciliation.png) | ![Exceptions](docs/screenshots/exceptions.png) |

| Admin |
|---|
| ![Admin](docs/screenshots/admin.png) |

> Placeholders. Run the app, take the shots and save them in `docs/screenshots/`.

## What it does

**Login with three demo roles.** Admin, Finance and Operations. The credentials are shown on the login page. Passwords are stored as salted PBKDF2 hashes. Each role only sees the pages it is allowed to open.

**Dashboard.** Total AUM, inflows, outflows and active customers for a chosen period, with a comparison to the previous period. Plotly charts show AUM over time, weekly inflows and outflows, weekly net flow, and AUM by segment and country.

**Reconciliation.** Compares two synthetic sources, the internal ledger and a payment processor feed, matched on reference. Every record lands in one of four groups: matched, amount mismatch, missing in processor, missing in ledger. The mismatch tolerance is adjustable and each view downloads as CSV.

**Exceptions.** Flags suspicious transactions by rule, with filters for rule, type, status, amount, date and customer, plus CSV export.
- Duplicate: same customer, type and amount within a short window
- Large amount: at or above a threshold
- Failed then retried: a failed attempt followed by a successful one with the same details

**Data Lookup.** Pages for looking up records, all on synthetic data. Each lookup is logged and downloads as CSV.
- Wallet Transactions: every transaction in a date range (up to 5 days)
- Customer Transactions: paste one or many customer IDs to see wallets and transactions
- Account Statement: one customer, a date range (up to 5 days), with opening, running and closing balance
- Maturities: investments reaching maturity in a date range, by product, with the payout due
- Savings Plans: plans that have not failed, with progress bars
- Equity Portfolios: holdings on one snapshot date, with value by ticker (tickers and prices are made up)

**Reports.** Embeds report links (like public Power BI links) that Admin adds. Each role only sees the reports ticked for it. The two reports that come with the demo are sample links to placeholder sites, so replace them in Admin.

**Execute Query.** A SQL box for Admin. It allows one SELECT on the data tables, shows 20 rows, blocks restricted columns (`email`) and blocks `SELECT *` on customers. Everything run or blocked is logged. The check in `portal/query_guard.py` is a safety net, so with a real database also use a read only login. Run `PYTHONPATH=. pytest tests` after changing it.

**Admin.** Four tabs. Users: add users, change roles, deactivate, reset passwords. Roles and pages: create roles, tick which pages and reports each role can open, delete empty roles. Reports: manage the report links. Data: row counts and a reset button. A Super role opens everything. You cannot change your own role, deactivate yourself, delete a role that has users, or delete the only Super role. Demo users are only created when missing, so your edits are kept.

People are signed out after 60 idle minutes (`IDLE_TIMEOUT_MINUTES`).

**Activity Log.** Records sign-ins (including failed ones), sign-outs, page views, CSV downloads, access changes and data resets, with the user, role, level, area and detail. Filter by date, user, level, area and text, and download the view. Times are UTC. The log is stored in the `audit_log` table and cannot be edited or cleared from the portal.

Default access:

| Role | Dashboard | Reconciliation | Exceptions | Admin |
|---|---|---|---|---|
| Admin | yes | yes | yes | yes |
| Finance | yes | yes | no | no |
| Operations | yes | no | yes | no |

## Setup

You need Python 3.10 or newer. The database is a local SQLite file, so there is nothing else to install.

### 1. Install

```bash
git clone <your-repo-url>
cd data-portal-demo
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure

```bash
cp .env.example .env
```

The defaults work as they are. The app creates `data/demo_capital.db` and generates the demo data on first start.

### 3. Run

```bash
streamlit run app.py
```

Open http://localhost:8501 and sign in with a demo account from the login page.

## Database

The app talks to the database through SQLAlchemy, so the engine is set by one variable:

```
DATABASE_URL=sqlite:///data/demo_capital.db
```

SQLite is the default and needs no server or extra driver. The schema in `db/schema.sql` uses plain SQL types and the app has no engine-specific code, so other engines work by installing their driver and changing the URL. For example, Postgres:

```
DATABASE_URL=postgresql+psycopg2://user:password@localhost:5432/demo_capital
```

`db/seed.sql` is an optional Postgres-only dump (it uses `BEGIN` and `COMMIT`). Load it with `psql -f db/schema.sql -f db/seed.sql` if you want it, otherwise the app seeds itself. To reset the SQLite data, delete `data/demo_capital.db`.

| File | Purpose |
|---|---|
| `db/schema.sql` | Table and index definitions |
| `db/seed.sql` | Synthetic data as plain INSERT statements |
| `scripts/generate_seed_sql.py` | Rebuilds `db/seed.sql` from the Faker generator |

Demo users are not in `seed.sql`. The app creates them on start from the passwords in `.env`, so no passwords are stored in the repo.

To rebuild the seed file after changing the generator or seed value:

```bash
python scripts/generate_seed_sql.py
```

To regenerate the data in a running app, use the button on the Admin page.

## Configuration

All settings are environment variables. See `.env.example`.

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | `sqlite:///data/demo_capital.db` | Database connection |
| `FAKER_SEED` | `2026` | Makes the data repeatable |
| `NUM_CUSTOMERS` | `300` | Customers to generate |
| `NUM_TRANSACTIONS` | `6000` | Base transactions to generate |
| `IDLE_TIMEOUT_MINUTES` | `60` | Sign out after this many idle minutes |
| `DEMO_*_PASSWORD` | see file | Demo login passwords |
| `LARGE_TXN_THRESHOLD` | `50000` | Large amount rule |
| `DUPLICATE_WINDOW_MINUTES` | `10` | Duplicate rule window |
| `RETRY_WINDOW_MINUTES` | `60` | Failed then retried window |
| `RECON_AMOUNT_TOLERANCE` | `0.01` | Default mismatch tolerance |

## Project structure

```
app.py                      Entry point: login and role-based navigation
views/                      One file per page
portal/
  config.py                 Environment settings
  db.py                     Database access, seeding, role access
  datagen.py                Faker data generation
  rules.py                  Reconciliation and exception logic
  auth.py                   Password hashing
  audit.py                  Writes and reads the activity log
  query_guard.py            Checks the SQL on the Execute Query page
  pages_registry.py         Page list and default access
  ui.py                     Shared styling and chart helpers
db/
  schema.sql                Tables and indexes
  seed.sql                  Synthetic seed data
scripts/
  generate_seed_sql.py      Builds db/seed.sql
tests/
  test_query_guard.py       Cases the query check must allow or block
```

## Notes

- This is a portfolio demo. The login is deliberately simple and is not meant to protect real data. The database user and password in the defaults are for local use only.
- The data has known problems on purpose: about 2.5% of ledger entries are missing from the processor, about 3% have amount mismatches, and 25 processor records have no ledger entry. Duplicate, large and retry cases are added so the Exceptions page has something to find.

## License

MIT
