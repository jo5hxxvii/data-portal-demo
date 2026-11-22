import pandas as pd
import streamlit as st

from portal import db
from portal.pages_registry import LOCKED, PAGES, ROLES
from portal.ui import page_header, require_page

require_page("admin")
page_header("Admin", "Choose which role can open which page. Changes are stored in the database and apply on the next click.")

access = db.get_access()
matrix = pd.DataFrame(
    {PAGES[p][0]: [p in access.get(r, set()) for r in ROLES] for p in PAGES}, index=ROLES
)
matrix.index.name = "Role"

edited = st.data_editor(
    matrix,
    width="stretch",
    column_config={PAGES[p][0]: st.column_config.CheckboxColumn(PAGES[p][0]) for p in PAGES},
)
st.caption("The Admin role always keeps the Admin page so nobody gets locked out.")

if st.button("Save access", type="primary"):
    new = {r: {p for p in PAGES if edited.loc[r, PAGES[p][0]]} for r in ROLES}
    for role, page in LOCKED:
        new[role].add(page)
    db.save_access(new)
    st.success("Access saved.")
    st.rerun()

st.subheader("Demo users")
st.dataframe(db.query("SELECT username, role FROM users ORDER BY username"), hide_index=True, width="stretch")

st.subheader("Data")
counts = db.table_counts()
st.dataframe(pd.DataFrame({"table": counts.keys(), "rows": counts.values()}), hide_index=True, width="stretch")
if st.button("Regenerate synthetic data"):
    db.init_db(reset_data=True)
    st.cache_data.clear()
    st.success("Synthetic data regenerated.")
