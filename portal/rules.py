"""Reconciliation and exception rules (pure pandas, no Streamlit)."""
import numpy as np
import pandas as pd

from . import config


def reconcile(ledger: pd.DataFrame, proc: pd.DataFrame, tol: float) -> pd.DataFrame:
    """Full outer join on reference. Adds a `result` column."""
    m = ledger.merge(proc, on="reference", how="outer", suffixes=("_ledger", "_processor"), indicator=True)
    m["difference"] = (m["amount_ledger"] - m["amount_processor"]).round(2)
    result = np.select(
        [
            m["_merge"] == "left_only",
            m["_merge"] == "right_only",
            m["difference"].abs() > tol,
        ],
        ["Missing in processor", "Missing in ledger", "Amount mismatch"],
        default="Matched",
    )
    m["result"] = result
    cols = [
        "reference", "result", "amount_ledger", "amount_processor", "difference",
        "type_ledger", "customer_id", "posted_at", "settled_at", "ledger_id", "processor_id",
    ]
    return m[cols].sort_values(["result", "reference"]).reset_index(drop=True)


def flag_exceptions(txns: pd.DataFrame) -> pd.DataFrame:
    """Return one row per flagged transaction with a `rules` column."""
    t = txns.copy()
    t["created_at"] = pd.to_datetime(t["created_at"])
    t = t.sort_values("created_at")
    flags = pd.DataFrame(False, index=t.index, columns=["Duplicate", "Large amount", "Failed then retried"])

    # Duplicate: same customer, type and amount within the window (flag the later one)
    key = ["customer_id", "type", "amount"]
    gap = t.groupby(key)["created_at"].diff()
    flags["Duplicate"] = gap.le(pd.Timedelta(minutes=config.DUPLICATE_WINDOW_MINUTES))

    flags["Large amount"] = t["amount"] >= config.LARGE_TXN_THRESHOLD

    # Failed then retried: a failed txn followed by a completed one with the same key inside the window
    failed = t[t.status == "failed"][key + ["created_at"]].rename(columns={"created_at": "failed_at"})
    done = t[t.status == "completed"][key + ["created_at"]].reset_index().rename(columns={"index": "idx"})
    pairs = failed.merge(done, on=key)
    delta = pairs["created_at"] - pairs["failed_at"]
    pairs = pairs[(delta > pd.Timedelta(0)) & (delta <= pd.Timedelta(minutes=config.RETRY_WINDOW_MINUTES))]
    # flag both the failed attempt and the retry
    failed_idx = failed.reset_index().merge(pairs[key + ["failed_at"]].drop_duplicates(), on=key + ["failed_at"])["index"]
    flags.loc[flags.index.isin(failed_idx), "Failed then retried"] = True
    flags.loc[flags.index.isin(pairs["idx"]), "Failed then retried"] = True

    hit = flags.any(axis=1)
    out = t[hit].copy()
    out["rules"] = flags[hit].apply(lambda r: ", ".join(r.index[r]), axis=1)
    return out.sort_values("created_at", ascending=False)
