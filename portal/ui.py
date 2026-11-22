"""Shared layout helpers."""
import re
from datetime import timedelta

import streamlit as st

from . import audit, db
from .config import COMPANY

BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
INK, MUTED, GRID = "#0b0b0b", "#898781", "#e1e0d9"

CSS = """
<style>
.block-container {padding-top: 2rem; max-width: 1200px;}
[data-testid="stMetric"] {background:#fff;border:1px solid #e1e0d9;border-radius:10px;padding:14px 18px;}
[data-testid="stMetricLabel"] {color:#52514e;}
h1 {font-weight:650; letter-spacing:-0.01em;}
</style>
"""


def inject_css() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def page_header(title: str, subtitle: str) -> None:
    st.title(title)
    st.caption(subtitle)


def require_page(key: str) -> None:
    """Block a page if the signed-in role is not allowed to see it."""
    role = st.session_state.get("role")
    if not role or key not in db.allowed_pages(role):
        audit.log("access_denied", key, area="Access", level="WARN")
        st.error("You do not have access to this page.")
        st.stop()
    # log only when the person moves to a new page, not on every filter click
    if st.session_state.get("last_page") != key:
        st.session_state["last_page"] = key
        audit.log("page_view", key, area="Navigation")


def download_csv(label: str, df, filename: str, key: str | None = None) -> None:
    """CSV download button that writes a log row when clicked."""
    st.download_button(label, df.to_csv(index=False), filename, "text/csv", key=key,
                       on_click=audit.log, args=("download", f"{filename}, {len(df):,} rows"),
                       kwargs={"area": "Download"})


def pick_range(start, end, max_days: int | None = None, label: str = "Date range"):
    """Date range input. Stops the page until two dates are picked and the range is short enough."""
    dates = st.date_input(label, (start, end))
    if len(dates) != 2:
        st.info("Pick a start date and an end date.")
        st.stop()
    if max_days and (dates[1] - dates[0]).days + 1 > max_days:
        st.error(f"Please pick at most {max_days} days.")
        st.stop()
    return dates


def parse_ids(raw: str, limit: int = 100) -> list[str]:
    """Split pasted IDs on commas, spaces and new lines. Only letters, numbers, dash and underscore are allowed."""
    ids = list(dict.fromkeys(x.upper() for x in re.split(r"[,\s]+", raw) if x))
    if len(ids) > limit:
        st.error(f"Please paste at most {limit} IDs.")
        st.stop()
    bad = [i for i in ids if not re.fullmatch(r"[A-Z0-9_-]+", i)]
    if bad:
        st.error(f"These IDs have characters that are not allowed: {', '.join(bad[:5])}")
        st.stop()
    return ids


def style_fig(fig, height: int = 340):
    fig.update_layout(
        height=height,
        margin=dict(l=8, r=8, t=36, b=8),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=INK, size=12),
        title=dict(font=dict(size=14), x=0, xanchor="left"),
        legend=dict(orientation="h", y=1.12, x=1, xanchor="right", title_text=""),
        hoverlabel=dict(bgcolor="white", font_color=INK),
    )
    fig.update_xaxes(showgrid=False, linecolor=GRID, tickfont=dict(color=MUTED), title_text="")
    fig.update_yaxes(gridcolor=GRID, zeroline=False, tickfont=dict(color=MUTED), title_text="")
    return fig


def money(x: float) -> str:
    return f"${x:,.0f}"


def compact(x: float) -> str:
    for div, suf in ((1e9, "B"), (1e6, "M"), (1e3, "K")):
        if abs(x) >= div:
            return f"${x / div:,.2f}{suf}"
    return f"${x:,.0f}"


__all__ = ["COMPANY"]
