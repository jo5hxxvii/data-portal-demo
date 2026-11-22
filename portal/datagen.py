"""Synthetic data for Demo Capital. Everything here is generated with Faker."""
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
from faker import Faker

from . import config

SEGMENTS = ["Retail", "Premium", "Institutional"]
CHANNELS = ["Bank transfer", "Card", "Wire", "Mobile app"]
PRODUCTS = ["Fixed Deposit", "Treasury Bill", "Bond", "Commercial Paper"]
PLAN_NAMES = ["Rainy Day", "School Fees", "Rent", "Holiday", "New Car", "Wedding"]
TICKERS = {"NVLX": 42.0, "BRTN": 18.5, "KOLA": 96.2, "ZENT": 7.8, "PAXO": 55.4, "MIRA": 23.1}  # made up
SEGMENT_SCALE = {"Retail": 2_000, "Premium": 9_000, "Institutional": 40_000}


def generate(seed: int | None = None) -> dict[str, pd.DataFrame]:
    seed = config.FAKER_SEED if seed is None else seed
    fake = Faker("en_GB")
    Faker.seed(seed)
    rng = np.random.default_rng(seed)
    end = datetime(2026, 11, 20, 18, 0)
    start = end - timedelta(days=365)

    # Customers
    rows = []
    for i in range(config.NUM_CUSTOMERS):
        seg = rng.choice(SEGMENTS, p=[0.7, 0.25, 0.05])
        rows.append(
            {
                "customer_id": f"C{i + 1:05d}",
                "name": fake.name(),
                "email": f"customer{i + 1}@example.com",
                "country": fake.current_country(),
                "segment": seg,
                "joined_at": fake.date_time_between(start - timedelta(days=700), start).date().isoformat(),
            }
        )
    customers = pd.DataFrame(rows)
    scale = customers["segment"].map(SEGMENT_SCALE).to_numpy()

    # Transactions (chronological so wallets never go negative)
    n = config.NUM_TRANSACTIONS
    ts = sorted(start + timedelta(seconds=int(s)) for s in rng.integers(0, 365 * 86400, n))
    opening = (scale * rng.uniform(2, 8, len(customers))).round(2)
    balances = dict(zip(customers["customer_id"], opening))
    txns = []
    for k, t in enumerate(ts):
        ci = int(rng.integers(0, len(customers)))
        cid = customers.at[ci, "customer_id"]
        base = scale[ci]
        kind = rng.choice(["deposit", "withdrawal"], p=[0.58, 0.42])
        amount = round(float(rng.lognormal(np.log(base * 0.3), 0.8)), 2)
        status = rng.choice(["completed", "failed", "pending"], p=[0.93, 0.05, 0.02])
        if kind == "withdrawal" and amount > balances[cid]:
            kind, amount = "deposit", amount
        txns.append(
            {
                "txn_id": f"T{k + 1:07d}",
                "reference": f"REF-{k + 1:07d}",
                "customer_id": cid,
                "type": kind,
                "amount": amount,
                "currency": "USD",
                "channel": str(rng.choice(CHANNELS)),
                "status": str(status),
                "created_at": t,
            }
        )
        if status == "completed":
            balances[cid] += amount if kind == "deposit" else -amount
    txns = pd.DataFrame(txns)

    # Inject patterns the Exceptions page looks for
    nxt = len(txns)
    extra = []

    def add(src, **kw):
        nonlocal nxt
        nxt += 1
        row = src.to_dict()
        row.update(txn_id=f"T{nxt:07d}", reference=f"REF-{nxt:07d}", **kw)
        extra.append(row)

    completed = txns[(txns.status == "completed") & (txns.type == "deposit")]
    for _, src in completed.sample(25, random_state=seed).iterrows():  # duplicates
        add(src, created_at=src.created_at + timedelta(minutes=int(rng.integers(1, 8))))
    for _, src in completed.sample(30, random_state=seed + 1).iterrows():  # failed then retried
        add(src, status="failed", created_at=src.created_at - timedelta(minutes=int(rng.integers(5, 40))))
    big_ids = customers[customers.segment == "Institutional"]["customer_id"].tolist() or customers.customer_id.tolist()
    for _ in range(12):  # large amounts
        src = completed.sample(1, random_state=int(rng.integers(0, 10**6))).iloc[0]
        add(src, customer_id=str(rng.choice(big_ids)), amount=round(float(rng.uniform(60_000, 400_000)), 2))
    txns = pd.concat([txns, pd.DataFrame(extra)], ignore_index=True).sort_values("created_at").reset_index(drop=True)

    # Recompute wallets from completed flows
    done = txns[txns.status == "completed"].copy()
    done["signed"] = np.where(done.type == "deposit", done.amount, -done.amount)
    net = done.groupby("customer_id")["signed"].sum()
    wallets = customers[["customer_id"]].copy()
    wallets["opening_balance"] = opening
    wallets["balance"] = (wallets.opening_balance + wallets.customer_id.map(net).fillna(0)).round(2)
    wallets["currency"] = "USD"

    # Two sources for reconciliation
    ledger = done[["reference", "customer_id", "type", "amount", "created_at"]].rename(
        columns={"created_at": "posted_at"}
    ).reset_index(drop=True)
    ledger.insert(0, "ledger_id", [f"L{i + 1:07d}" for i in range(len(ledger))])

    proc = ledger[["reference", "type", "amount", "posted_at"]].copy()
    r = rng.random(len(proc))
    proc = proc[r >= 0.025]  # ~2.5% never reached the processor
    mism = rng.random(len(proc)) < 0.03  # ~3% amount mismatch
    delta = rng.choice([-1, 1], mism.sum()) * np.round(rng.uniform(0.5, 120, mism.sum()), 2)
    proc.loc[mism, "amount"] = (proc.loc[mism, "amount"] + delta).round(2)
    proc["settled_at"] = proc.pop("posted_at") + pd.to_timedelta(rng.integers(1, 48, len(proc)), unit="h")
    orphans = []
    for j in range(25):  # processor-only records
        orphans.append(
            {
                "reference": f"EXT-{j + 1:05d}",
                "type": str(rng.choice(["deposit", "withdrawal"])),
                "amount": round(float(rng.uniform(100, 9000)), 2),
                "settled_at": end - timedelta(days=int(rng.integers(0, 300))),
            }
        )
    proc = pd.concat([proc, pd.DataFrame(orphans)], ignore_index=True)
    proc.insert(0, "processor_id", [f"P{i + 1:07d}" for i in range(len(proc))])

    # Product data. Own random generator, so the data above never changes.
    prng = np.random.default_rng(seed + 100)
    ids = customers["customer_id"].to_numpy()
    seg_scale = dict(zip(customers.customer_id, scale))
    today = end.date()

    mats = []
    for i in range(400):
        cid = str(prng.choice(ids))
        start_d = today - timedelta(days=int(prng.integers(0, 300)))
        due = start_d + timedelta(days=int(prng.choice([90, 180, 270, 365])))
        mats.append(
            {
                "maturity_id": f"M{i + 1:05d}",
                "customer_id": cid,
                "product": str(prng.choice(PRODUCTS)),
                "principal": round(float(seg_scale[cid] * prng.uniform(0.5, 6)), 2),
                "rate_pct": round(float(prng.uniform(8, 22)), 2),
                "start_date": start_d.isoformat(),
                "maturity_date": due.isoformat(),
                "status": "Matured" if due <= today else "Active",
            }
        )

    plans = []
    for i in range(150):
        cid = str(prng.choice(ids))
        status = str(prng.choice(["Active", "Completed", "Failed"], p=[0.7, 0.2, 0.1]))
        target = round(float(seg_scale[cid] * prng.uniform(0.5, 4)), 2)
        share = {"Completed": 1.0, "Failed": prng.uniform(0, 0.3), "Active": prng.uniform(0.05, 0.95)}[status]
        plans.append(
            {
                "plan_id": f"S{i + 1:05d}",
                "customer_id": cid,
                "plan_name": str(prng.choice(PLAN_NAMES)),
                "frequency": str(prng.choice(["Daily", "Weekly", "Monthly"])),
                "target_amount": target,
                "saved_amount": round(float(target * share), 2),
                "start_date": (today - timedelta(days=int(prng.integers(10, 400)))).isoformat(),
                "status": status,
            }
        )

    snaps = [today - timedelta(days=d) for d in range(1, 8)]  # the last 7 days up to yesterday
    paths = {t: p * np.cumprod(1 + prng.normal(0, 0.015, len(snaps))) for t, p in TICKERS.items()}
    holdings = []
    for cid in prng.choice(ids, 80, replace=False):
        for tk in prng.choice(list(TICKERS), int(prng.integers(2, 5)), replace=False):
            units = int(prng.integers(10, 2000))
            for k, d in enumerate(snaps):
                holdings.append(
                    {"snapshot_date": d.isoformat(), "customer_id": str(cid), "ticker": str(tk),
                     "units": units, "price": round(float(paths[str(tk)][k]), 2)}
                )

    return {
        "customers": customers,
        "wallets": wallets,
        "transactions": txns,
        "ledger_entries": ledger,
        "processor_entries": proc,
        "maturities": pd.DataFrame(mats),
        "savings_plans": pd.DataFrame(plans),
        "equity_holdings": pd.DataFrame(holdings),
    }
