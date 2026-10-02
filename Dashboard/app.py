import calendar
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="Cecafe Daily", layout="wide")

NAVY, TEAL, RED, AMBER, GREEN, GREY = "#0a2463", "#1f8a9c", "#c94a4a", "#c98a1f", "#1f9d6f", "#9aa3b8"
HIST_COLORS = [GREY, AMBER, GREEN, TEAL, RED]          # oldest -> newest previous year
DATA = Path(__file__).resolve().parent.parent / "Database" / "cecafe_daily.csv"
COMMS = ["Arabica", "Robusta"]
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

st.markdown("""
<style>
body, .main { color: #1a1a2e; }
.block-container { padding-top: 1.6rem; max-width: 1500px; }
h1, h2, h3 { color: #0a2463; }
section[data-testid="stSidebar"] { background: #f0f2f8; }
.stTabs [data-baseweb="tab-list"] { gap: 6px; background: #e6e9f2; padding: 4px; border-radius: 10px; width: fit-content; }
.stTabs [data-baseweb="tab"] { border-radius: 8px; padding: 6px 18px; }
.stTabs [aria-selected="true"] { background: #0a2463 !important; color: #fff !important; }
.stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] { display: none; }
.side-note { font-size: 12px; color: #5a6688; line-height: 1.55; }
.side-note b { color: #0a2463; }
.card-desc { font-size: 12px; color: #7a86a8; margin: -6px 0 6px 0; }
.proj { width: 100%; border-collapse: collapse; font-size: 13px; background: #fff; }
.proj th { background: #0a2463; color: #fff; text-align: right; padding: 6px 10px; font-weight: 600; }
.proj th:first-child, .proj td:first-child { text-align: left; }
.proj td { text-align: right; padding: 6px 10px; border-bottom: 1px solid #e6e9f2; }
.proj tr.hl td { background: #e8f3ee; font-weight: 700; color: #0a2463; }
</style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=600)
def load():
    return pd.read_csv(DATA, parse_dates=["date"]).set_index("date").sort_index()


def month_series(s: pd.Series, year: int, month: int) -> pd.Series:
    """Observed cumulative values for one calendar month, indexed by day-of-month."""
    m = s[(s.index.year == year) & (s.index.month == month)].dropna()
    m.index = m.index.day
    return m


def adjusted_daily(m: pd.Series) -> pd.Series:
    """Cumulative -> daily. A jump after skipped days is split equally across those days."""
    out, prev_day, prev_val = {}, 0, 0.0
    for day, val in m.items():
        per = max(val - prev_val, 0.0) / (day - prev_day)
        for k in range(prev_day + 1, day + 1):
            out[k] = per
        prev_day, prev_val = day, val
    return pd.Series(out, dtype=float)


def project(m: pd.Series, year: int, month: int):
    """Linear: x registered in N days -> x / N * days in month."""
    if m.empty:
        return None
    n, x = int(m.index[-1]), float(m.iloc[-1])
    dim = calendar.monthrange(year, month)[1]
    return n, x, x / n * dim, dim


def fmt(v):
    return "-" if v is None or pd.isna(v) else f"{v:,.0f}"


def base_layout(fig, title, height=430):
    fig.update_layout(
        template="plotly_white", height=height, margin=dict(l=10, r=10, t=44, b=10),
        title=dict(text=title, x=0.01, font=dict(size=15, color=NAVY)),
        legend=dict(orientation="h", y=1.0, x=1.0, xanchor="right", yanchor="bottom"),
        hovermode="x unified", paper_bgcolor="#fafafa", plot_bgcolor="#ffffff",
        yaxis=dict(tickformat=","), xaxis=dict(dtick=2, title=None, range=[0.5, 31.5]),
    )
    return fig


df = load()
last_date = df.dropna(how="all").index.max()

# --------------------------------------------------------------------------- sidebar
with st.sidebar:
    st.markdown("### Cecafe Daily")
    ym_all = sorted({(d.year, d.month) for d in df.index})
    labels = [f"{MONTHS[m - 1]} {y}" for y, m in ym_all]
    sel = st.selectbox("Month", labels[::-1], index=0)
    sel_y, sel_m = ym_all[labels.index(sel)]
    min_year = st.slider("History from", int(df.index.year.min()), sel_y - 1, max(sel_y - 5, int(df.index.year.min())))
    connect = st.toggle("Connect gaps", value=False)
    st.markdown(f"<div class='side-note'>Latest data: <b>{last_date:%d %b %Y}</b><br>"
                f"Cumulative month-to-date registrations, bags.<br>"
                f"Blank days are split equally in Adj daily.</div>", unsafe_allow_html=True)

st.markdown("## Cecafe Daily Registrations")

tabs = st.tabs(COMMS)
for tab, comm in zip(tabs, COMMS):
    with tab:
        s = df[comm]
        cur = month_series(s, sel_y, sel_m)
        dim = calendar.monthrange(sel_y, sel_m)[1]
        pr = project(cur, sel_y, sel_m)

        # ---- projection table: selected month + same month in earlier years
        rows = []
        if pr:
            n, x, p, _ = pr
            rows.append((f"{MONTHS[sel_m - 1]} {sel_y}", f"{n} of {dim}", fmt(x), fmt(p), True))
        for y in range(sel_y - 1, min_year - 1, -1):
            h = month_series(s, y, sel_m)
            if not h.empty:
                pj = project(h, y, sel_m)
                rows.append((f"{MONTHS[sel_m - 1]} {y}", f"{int(h.index[-1])} of {calendar.monthrange(y, sel_m)[1]}",
                             fmt(h.iloc[-1]), fmt(pj[2]), False))
        body = "".join(f"<tr class='{'hl' if hl else ''}'><td>{a}</td><td>{b}</td><td>{c}</td><td>{d}</td></tr>"
                       for a, b, c, d, hl in rows)
        st.markdown("<div class='card-desc'>Month-end projection, linear from latest day</div>", unsafe_allow_html=True)
        st.markdown(f"<table class='proj'><tr><th>Month</th><th>Latest day</th><th>Registered</th>"
                    f"<th>Month-end (projected)</th></tr>{body}</table>", unsafe_allow_html=True)
        st.write("")

        c1, c2 = st.columns(2)

        # ---- chart 1: same month, previous years + adjusted daily bars
        fig = go.Figure()
        years = [y for y in range(min_year, sel_y) if not month_series(s, y, sel_m).empty]
        for i, y in enumerate(years):
            h = month_series(s, y, sel_m).reindex(range(1, calendar.monthrange(y, sel_m)[1] + 1))
            back = len(years) - i
            col = HIST_COLORS[-back] if back <= len(HIST_COLORS) else GREY
            fig.add_trace(go.Scatter(x=h.index, y=h.values, name=str(y), mode="lines+markers",
                                     line=dict(color=col, width=2), marker=dict(size=5, symbol="x"),
                                     connectgaps=connect))
        if not cur.empty:
            c = cur.reindex(range(1, dim + 1))
            ad = adjusted_daily(cur)
            fig.add_trace(go.Bar(x=ad.index, y=ad.values, name="Adj daily", marker_color="#c9ced9",
                                 opacity=0.85, yaxis="y2"))
            fig.add_trace(go.Scatter(x=c.index, y=c.values, name=str(sel_y), mode="lines+markers",
                                     line=dict(color=NAVY, width=3.5),
                                     marker=dict(size=8, color="#f2c200", line=dict(color=NAVY, width=1.5)),
                                     connectgaps=connect))
            if pr and pr[0] < dim:
                fig.add_trace(go.Scatter(x=[pr[0], dim], y=[pr[1], pr[2]], name="Projection", mode="lines+markers",
                                         line=dict(color=NAVY, width=2, dash="dot"),
                                         marker=dict(size=7, symbol="diamond")))
            fig.update_layout(yaxis2=dict(overlaying="y", side="right", range=[0, max(ad.max() * 5, 1)],
                                          showgrid=False, visible=False))
        base_layout(fig, f"{comm}: {MONTHS[sel_m - 1]} vs same month, previous years")
        with c1:
            st.plotly_chart(fig, width="stretch")

        # ---- chart 2: selected month vs last 4 months
        fig2 = go.Figure()
        seq, y, m = [], sel_y, sel_m
        for _ in range(5):
            seq.append((y, m))
            m -= 1
            if m == 0:
                y, m = y - 1, 12
        for k, ((yy, mm), col) in enumerate(zip(seq, [NAVY, RED, TEAL, AMBER, GREY])):
            h = month_series(s, yy, mm)
            if h.empty:
                continue
            h = h.reindex(range(1, calendar.monthrange(yy, mm)[1] + 1))
            fig2.add_trace(go.Scatter(x=h.index, y=h.values, name=f"{MONTHS[mm - 1]}'{str(yy)[2:]}",
                                      mode="lines+markers", line=dict(color=col, width=3.5 if k == 0 else 2),
                                      marker=dict(size=7 if k == 0 else 5), connectgaps=connect))
        base_layout(fig2, f"{comm}: {MONTHS[sel_m - 1]} {sel_y} vs last 4 months")
        with c2:
            st.plotly_chart(fig2, width="stretch")
