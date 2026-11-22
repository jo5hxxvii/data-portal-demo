import plotly.express as px
import streamlit as st

from portal import audit, db
from portal.ui import BLUE, compact, download_csv, page_header, require_page, style_fig

require_page("equity_portfolios")
page_header("Equity Portfolios", "What customers hold on one snapshot date. Prices are made up.")

dates = db.query("SELECT DISTINCT snapshot_date FROM equity_holdings ORDER BY snapshot_date DESC")["snapshot_date"].tolist()
snap = st.selectbox("Snapshot date", dates)

df = db.query(
    "SELECT h.customer_id, c.name, h.ticker, h.units, h.price FROM equity_holdings h "
    "JOIN customers c ON c.customer_id = h.customer_id WHERE h.snapshot_date = :d ORDER BY h.customer_id, h.ticker",
    {"d": snap},
)
df["value"] = (df.units * df.price).round(2)
audit.log_once("equity", "lookup", f"equity portfolios {snap}: {len(df):,} rows", area="Lookup")

c1, c2, c3 = st.columns(3)
c1.metric("Investors", f"{df.customer_id.nunique():,}")
c2.metric("Positions", f"{len(df):,}")
c3.metric("Total value", compact(df.value.sum()))

by_ticker = df.groupby("ticker", as_index=False).value.sum().sort_values("value", ascending=False)
st.plotly_chart(style_fig(px.bar(by_ticker, x="ticker", y="value", title="Value by ticker", color_discrete_sequence=[BLUE]), 300),
                width="stretch")
st.dataframe(df, width="stretch", hide_index=True, height=420,
             column_config={"price": st.column_config.NumberColumn(format="$%.2f"),
                            "value": st.column_config.NumberColumn(format="$%.2f")})
download_csv("Download (CSV)", df, f"equity_portfolios_{snap}.csv")
