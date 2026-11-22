import streamlit as st

from portal import audit, db
from portal.ui import page_header, require_page

require_page("reports")
page_header("Reports", "Dashboards your role can open. Admin manages the list.")

reports = db.allowed_reports(st.session_state["role"])
if reports.empty:
    st.info("No reports have been shared with your role yet.")
    st.stop()

titles = dict(zip(reports.slug, reports.title))
slug = st.selectbox("Report", reports.slug, format_func=titles.get)
url = reports.set_index("slug").url[slug]
audit.log_once("report", "report_view", slug, area="Reports")
if not url.startswith("https://"):  # st.iframe treats other text as raw HTML, so never embed it
    st.error("This report link is not a valid https link. Ask an Admin to fix it.")
    st.stop()
st.link_button("Open in a new tab", url)
st.iframe(url, height=720)
