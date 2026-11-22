"""Demo Capital Data Portal: entry point with login and role-based navigation."""
import time

import streamlit as st

from portal import audit, config, db
from portal.pages_registry import PAGES
from portal.ui import inject_css

st.set_page_config(page_title=f"{config.COMPANY} Data Portal", page_icon=":material/account_balance:", layout="wide")
inject_css()


@st.cache_resource
def setup() -> bool:
    db.init_db()
    return True


setup()


def login_screen() -> None:
    _, mid, _ = st.columns([1, 1.4, 1])
    with mid:
        if st.session_state.pop("timed_out", False):
            st.warning(f"You were signed out after {config.IDLE_TIMEOUT_MINUTES} minutes without activity.")
        st.title(f"{config.COMPANY}")
        st.caption("Data Portal. Synthetic demo data only.")
        with st.form("login"):
            user = st.text_input("Username")
            pw = st.text_input("Password", type="password")
            go = st.form_submit_button("Sign in", type="primary", width="stretch")
        if go:
            role = db.authenticate(user, pw)
            if role:
                st.session_state.update(user=user.strip().lower(), role=role)
                audit.log("login", area="Auth")
                st.rerun()
            audit.log("login_failed", f"username: {user.strip().lower()[:50]}", area="Auth", level="WARN",
                      user="anonymous")
            st.error("Invalid username or password.")
        with st.container(border=True):
            st.markdown("**Demo credentials** (fictional, for this portfolio demo)")
            st.table({
                "Username": [u for u, _, _ in config.demo_users()],
                "Password": [p for _, _, p in config.demo_users()],
                "Role": [r for _, r, _ in config.demo_users()],
            })


if "role" not in st.session_state:
    login_screen()
    st.stop()

now = time.time()
if now - st.session_state.get("last_seen", now) > config.IDLE_TIMEOUT_MINUTES * 60:
    audit.log("session_timeout", area="Auth")
    st.session_state.clear()
    st.session_state["timed_out"] = True
    st.rerun()
st.session_state["last_seen"] = now

role = st.session_state["role"]
menu: dict[str, list] = {}
for k in db.allowed_pages(role):
    title, file, icon, group = PAGES[k]
    menu.setdefault(group, []).append(st.Page(file, title=title, icon=icon, url_path=k))
nav = st.navigation(menu)
with st.sidebar:
    st.markdown(f"**{config.COMPANY}**")
    st.caption(f"Signed in as `{st.session_state['user']}` ({role})")
    if st.button("Sign out", width="stretch"):
        audit.log("logout", area="Auth")
        st.session_state.clear()
        st.rerun()
nav.run()
