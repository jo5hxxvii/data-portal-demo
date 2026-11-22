# Demo Capital Data Portal

An internal data portal for a fictional investment company, built with Streamlit, PostgreSQL and Plotly. It shows a typical finance operations workflow: reporting, reconciliation, exception review and role-based access.

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

**Admin.** A role by page grid that controls who sees what. It is stored in the database and takes effect on the next click. The Admin role always keeps the Admin page so nobody gets locked out.

Default access:

| Role | Dashboard | Reconciliation | Exceptions | Admin |
|---|---|---|---|---|
| Admin | yes | yes | yes | yes |
| Finance | yes | yes | no | no |
| Operations | yes | no | yes | no |

## Setup

You need Python 3.10 or newer and a PostgreSQL database. The quickest way to get one is Docker.

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

The defaults match the Docker setup below, so you can leave `.env` as it is.

### 3. Start Postgres

With Docker:

```bash
docker compose up -d
```

On first start the container loads `db/schema.sql` and `db/seed.sql`, so the data is ready straight away.

Without Docker, create a database and user yourself, then load the two files:

```bash
psql -h localhost -U demo -d demo_capital -f db/schema.sql -f db/seed.sql
```

If you skip seeding, the app creates the tables and generates the same data on first start.

### 4. Run

```bash
streamlit run app.py
```

Open http://localhost:8501 and sign in with a demo account from the login page.

## Database

The app talks to the database through SQLAlchemy, so the engine is set by one variable:

```
DATABASE_URL=postgresql+psycopg2://demo:demo@localhost:5432/demo_capital
```

This project is built for Postgres, but the engine can be swapped. The schema in `db/schema.sql` uses plain SQL types, and the app has no engine-specific code. To try another engine, install its driver and change the URL. For example, SQLite needs no extra driver:

```
DATABASE_URL=sqlite:///data/demo_capital.db
```

MySQL or SQL Server would work the same way with their drivers. Only `db/seed.sql` is written for Postgres, because of the `BEGIN` and `COMMIT` wrapper. Other engines can skip it, since the app seeds itself.

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
| `DATABASE_URL` | local Postgres | Database connection |
| `FAKER_SEED` | `2026` | Makes the data repeatable |
| `NUM_CUSTOMERS` | `300` | Customers to generate |
| `NUM_TRANSACTIONS` | `6000` | Base transactions to generate |
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
  pages_registry.py         Page list and default access
  ui.py                     Shared styling and chart helpers
db/
  schema.sql                Tables and indexes
  seed.sql                  Synthetic seed data
scripts/
  generate_seed_sql.py      Builds db/seed.sql
docker-compose.yml          Local Postgres
```

## Notes

- This is a portfolio demo. The login is deliberately simple and is not meant to protect real data. The database user and password in the defaults are for local use only.
- The data has known problems on purpose: about 2.5% of ledger entries are missing from the processor, about 3% have amount mismatches, and 25 processor records have no ledger entry. Duplicate, large and retry cases are added so the Exceptions page has something to find.

## License

MIT
