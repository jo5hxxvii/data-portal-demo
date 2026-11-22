"""Write db/seed.sql from the Faker generator (same data the app seeds with).

Usage: python scripts/generate_seed_sql.py
"""
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from portal.datagen import generate  # noqa: E402
from portal.pages_registry import DEFAULT_ACCESS  # noqa: E402

BATCH = 500
ORDER = ["customers", "wallets", "transactions", "ledger_entries", "processor_entries"]


def lit(v) -> str:
    if isinstance(v, pd.Timestamp):
        return f"'{v:%Y-%m-%d %H:%M:%S}'"
    if isinstance(v, float):
        return f"{v:.2f}"
    if isinstance(v, (int,)):
        return str(v)
    return "'" + str(v).replace("'", "''") + "'"


def inserts(table: str, df: pd.DataFrame) -> list[str]:
    cols = ", ".join(df.columns)
    out = []
    for i in range(0, len(df), BATCH):
        rows = ",\n".join("  (" + ", ".join(lit(v) for v in r) + ")" for r in df.iloc[i : i + BATCH].itertuples(index=False))
        out.append(f"INSERT INTO {table} ({cols}) VALUES\n{rows};\n")
    return out


def main() -> None:
    data = generate()
    lines = [
        "-- Demo Capital Data Portal: synthetic seed data (generated with Faker)",
        "-- Regenerate with: python scripts/generate_seed_sql.py",
        "-- Run after db/schema.sql. Demo users are created by the app on start, not here,",
        "-- so no passwords live in this file.",
        "",
        "BEGIN;",
        "",
    ]
    lines += [f"DELETE FROM {t};" for t in reversed(ORDER)] + ["DELETE FROM page_access;", ""]
    for t in ORDER:
        lines.append(f"-- {t} ({len(data[t])} rows)")
        lines += inserts(t, data[t])
    lines.append("-- Default role access")
    vals = ",\n".join(f"  ('{r}', '{p}')" for r, pages in DEFAULT_ACCESS.items() for p in pages)
    lines += [f"INSERT INTO page_access (role, page_key) VALUES\n{vals};", "", "COMMIT;", ""]
    out = ROOT / "db" / "seed.sql"
    out.write_text("\n".join(lines))
    print(f"Wrote {out} ({out.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
