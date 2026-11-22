from datetime import timedelta

import streamlit as st

from portal import audit, config, db
from portal.ui import download_csv, page_header, pick_range, require_page

require_page("wallet_transactions")
page_header("Wallet Transactions", f"Every wallet transaction in a date range, up to {config.MAX_RANGE_DAYS} days at a time.")

last = db.data_date()
d0, d1 = pick_range(last - timedelta(days=config.MAX_RANGE_DAYS - 1), last, config.MAX_RANGE_DAYS)

df = db.query(
    "SELECT t.txn_id, t.created_at, t.customer_id, c.name, t.type, t.amount, t.currency, t.channel, t.status "
    "FROM transactions t JOIN customers c ON c.customer_id = t.customer_id "
    "WHERE t.created_at >= :a AND t.created_at < :b ORDER BY t.created_at",
    {"a": str(d0), "b": str(d1 + timedelta(days=1))},
)
audit.log_once("wallet_txn", "lookup", f"wallet transactions {d0} to {d1}: {len(df):,} rows", area="Lookup")

done = df[df.status == "completed"]
c1, c2, c3, c4 = st.columns(4)
c1.metric("Transactions", f"{len(df):,}")
c2.metric("Deposits (completed)", f"${done[done.type == 'deposit'].amount.sum():,.0f}")
c3.metric("Withdrawals (completed)", f"${done[done.type == 'withdrawal'].amount.sum():,.0f}")
c4.metric("Failed", f"{(df.status == 'failed').sum():,}")

st.dataframe(df, width="stretch", hide_index=True, height=480,
             column_config={"amount": st.column_config.NumberColumn(format="$%.2f")})
download_csv("Download (CSV)", df, f"wallet_transactions_{d0}_{d1}.csv")
