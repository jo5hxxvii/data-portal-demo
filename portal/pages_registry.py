"""Single list of pages, roles and the default access."""

# (name, description, is_super). A super role opens every page, including Admin.
ROLES = [
    ("Admin", "Full access, including Admin", 1),
    ("Finance", "Reporting, reconciliation and lookups", 0),
    ("Operations", "Exceptions and lookups", 0),
]

# key -> (title, file, icon, menu group). Keep pages of one group together.
PAGES = {
    "dashboard": ("Dashboard", "views/dashboard.py", ":material/monitoring:", "General"),
    "reconciliation": ("Reconciliation", "views/reconciliation.py", ":material/compare_arrows:", "Finance and Ops"),
    "exceptions": ("Exceptions", "views/exceptions.py", ":material/flag:", "Finance and Ops"),
    "wallet_transactions": ("Wallet Transactions", "views/wallet_transactions.py", ":material/receipt_long:", "Data Lookup"),
    "customer_transactions": ("Customer Transactions", "views/customer_transactions.py", ":material/person_search:", "Data Lookup"),
    "account_statement": ("Account Statement", "views/account_statement.py", ":material/description:", "Data Lookup"),
    "maturities": ("Maturities", "views/maturities.py", ":material/event:", "Data Lookup"),
    "savings_plans": ("Savings Plans", "views/savings_plans.py", ":material/savings:", "Data Lookup"),
    "equity_portfolios": ("Equity Portfolios", "views/equity_portfolios.py", ":material/show_chart:", "Data Lookup"),
    "reports": ("Reports", "views/reports.py", ":material/bar_chart:", "Reports"),
    "execute_query": ("Execute Query", "views/execute_query.py", ":material/terminal:", "Tools"),
    "activity": ("Activity Log", "views/activity.py", ":material/history:", "Administration"),
    "admin": ("Admin", "views/admin.py", ":material/admin_panel_settings:", "Administration"),
}

# Page keys per non-super role. "report:<slug>" grants one report on the Reports page.
DEFAULT_ACCESS = {
    "Finance": ["dashboard", "reconciliation", "wallet_transactions", "customer_transactions", "account_statement",
                "maturities", "savings_plans", "equity_portfolios", "reports", "report:sales-overview"],
    "Operations": ["dashboard", "exceptions", "wallet_transactions", "customer_transactions", "reports",
                   "report:ops-health"],
}

# (slug, title, url, active). Sample links: replace them in Admin with your own.
DEFAULT_REPORTS = [
    ("sales-overview", "Sales Overview (sample)", "https://example.com", 1),
    ("ops-health", "Operations Health (sample)", "https://example.org", 1),
]
