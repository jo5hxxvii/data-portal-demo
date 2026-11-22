import streamlit as st

from portal import audit, db
from portal.ui import download_csv, page_header, parse_ids, require_page

require_page("customer_transactions")
page_header("Customer Transactions", "Paste one or many customer IDs to see their wallets and every transaction.")

raw = st.text_area("Customer IDs", placeholder="C00001, C00002\nC00003", help="Separate IDs with commas, spaces or new lines.")
ids = parse_ids(raw)
if not ids:
    st.info("Paste at least one customer ID, for example C00001.")
    st.stop()

people = db.query(
    "SELECT c.customer_id, c.name, c.segment, c.country, w.balance, w.currency "
    "FROM customers c JOIN wallets w ON w.customer_id = c.customer_id WHERE c.customer_id IN :ids ORDER BY c.customer_id",
    {"ids": ids},
)
txns = db.query(
    "SELECT txn_id, created_at, customer_id, type, amount, currency, channel, status "
    "FROM transactions WHERE customer_id IN :ids ORDER BY created_at DESC LIMIT 5000",
    {"ids": ids},
)
audit.log_once("customer_txn", "lookup", f"customer transactions for {len(ids)} IDs: {len(txns):,} rows", area="Lookup")

missing = sorted(set(ids) - set(people.customer_id))
if missing:
    st.warning(f"Not found: {', '.join(missing[:20])}")

st.subheader("Customers")
st.dataframe(people, width="stretch", hide_index=True,
             column_config={"balance": st.column_config.NumberColumn(format="$%.2f")})
st.subheader(f"Transactions ({len(txns):,})")
st.dataframe(txns, width="stretch", hide_index=True, height=420,
             column_config={"amount": st.column_config.NumberColumn(format="$%.2f")})
download_csv("Download transactions (CSV)", txns, "customer_transactions.csv")
