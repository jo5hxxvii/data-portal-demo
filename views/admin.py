import pandas as pd
import streamlit as st

from portal import audit, db
from portal.pages_registry import PAGES
from portal.ui import page_header, require_page

require_page("admin")
page_header("Admin", "Manage users, roles, page access and report links. Changes apply on the next click.")
me = st.session_state["user"]

if msg := st.session_state.pop("flash", None):
    st.success(msg)


def attempt(change, action: str, detail: str, message: str) -> None:
    """Run a change, log it, and show the result. Passwords are never logged."""
    try:
        change()
    except ValueError as e:
        st.error(str(e))
        return
    audit.log(action, detail, area="Admin")
    st.session_state["flash"] = message
    st.rerun()


users_tab, roles_tab, reports_tab, data_tab = st.tabs(["Users", "Roles and pages", "Reports", "Data"])
roles = db.query(
    "SELECT r.name, r.description, r.is_super, (SELECT COUNT(*) FROM users u WHERE u.role = r.name) AS users "
    "FROM roles r ORDER BY r.name"
)

with users_tab:
    users = db.query("SELECT username, role, active FROM users ORDER BY username")
    users["active"] = users["active"].astype(bool)
    edited = st.data_editor(
        users, hide_index=True, width="stretch", disabled=["username"], key="users_editor",
        column_config={"role": st.column_config.SelectboxColumn("Role", options=roles.name.tolist(), required=True),
                       "active": st.column_config.CheckboxColumn("Active")},
    )
    if st.button("Save user changes", type="primary"):
        changed = edited[(edited.role != users.role) | (edited.active != users.active)]
        if me in changed.username.values:
            st.error("You cannot change your own role or deactivate yourself.")
        elif changed.empty:
            st.info("Nothing to save.")
        else:
            def save_users():
                for r in changed.itertuples():
                    db.update_user(r.username, r.role, r.active)
            attempt(save_users, "users_changed", ", ".join(changed.username), "Users saved.")

    with st.expander("Add a user"), st.form("add_user", clear_on_submit=True):
        new_name = st.text_input("Username")
        new_role = st.selectbox("Role", roles.name)
        new_pw = st.text_input("Password (at least 8 characters)", type="password")
        if st.form_submit_button("Add user"):
            attempt(lambda: db.add_user(new_name, new_role, new_pw), "user_added",
                    f"{new_name.strip().lower()} as {new_role}", "User added.")

    with st.expander("Reset a password"), st.form("reset_pw", clear_on_submit=True):
        who = st.selectbox("User", users.username)
        pw = st.text_input("New password (at least 8 characters)", type="password")
        if st.form_submit_button("Reset password"):
            attempt(lambda: db.set_password(who, pw), "password_reset", who, "Password reset.")

with roles_tab:
    st.dataframe(roles.rename(columns={"is_super": "super"}).assign(super=lambda d: d["super"].astype(bool)),
                 hide_index=True, width="stretch")
    st.caption("A Super role opens every page, including Admin. Other roles only get the pages ticked below.")

    reports = db.query("SELECT slug, title FROM reports WHERE active = 1 ORDER BY title")
    columns = {p: PAGES[p][0] for p in PAGES if p != "admin"}
    columns.update({f"report:{s}": f"Report: {t}" for s, t in zip(reports.slug, reports.title)})
    plain = roles[roles.is_super == 0].name.tolist()
    if plain:
        access = db.get_access()
        matrix = pd.DataFrame({label: [key in access.get(r, set()) for r in plain] for key, label in columns.items()}, index=plain)
        matrix.index.name = "Role"
        grid = st.data_editor(matrix, width="stretch", key="access_grid",
                              column_config={label: st.column_config.CheckboxColumn(label) for label in columns.values()})
        if st.button("Save access", type="primary"):
            new = {r: {k for k, label in columns.items() if grid.loc[r, label]} for r in plain}
            attempt(lambda: db.save_access(new), "access_saved",
                    ", ".join(f"{r}: {len(p)} pages" for r, p in new.items()), "Access saved.")

    with st.expander("Create a role"), st.form("add_role", clear_on_submit=True):
        role_name = st.text_input("Role name")
        role_desc = st.text_input("Description")
        role_super = st.checkbox("Super role (opens everything)")
        if st.form_submit_button("Create role"):
            attempt(lambda: db.add_role(role_name, role_desc, role_super), "role_created",
                    f"{role_name.strip()}{' (super)' if role_super else ''}", "Role created. Tick its pages above.")

    with st.expander("Delete a role"):
        gone = st.selectbox("Role", roles.name, key="role_to_delete")
        if st.button("Delete role"):
            attempt(lambda: db.delete_role(gone), "role_deleted", gone, "Role deleted.")

with reports_tab:
    reps = db.query("SELECT slug, title, url, active FROM reports ORDER BY title")
    reps["active"] = reps["active"].astype(bool)
    rep_grid = st.data_editor(reps, num_rows="dynamic", hide_index=True, width="stretch", key="reports_editor",
                              column_config={"active": st.column_config.CheckboxColumn("Active", default=True)})
    st.caption("Add rows for new reports. Use the public share link (https only). Anyone with a public link can open it, "
               "so do not add sensitive reports. Then tick the report for a role on the Roles and pages tab.")
    if st.button("Save reports", type="primary"):
        attempt(lambda: db.save_reports(rep_grid), "reports_saved", f"{len(rep_grid)} reports", "Reports saved.")

with data_tab:
    counts = db.table_counts()
    st.dataframe(pd.DataFrame({"table": counts.keys(), "rows": counts.values()}), hide_index=True, width="stretch")
    if st.button("Regenerate synthetic data"):
        db.init_db(reset_data=True)
        audit.log("data_regenerated", "synthetic data reset", area="Admin")
        st.cache_data.clear()
        st.success("Synthetic data regenerated.")
