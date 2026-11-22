from datetime import timedelta

import pandas as pd
import streamlit as st

from portal import audit
from portal.ui import download_csv, page_header, require_page

require_page("activity")
page_header("Activity Log", "Who signed in, which pages they opened, what they downloaded and what changed. Times are UTC.")

log = audit.read()
if log.empty:
    st.info("Nothing logged yet.")
    st.stop()
log["ts"] = pd.to_datetime(log["ts"])

with st.sidebar:
    st.subheader("Filters")
    last = log.ts.max().date()
    dates = st.date_input("Date range", (last - timedelta(days=7), last))
    users = st.multiselect("User", sorted(log.username.unique()))
    levels = st.multiselect("Level", sorted(log.level.unique()))
    areas = st.multiselect("Area", sorted(log.area.unique()))
    text = st.text_input("Search detail")

view = log
if len(dates) == 2:
    view = view[(view.ts.dt.date >= dates[0]) & (view.ts.dt.date <= dates[1])]
if users:
    view = view[view.username.isin(users)]
if levels:
    view = view[view.level.isin(levels)]
if areas:
    view = view[view.area.isin(areas)]
if text:
    view = view[view.detail.str.contains(text, case=False)]

c1, c2, c3, c4 = st.columns(4)
c1.metric("Events", f"{len(view):,}")
c2.metric("Sign-ins", f"{(view.action == 'login').sum():,}")
c3.metric("Downloads", f"{(view.action == 'download').sum():,}")
c4.metric("Warnings", f"{(view.level == 'WARN').sum():,}")

st.dataframe(view, width="stretch", hide_index=True, height=520,
             column_config={"ts": st.column_config.DatetimeColumn("Time (UTC)", format="YYYY-MM-DD HH:mm:ss")})
st.caption("Showing the latest 5,000 events. The log cannot be edited or cleared from the portal.")
download_csv("Download this view (CSV)", view, "activity_log.csv")
