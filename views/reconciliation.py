import streamlit as st

from portal import config, db
from portal.rules import reconcile
from portal.ui import compact, page_header, require_page

require_page("reconciliation")
page_header("Reconciliation", "Internal ledger compared with the payment processor, matched on reference.")


@st.cache_data(ttl=300)
def load():
    return db.read_table("ledger_entries"), db.read_table("processor_entries")


ledger, proc = load()
tol = st.sidebar.number_input("Amount tolerance ($)", 0.0, 100.0, config.RECON_AMOUNT_TOLERANCE, 0.01)
res = reconcile(ledger, proc, tol)

counts = res.result.value_counts()
total = len(res)
c1, c2, c3, c4 = st.columns(4)
c1.metric("Matched", f"{counts.get('Matched', 0):,}", f"{counts.get('Matched', 0) / total:.1%} of records", delta_color="off")
c2.metric("Amount mismatches", f"{counts.get('Amount mismatch', 0):,}")
c3.metric("Missing in processor", f"{counts.get('Missing in processor', 0):,}")
c4.metric("Missing in ledger", f"{counts.get('Missing in ledger', 0):,}")

mm = res[res.result == "Amount mismatch"]
st.caption(
    f"Ledger total {compact(ledger.amount.sum())}, processor total {compact(proc.amount.sum())}. "
    f"Net mismatch value {compact(mm.difference.sum())}, gross {compact(mm.difference.abs().sum())}."
)

options = ["Matched", "Amount mismatch", "Missing in processor", "Missing in ledger"]
pick = st.multiselect("Show", options, default=options[1:])
ref = st.text_input("Search reference", placeholder="REF-0000123")
view = res[res.result.isin(pick)]
if ref:
    view = view[view.reference.str.contains(ref, case=False)]

tabs = st.tabs([f"{o} ({counts.get(o, 0):,})" for o in options] + ["Selected view"])
for tab, o in zip(tabs[:-1], options):
    with tab:
        sub = res[res.result == o]
        st.dataframe(sub, width="stretch", hide_index=True, height=360)
        st.download_button(f"Download {o.lower()} (CSV)", sub.to_csv(index=False), f"recon_{o.lower().replace(' ', '_')}.csv",
                           "text/csv", key=f"dl_{o}")
with tabs[-1]:
    st.dataframe(view, width="stretch", hide_index=True, height=360)
    st.download_button("Download selected view (CSV)", view.to_csv(index=False), "recon_selected.csv", "text/csv")
