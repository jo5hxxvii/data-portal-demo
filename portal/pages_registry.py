"""Single list of pages and the default role access."""

ROLES = ["Admin", "Finance", "Operations"]

# key -> (title, file, icon)
PAGES = {
    "dashboard": ("Dashboard", "views/dashboard.py", ":material/monitoring:"),
    "reconciliation": ("Reconciliation", "views/reconciliation.py", ":material/compare_arrows:"),
    "exceptions": ("Exceptions", "views/exceptions.py", ":material/flag:"),
    "admin": ("Admin", "views/admin.py", ":material/admin_panel_settings:"),
}

DEFAULT_ACCESS = {
    "Admin": ["dashboard", "reconciliation", "exceptions", "admin"],
    "Finance": ["dashboard", "reconciliation"],
    "Operations": ["dashboard", "exceptions"],
}

# The Admin role can never lose this page, so nobody gets locked out.
LOCKED = {("Admin", "admin")}
