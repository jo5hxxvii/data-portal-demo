"""Activity log. One row per event. A logging failure must never break the app."""
from datetime import datetime, timezone

import streamlit as st
from sqlalchemy import text

from . import db


def log(action: str, detail: str = "", area: str = "General", level: str = "INFO",
        user: str | None = None, role: str | None = None) -> None:
    user = user or st.session_state.get("user", "anonymous")
    role = role or st.session_state.get("role", "-")
    try:
        with db.connect() as con:
            con.execute(
                text("INSERT INTO audit_log (ts, username, role, level, area, action, detail) "
                     "VALUES (:ts, :u, :r, :l, :a, :x, :d)"),
                {"ts": datetime.now(timezone.utc).replace(tzinfo=None), "u": user, "r": role,
                 "l": level, "a": area, "x": action, "d": detail},
            )
    except Exception as e:  # keep the app running
        print(f"audit log failed: {e}")


def read(limit: int = 5000):
    return db.query("SELECT ts, username, role, level, area, action, detail FROM audit_log "
                    "ORDER BY ts DESC LIMIT :n", {"n": limit})


def log_once(key: str, action: str, detail: str, **kw) -> None:
    """Log only when the detail changed since this person last triggered `key` (stops repeat rows on reruns)."""
    if st.session_state.get("logged_" + key) != detail:
        st.session_state["logged_" + key] = detail
        log(action, detail, **kw)
