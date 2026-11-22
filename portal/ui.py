"""Shared layout helpers."""
import streamlit as st

from . import db
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
        st.error("You do not have access to this page.")
        st.stop()


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
