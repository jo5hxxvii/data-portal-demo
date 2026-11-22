"""Demo Capital Data Portal: entry point with login and role-based navigation."""
import streamlit as st

from portal import config, db
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
                st.rerun()
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

role = st.session_state["role"]
pages = [
    st.Page(PAGES[k][1], title=PAGES[k][0], icon=PAGES[k][2], url_path=k)
    for k in db.allowed_pages(role)
]
nav = st.navigation(pages)
with st.sidebar:
    st.markdown(f"**{config.COMPANY}**")
    st.caption(f"Signed in as `{st.session_state['user']}` ({role})")
    if st.button("Sign out", width="stretch"):
        st.session_state.clear()
        st.rerun()
nav.run()
