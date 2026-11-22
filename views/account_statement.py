from datetime import timedelta

import numpy as np
import streamlit as st

from portal import audit, config, db
from portal.ui import download_csv, page_header, parse_ids, pick_range, require_page

require_page("account_statement")
page_header("Account Statement", f"Wallet statement with a running balance, up to {config.MAX_RANGE_DAYS} days at a time. Completed transactions only.")

ids = parse_ids(st.text_input("Customer ID", placeholder="C00001"), limit=1)
if not ids:
    st.info("Enter one customer ID, for example C00001.")
    st.stop()
cid = ids[0]
last = db.data_date()
d0, d1 = pick_range(last - timedelta(days=config.MAX_RANGE_DAYS - 1), last, config.MAX_RANGE_DAYS)

wallet = db.query(
    "SELECT c.name, w.opening_balance, w.currency FROM wallets w JOIN customers c ON c.customer_id = w.customer_id "
    "WHERE w.customer_id = :c", {"c": cid})
if wallet.empty:
    st.error(f"No wallet found for {cid}.")
    st.stop()

signed = "CASE WHEN type = 'deposit' THEN amount ELSE -amount END"
before = db.query(f"SELECT COALESCE(SUM({signed}), 0) AS s FROM transactions "
                  "WHERE customer_id = :c AND status = 'completed' AND created_at < :a", {"c": cid, "a": str(d0)})
opening = float(wallet.opening_balance[0] + before.s[0])
rows = db.query("SELECT txn_id, created_at, reference, type, amount, channel FROM transactions "
                "WHERE customer_id = :c AND status = 'completed' AND created_at >= :a AND created_at < :b ORDER BY created_at",
                {"c": cid, "a": str(d0), "b": str(d1 + timedelta(days=1))})
rows["balance"] = (opening + np.cumsum(np.where(rows.type == "deposit", rows.amount, -rows.amount))).round(2)
audit.log_once("statement", "lookup", f"statement {cid} {d0} to {d1}: {len(rows):,} rows", area="Lookup")

credits = rows[rows.type == "deposit"].amount.sum()
debits = rows[rows.type == "withdrawal"].amount.sum()
st.subheader(f"{wallet.name[0]} ({cid})")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Opening balance", f"${opening:,.2f}")
c2.metric("Credits", f"${credits:,.2f}")
c3.metric("Debits", f"${debits:,.2f}")
c4.metric("Closing balance", f"${opening + credits - debits:,.2f}")

st.dataframe(rows, width="stretch", hide_index=True, height=420,
             column_config={"amount": st.column_config.NumberColumn(format="$%.2f"),
                            "balance": st.column_config.NumberColumn(format="$%.2f")})
download_csv("Download statement (CSV)", rows, f"statement_{cid}_{d0}_{d1}.csv")
