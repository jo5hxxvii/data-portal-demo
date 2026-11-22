"""Synthetic data for Demo Capital. Everything here is generated with Faker."""
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
from faker import Faker

from . import config

SEGMENTS = ["Retail", "Premium", "Institutional"]
CHANNELS = ["Bank transfer", "Card", "Wire", "Mobile app"]
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

    return {
        "customers": customers,
        "wallets": wallets,
        "transactions": txns,
        "ledger_entries": ledger,
        "processor_entries": proc,
    }
