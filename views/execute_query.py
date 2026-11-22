import streamlit as st

from portal import audit, config, db
from portal.query_guard import ALLOWED_TABLES, RESTRICTED_COLUMNS, check
from portal.ui import download_csv, page_header, require_page

require_page("execute_query")
page_header("Execute Query", f"Run one SELECT on the data tables. Shows the first {config.QUERY_MAX_ROWS} rows. Every run is logged.")

sql = st.text_area("SQL", "SELECT txn_id, customer_id, type, amount, status\nFROM transactions\nWHERE amount > 50000\nORDER BY amount DESC", height=180)
st.caption(f"Tables: {', '.join(sorted(ALLOWED_TABLES))}. Restricted columns: {', '.join(sorted(RESTRICTED_COLUMNS))}. "
           "SELECT * is not allowed on customers.")

if st.button("Run query", type="primary"):
    st.session_state.pop("query_result", None)
    reason = check(sql, db.dialect())
    if reason:
        audit.log("query_blocked", f"{reason} | {sql[:300]}", area="Query", level="WARN")
        st.error(reason)
    else:
        try:
            st.session_state["query_result"] = db.run_select(sql, config.QUERY_MAX_ROWS)
            audit.log("query_run", f"{sql[:300]} | {len(st.session_state['query_result'])} rows", area="Query")
        except Exception as e:
            audit.log("query_error", f"{sql[:300]}", area="Query", level="WARN")
            st.error(f"The query failed: {str(e).splitlines()[0][:200]}")

result = st.session_state.get("query_result")
if result is not None:
    st.dataframe(result, width="stretch", hide_index=True)
    download_csv("Download result (CSV)", result, "query_result.csv")
