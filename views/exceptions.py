import streamlit as st

from portal import config, db
from portal.rules import flag_exceptions
from portal.ui import compact, download_csv, page_header, require_page

require_page("exceptions")
page_header("Exceptions", "Transactions flagged by rule. Review and filter below.")


@st.cache_data(ttl=300)
def load():
    t = db.read_table("transactions")
    c = db.read_table("customers")[["customer_id", "name", "segment"]]
    return flag_exceptions(t).merge(c, on="customer_id", how="left")


flagged = load()
rules = ["Duplicate", "Large amount", "Failed then retried"]
with st.sidebar:
    st.subheader("Filters")
    pick = st.multiselect("Rule", rules, default=rules)
    types = st.multiselect("Type", ["deposit", "withdrawal"], default=["deposit", "withdrawal"])
    statuses = st.multiselect("Status", sorted(flagged.status.unique()), default=sorted(flagged.status.unique()))
    lo, hi = float(flagged.amount.min()), float(flagged.amount.max())
    amt = st.slider("Amount range ($)", lo, hi, (lo, hi))
    d0, d1 = flagged.created_at.min().date(), flagged.created_at.max().date()
    dates = st.date_input("Date range", (d0, d1), min_value=d0, max_value=d1)
    cust = st.text_input("Customer ID or name")

view = flagged[flagged.rules.apply(lambda r: any(p in r for p in pick))]
view = view[view.type.isin(types) & view.status.isin(statuses) & view.amount.between(*amt)]
if len(dates) == 2:
    view = view[(view.created_at.dt.date >= dates[0]) & (view.created_at.dt.date <= dates[1])]
if cust:
    view = view[view.customer_id.str.contains(cust, case=False) | view.name.str.contains(cust, case=False, na=False)]

c1, c2, c3, c4 = st.columns(4)
c1.metric("Flagged transactions", f"{len(view):,}")
c2.metric("Duplicates", f"{view.rules.str.contains('Duplicate').sum():,}")
c3.metric(f"Large (≥ {compact(config.LARGE_TXN_THRESHOLD)})", f"{view.rules.str.contains('Large').sum():,}")
c4.metric("Failed then retried", f"{view.rules.str.contains('retried').sum():,}")

with st.expander("How the rules work"):
    st.markdown(
        f"- **Duplicate**: same customer, type and amount within {config.DUPLICATE_WINDOW_MINUTES} minutes.\n"
        f"- **Large amount**: amount of {compact(config.LARGE_TXN_THRESHOLD)} or more.\n"
        f"- **Failed then retried**: a failed attempt followed by a completed one with the same customer, "
        f"type and amount within {config.RETRY_WINDOW_MINUTES} minutes. Both rows are flagged."
    )

cols = ["txn_id", "created_at", "customer_id", "name", "segment", "type", "amount", "status", "channel", "rules"]
st.dataframe(view[cols], width="stretch", hide_index=True, height=480,
             column_config={"amount": st.column_config.NumberColumn(format="$%.2f")})
download_csv("Download filtered exceptions (CSV)", view[cols], "exceptions.csv")
