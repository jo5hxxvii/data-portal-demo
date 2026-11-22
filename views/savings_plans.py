import streamlit as st

from portal import audit, db
from portal.ui import compact, download_csv, page_header, require_page

require_page("savings_plans")
page_header("Savings Plans", "All plans that have not failed, with progress towards each target.")

df = db.query(
    "SELECT p.plan_id, p.customer_id, c.name, p.plan_name, p.frequency, p.target_amount, p.saved_amount, p.start_date, p.status "
    "FROM savings_plans p JOIN customers c ON c.customer_id = p.customer_id WHERE p.status <> 'Failed' ORDER BY p.start_date DESC"
)
with st.sidebar:
    st.subheader("Filters")
    status = st.multiselect("Status", sorted(df.status.unique()), default=sorted(df.status.unique()))
    freq = st.multiselect("Frequency", sorted(df.frequency.unique()), default=sorted(df.frequency.unique()))
view = df[df.status.isin(status) & df.frequency.isin(freq)].copy()
view["progress"] = (view.saved_amount / view.target_amount * 100).round(1)
audit.log_once("savings", "lookup", f"savings plans: {len(view):,} rows", area="Lookup")

c1, c2, c3 = st.columns(3)
c1.metric("Plans", f"{len(view):,}")
c2.metric("Saved so far", compact(view.saved_amount.sum()))
c3.metric("Target", compact(view.target_amount.sum()))
st.dataframe(view, width="stretch", hide_index=True, height=480,
             column_config={"target_amount": st.column_config.NumberColumn(format="$%.2f"),
                            "saved_amount": st.column_config.NumberColumn(format="$%.2f"),
                            "progress": st.column_config.ProgressColumn("Progress", format="%.0f%%", min_value=0, max_value=100)})
download_csv("Download (CSV)", view, "savings_plans.csv")
