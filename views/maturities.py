from datetime import timedelta

import pandas as pd
import streamlit as st

from portal import audit, db
from portal.ui import download_csv, page_header, pick_range, require_page

require_page("maturities")
page_header("Maturities", "Investments reaching their maturity date in a date range, by product.")

products = db.query("SELECT DISTINCT product FROM maturities ORDER BY product")["product"].tolist()
product = st.selectbox("Product", products)
last = db.data_date()
d0, d1 = pick_range(last, last + timedelta(days=30), label="Maturity date range")

df = db.query(
    "SELECT maturity_id, customer_id, product, principal, rate_pct, start_date, maturity_date, status "
    "FROM maturities WHERE product = :p AND maturity_date BETWEEN :a AND :b ORDER BY maturity_date",
    {"p": product, "a": str(d0), "b": str(d1)},
)
days = (pd.to_datetime(df.maturity_date) - pd.to_datetime(df.start_date)).dt.days
df["payout"] = (df.principal * (1 + df.rate_pct / 100 * days / 365)).round(2)
audit.log_once("maturities", "lookup", f"maturities {product} {d0} to {d1}: {len(df):,} rows", area="Lookup")

c1, c2, c3 = st.columns(3)
c1.metric("Maturing", f"{len(df):,}")
c2.metric("Principal", f"${df.principal.sum():,.0f}")
c3.metric("Payout due", f"${df.payout.sum():,.0f}")
st.dataframe(df, width="stretch", hide_index=True, height=480,
             column_config={"principal": st.column_config.NumberColumn(format="$%.2f"),
                            "payout": st.column_config.NumberColumn(format="$%.2f"),
                            "rate_pct": st.column_config.NumberColumn("Rate %", format="%.2f")})
download_csv("Download (CSV)", df, f"maturities_{product.lower().replace(' ', '_')}.csv")
