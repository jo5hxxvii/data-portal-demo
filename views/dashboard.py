import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from portal import db
from portal.ui import AQUA, BLUE, ORANGE, compact, page_header, require_page, style_fig

require_page("dashboard")
page_header("Dashboard", "Assets, flows and customer activity across Demo Capital.")


@st.cache_data(ttl=300)
def load():
    t = db.read_table("transactions")
    t["created_at"] = pd.to_datetime(t["created_at"])
    return db.read_table("customers"), db.read_table("wallets"), t


customers, wallets, txns = load()
done = txns[txns.status == "completed"].copy()
done["day"] = done.created_at.dt.normalize()

days = st.segmented_control("Period", [30, 90, 180, 365], default=90, format_func=lambda d: f"Last {d} days")
days = days or 90
end = done.created_at.max().normalize()
cur = done[done.created_at > end - pd.Timedelta(days=days)]
prev = done[(done.created_at <= end - pd.Timedelta(days=days)) & (done.created_at > end - pd.Timedelta(days=2 * days))]


def flows(df):
    inf = df.loc[df.type == "deposit", "amount"].sum()
    out = df.loc[df.type == "withdrawal", "amount"].sum()
    return inf, out, df.customer_id.nunique()


inf, out, active = flows(cur)
pinf, pout, pactive = flows(prev)
aum = wallets.balance.sum()


def delta(a, b):
    return f"{(a - b) / b:+.1%}" if b else None


c1, c2, c3, c4 = st.columns(4)
c1.metric("Total AUM", compact(aum))
c2.metric("Inflows", compact(inf), delta(inf, pinf))
c3.metric("Outflows", compact(out), delta(out, pout), delta_color="inverse")
c4.metric("Active customers", f"{active:,}", delta(active, pactive))
st.caption("Deltas compare with the previous period of the same length. Active means at least one completed transaction.")

# AUM over time: opening balances plus cumulative net flow
done["signed"] = done.amount.where(done.type == "deposit", -done.amount)
daily = done.groupby("day")["signed"].sum().asfreq("D", fill_value=0)
aum_series = wallets.opening_balance.sum() + daily.cumsum()
aum_series = aum_series[aum_series.index > end - pd.Timedelta(days=days)]

fig = go.Figure(go.Scatter(x=aum_series.index, y=aum_series.values, mode="lines", name="AUM",
                           line=dict(color=BLUE, width=2), fill="tozeroy", fillcolor="rgba(42,120,214,0.10)",
                           hovertemplate="%{x|%d %b %Y}<br>AUM $%{y:,.0f}<extra></extra>"))
fig.update_layout(title="Assets under management", showlegend=False)
fig.update_yaxes(range=[aum_series.min() * 0.97, aum_series.max() * 1.01], tickprefix="$", tickformat="~s")
st.plotly_chart(style_fig(fig), width="stretch")

left, right = st.columns(2)

weekly = cur.set_index("created_at").groupby([pd.Grouper(freq="W"), "type"])["amount"].sum().unstack(fill_value=0)
fig = go.Figure()
fig.add_bar(x=weekly.index, y=weekly.get("deposit", 0), name="Inflows", marker_color=BLUE,
            hovertemplate="%{x|%d %b}<br>Inflows $%{y:,.0f}<extra></extra>")
fig.add_bar(x=weekly.index, y=weekly.get("withdrawal", 0), name="Outflows", marker_color=ORANGE,
            hovertemplate="%{x|%d %b}<br>Outflows $%{y:,.0f}<extra></extra>")
fig.update_layout(title="Weekly inflows and outflows", barmode="group", bargap=0.35)
fig.update_yaxes(tickprefix="$", tickformat="~s")
left.plotly_chart(style_fig(fig), width="stretch")

net = (weekly.get("deposit", 0) - weekly.get("withdrawal", 0))
fig = go.Figure(go.Scatter(x=net.index, y=net.values, mode="lines+markers", name="Net flow",
                           line=dict(color=AQUA, width=2), marker=dict(size=7),
                           hovertemplate="%{x|%d %b}<br>Net $%{y:,.0f}<extra></extra>"))
fig.add_hline(y=0, line_color="#c3c2b7", line_width=1)
fig.update_layout(title="Weekly net flow", showlegend=False)
fig.update_yaxes(tickprefix="$", tickformat="~s")
right.plotly_chart(style_fig(fig), width="stretch")

left, right = st.columns(2)
seg = wallets.merge(customers[["customer_id", "segment", "country"]], on="customer_id")
by_seg = seg.groupby("segment")["balance"].sum().sort_values()
fig = go.Figure(go.Bar(x=by_seg.values, y=by_seg.index, orientation="h", marker_color=BLUE,
                       hovertemplate="%{y}<br>$%{x:,.0f}<extra></extra>"))
fig.update_layout(title="AUM by segment", showlegend=False, bargap=0.5)
fig.update_xaxes(tickprefix="$", tickformat="~s")
left.plotly_chart(style_fig(fig, 300), width="stretch")

by_c = seg.groupby("country")["balance"].sum().nlargest(8).sort_values()
fig = go.Figure(go.Bar(x=by_c.values, y=by_c.index, orientation="h", marker_color=BLUE,
                       hovertemplate="%{y}<br>$%{x:,.0f}<extra></extra>"))
fig.update_layout(title="Top 8 countries by AUM", showlegend=False, bargap=0.5)
fig.update_xaxes(tickprefix="$", tickformat="~s")
right.plotly_chart(style_fig(fig, 300), width="stretch")
