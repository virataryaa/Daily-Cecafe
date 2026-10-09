import base64
import calendar
import io
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st

st.set_page_config(page_title="Cecafe Daily", layout="wide", initial_sidebar_state="collapsed")

NAVY = "#0a2463"
TEAL = "#1f8a9c"
GREEN = "#1f9d6f"
RED = "#c94a4a"
AMBER = "#c98a1f"
GREY = "#8a94a8"
OTHER_YEARS = [GREY, AMBER, GREEN, TEAL]               # older years, hidden by default (click legend to show)

DATA = Path(__file__).resolve().parent.parent / "Database" / "cecafe_daily.csv"
PCT_HIST = Path(__file__).resolve().parent.parent / "Database" / "dispatched_pct_history.csv"
COMMS = ["Arabica", "Robusta"]                          # charts + accuracy (have history)
ALL = ["Arabica", "Robusta", "Soluble"]                 # table + entry (Soluble from Oct 2026)
DISP = {c: f"{c} Dispatched" for c in ALL}               # dispatched, cumulative MTD (from Oct 2026)
COLS = ALL + list(DISP.values())                         # every data column in the CSV
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
LOOKBACK = 5                                            # years in the seasonal bands

# Strict light theme (same as Cotton On-Call): CSS hard-codes colours, no prefers-color-scheme,
# and .streamlit/config.toml pins base="light".
st.markdown(
    """
<style>
[data-testid="stAppViewContainer"], [data-testid="stMain"], .main { background: #fafafa !important; }
[data-testid="stHeader"] { background: #fafafa !important; }
[data-testid="stSidebar"] { background: #f0f2f8 !important; border-right: 1px solid #dfe3ee; }
h1, h2, h3, h4, h5, h6 { color: #0a2463 !important; }
body, .main { color: #1a1a2e; }
[data-testid="stSidebar"] { color: #1a1a2e; }
.block-container { padding-top: 2.2rem; }

/* Pill / segmented-control tabs */
.stTabs [data-baseweb="tab-list"] { background: #eef0f6; padding: 4px; border-radius: 999px; gap: 4px; display: inline-flex; }
.stTabs [data-baseweb="tab"] { background: transparent !important; color: #5a6688 !important; border-radius: 999px !important;
                               padding: 8px 20px !important; font-weight: 600; border: none !important; }
.stTabs [aria-selected="true"] { background: #0a2463 !important; color: #ffffff !important; }
.stTabs [data-baseweb="tab-highlight"] { display: none !important; }
.stTabs [data-baseweb="tab-border"] { display: none !important; }

/* Radio as pill/segmented control */
div[role="radiogroup"] { background: #eef0f6; padding: 4px; border-radius: 999px; gap: 2px; display: inline-flex; flex-wrap: wrap; }
div[role="radiogroup"] label { background: transparent !important; border-radius: 999px !important; padding: 4px 12px !important; margin: 0 !important; }
div[role="radiogroup"] label[data-baseweb="radio"] > div:first-child { display: none; }
div[role="radiogroup"] label div[data-testid="stMarkdownContainer"] p { font-size: 12px !important; color: #5a6688; }
div[role="radiogroup"] label:has(input:checked) { background: #0a2463 !important; }
div[role="radiogroup"] label:has(input:checked) div[data-testid="stMarkdownContainer"] p { color: #ffffff !important; font-weight: 600; }

/* Selects: white bg, dark text */
[data-baseweb="popover"] [data-baseweb="menu"] { background: #ffffff !important; }
[data-baseweb="popover"] [data-baseweb="menu"] li,
[data-baseweb="popover"] [data-baseweb="menu"] li * { color: #1a1a2e !important; }
[data-baseweb="select"] { background: #ffffff !important; }
[data-baseweb="select"] > div { background: #ffffff !important; color: #1a1a2e !important; }

.card-desc { color: #5a6688; font-size: 0.82rem; margin-top: -6px; margin-bottom: 10px; }
.chart-head { color: #0a2463; font-weight: 600; font-size: 0.95rem; margin-bottom: 0; }
[data-testid="stVerticalBlockBorderWrapper"]:has(> div > [data-testid="stVerticalBlock"]) {
    background: #ffffff; border: 1px solid #e3e7f0 !important; border-radius: 12px;
    box-shadow: 0 1px 3px rgba(10,36,99,0.06); }
.st-key-main div[role="radiogroup"] { background: transparent; border-bottom: 2px solid #dfe3ee; border-radius: 0; padding: 0; gap: 6px; display: flex; width: 100%; }
.st-key-main div[role="radiogroup"] label { background: transparent !important; border-radius: 0 !important; padding: 8px 16px !important; margin-bottom: -2px !important; border-bottom: 3px solid transparent; }
.st-key-main div[role="radiogroup"] label div[data-testid="stMarkdownContainer"] p { font-size: 17px !important; font-weight: 700; color: #7a86a8 !important; }
.st-key-main div[role="radiogroup"] label:has(input:checked) { background: transparent !important; border-bottom: 3px solid #0a2463 !important; }
.st-key-main div[role="radiogroup"] label:has(input:checked) div[data-testid="stMarkdownContainer"] p { color: #0a2463 !important; }
.st-key-nav div[role="radiogroup"] label { padding: 7px 18px !important; }
.st-key-monthsel { display: flex; justify-content: flex-end; }
.st-key-monthsel [data-baseweb="select"] { min-width: 210px; max-width: 250px; margin-left: auto; }
.st-key-monthsel [data-baseweb="select"] > div { border-radius: 999px !important; border: 1.5px solid #0a2463 !important;
    background: #ffffff !important; box-shadow: 0 1px 5px rgba(10,36,99,0.14); min-height: 40px; padding-left: 8px; }
.st-key-monthsel [data-baseweb="select"] div, .st-key-monthsel [data-baseweb="select"] span { color: #0a2463 !important; font-weight: 600; }
.st-key-monthsel [data-baseweb="select"] svg { fill: #0a2463 !important; }
.st-key-nav div[role="radiogroup"] label:first-of-type div[data-testid="stMarkdownContainer"] p { color: #1f8a9c !important; font-weight: 700; }
.st-key-nav div[role="radiogroup"] label:first-of-type:has(input:checked) { background: #1f8a9c !important; }
.st-key-nav div[role="radiogroup"] label:first-of-type:has(input:checked) div[data-testid="stMarkdownContainer"] p { color: #ffffff !important; }
.st-key-nav div[role="radiogroup"] label div[data-testid="stMarkdownContainer"] p { font-size: 14px !important; }
.page-title { color: #0a2463; font-weight: 700; font-size: 1.25rem; margin: 0 0 6px 0; }
.card-title { color: #0a2463; font-weight: 700; font-size: 1rem; margin-bottom: 2px; }
.pill { display: inline-block; background: #e6e9f2; color: #0a2463; font-size: 11px; font-weight: 600;
        padding: 1px 8px; border-radius: 999px; margin-left: 6px; vertical-align: middle; }
.grid-head { color: #0a2463; font-weight: 600; font-size: 0.85rem; padding: 3px 8px; background: #e6e9f2; border-radius: 6px 6px 0 0; margin-bottom: 2px; display: inline-block; }

/* Sidebar title + small stats */
.sb-title { font-family: 'Fraunces', Georgia, serif; font-size: 1.5rem; font-weight: 600; color: #0a2463; margin-bottom: 2px; }
.sb-caption { font-size: 11px; color: #7a86a8; margin-bottom: 16px; line-height: 1.4; }
.filter-stat { font-size: 12px; color: #5a6688 !important; line-height: 1.7; margin-bottom: 14px; }
.filter-stat b { color: #0a2463 !important; font-size: 13px; }

/* Compact Excel-style tables */
.dtab { width: auto; border-collapse: collapse; font-size: 11.5px; line-height: 1.15; background: #ffffff; }
.dtab th { text-align: center; padding: 2px 8px; font-weight: 600; white-space: nowrap; }
.dtab .g1 { background: #ffffff; color: #1a1a2e; border: 1px solid #dfe3ee; }
.dtab .g2 { background: #dfe5f1; color: #0a2463; border: 1px solid #dfe3ee; }
.dtab .g3 { background: #e3f1ee; color: #0a2463; border: 1px solid #dfe3ee; }
.dtab .sub th { background: #0a2463; color: #ffffff; }
.dtab td { text-align: right; padding: 1px 8px; border-bottom: 1px solid #eef0f6; white-space: nowrap; color: #1a1a2e; }
.dtab td.dt { text-align: center; background: #f0f2f8; }
.dtab td.b { font-weight: 700; background: #f6f7fb; }
.dtab-lg { font-size: 13px; }
.dtab-lg th { padding: 3px 9px; }
.dtab-lg td { padding: 2px 9px; }
.dtab td.avgc { background: #e3f1ee; color: #0a2463; font-style: italic; }
.dtab td.early { color: #6f7895; background: #f4f5f8; font-weight: 400; font-style: italic; }
.tab-note { font-size: 11px; color: #7a86a8; margin-top: 4px; }
.dtab td.ts { font-size: 10.5px; font-style: italic; color: #7a86a8; text-align: left; }
</style>
""",
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------------------------
# data helpers
# ---------------------------------------------------------------------------------------------
@st.cache_data(ttl=600)
def load():
    d = pd.read_csv(DATA, parse_dates=["date"]).set_index("date").sort_index()
    return d.reindex(columns=COLS)


def month_dim(year, month):
    return calendar.monthrange(year, month)[1]


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
    dim = month_dim(year, month)
    return n, x, x / n * dim, dim


def full_curve(m: pd.Series, dim: int) -> pd.Series:
    """Observed cumulative -> every day 0..dim. 0 at day 0, linear between observations, flat after the last."""
    c = pd.Series({0: 0.0, **m.astype(float).to_dict()}).reindex(range(0, dim + 1))
    return c.interpolate(limit_area="inside").ffill()


def month_final(s: pd.Series, year: int, month: int):
    """Month-end total: last observation, only if it lands in the final 3 days (month complete)."""
    m = month_series(s, year, month)
    if m.empty or m.index[-1] < month_dim(year, month) - 3:
        return None
    return float(m.iloc[-1])


@st.cache_data(ttl=600)
def accuracy_table(data: pd.DataFrame, comm: str) -> pd.DataFrame:
    """Every complete month: what the linear projection said on each day vs the actual month-end."""
    s = data[comm]
    rows = []
    for y, mo in sorted({(d.year, d.month) for d in s.dropna().index}):
        fin = month_final(s, y, mo)
        if not fin:
            continue
        m = month_series(s, y, mo)
        dim = month_dim(y, mo)
        for day in range(1, dim + 1):
            known = m[m.index <= day]                                  # only what was known on that day
            if known.empty:
                continue
            k, x = int(known.index[-1]), float(known.iloc[-1])
            rows.append(dict(year=y, month=mo, day=day, err=(x / k * dim / fin - 1) * 100))
    return pd.DataFrame(rows)


def fmt(v):
    return "-" if v is None or pd.isna(v) else f"{v:,.0f}"


def cell(v, bold=False, early=False):
    return f"<td class='{'b' if bold else ''}{' early' if early else ''}'>{fmt(v)}</td>"


def chart_layout(fig, **extra):
    xaxis = dict(gridcolor="rgba(10,36,99,0.08)", color="#4a5578", dtick=2, range=[0.5, 31.5])
    yaxis = dict(gridcolor="rgba(10,36,99,0.08)", color="#4a5578", tickformat=",", hoverformat=",.0f")
    xaxis.update(extra.pop("xaxis", {}))
    yaxis.update(extra.pop("yaxis", {}))
    fig.update_layout(
        template="plotly_white",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#1a1a2e"),
        legend=dict(bgcolor="rgba(0,0,0,0)"),
        hovermode="x unified",
        xaxis=xaxis,
        yaxis=yaxis,
        margin=dict(t=20, b=30, l=10, r=10),
        **extra,
    )
    return fig


def bottom_legend(fig):
    fig.update_layout(legend=dict(orientation="h", x=0, y=-0.08, xanchor="left", yanchor="top",
                                  font=dict(size=11), bgcolor="rgba(0,0,0,0)", traceorder="normal"),
                      margin=dict(t=20, b=10, l=10, r=10), height=(fig.layout.height or 480) + 50)
    return fig


def sidebar_stats(rows):
    """rows: list of (label, value, subtext) - small text, not cards."""
    html = "<div class='filter-stat'>"
    for label, value, sub in rows:
        html += f"{label}: <b>{value}</b>" + (f" <span style='color:#7a86a8;'>({sub})</span>" if sub else "") + "<br>"
    st.markdown(html + "</div>", unsafe_allow_html=True)


# ---------------------------------------------------------------------------------------------
# sidebar
# ---------------------------------------------------------------------------------------------
df = load()
last_date = df.dropna(how="all").index.max()

# Widgets that are not drawn in a run lose their value (e.g. the Daily controls while Monthly is open).
# Keep a copy of the ones we care about and put it back before the widgets are created.
KEEP = ["main_tab", "page", "month_sel", "years", "pct_kind", "pct_span", "pct_connect", "mc_ch_comm", "mc_ch_unit", "mc_ch_span", "mc_tb_comm", "mc_tb_unit",
        "mc_page", "mc_view", "mc_pj_method", "mc_cy_basis", "mc_cy_start", "mc_edit_years"]
for _k in KEEP:
    if _k not in st.session_state and f"_keep_{_k}" in st.session_state:
        st.session_state[_k] = st.session_state[f"_keep_{_k}"]

TODAY = pd.Timestamp.today()
# months with data, plus the running calendar month so its first day can be entered
ym_all = sorted({(d.year, d.month) for d in df.index} | {(TODAY.year, TODAY.month)})
labels = [f"{MONTHS[m - 1]} {y}" for y, m in ym_all]

with st.sidebar:
    st.markdown("<div class='sb-title'>Cecafe</div>", unsafe_allow_html=True)
    st.markdown("<div class='sb-caption'>Brazil coffee exports: daily registrations and dispatched (Daily Cecafe), "
                "crop-year monthly exports (Monthly Cecafe). Bags.</div>", unsafe_allow_html=True)

# the month filter lives in the Daily Cecafe tab (right of the page tabs); read it here so the title can use it
MONTH_CHOICES = labels[::-1][:12]                              # newest first, last 12 months
if st.session_state.get("month_sel") not in MONTH_CHOICES:
    st.session_state["month_sel"] = MONTH_CHOICES[0]
sel = st.session_state["month_sel"]
sel_y, sel_m = ym_all[labels.index(sel)]
MON = f"{MONTHS[sel_m - 1]}'{str(sel_y)[2:]}"
first_year = int(df.index.year.min())
min_year = first_year                                          # History page: all years



# ---------------------------------------------------------------------------------------------
# VIEWS (rendered at the bottom)
# ---------------------------------------------------------------------------------------------
def render_table():
    dim_sel = month_dim(sel_y, sel_m)
    cur = {c: month_series(df[c], sel_y, sel_m) for c in ALL}
    have = [c for c in ALL if not cur[c].empty]               # types with data this month -> Total
    cols = ALL                                                # always show all three columns
    days = sorted(set().union(*[cur[c].index for c in have])) if have else []

    def total(vals):
        return None if any(v is None for v in vals) else sum(vals)

    rows_html = ""
    prev = {c: 0.0 for c in cols}
    for d_ in days:
        cum, chg, prj = {}, {}, {}
        for c in cols:
            v = cur[c].get(d_)
            if v is not None and pd.notna(v):
                cum[c], chg[c], prev[c] = v, v - prev[c], v
                prj[c] = v / d_ * dim_sel                       # linear month-end projection as of that day
            else:
                cum[c] = chg[c] = prj[c] = None
        e = d_ <= 10
        rows_html += f"<tr><td class='dt'>{d_:02d}-{MONTHS[sel_m - 1]}</td>"
        for grp, early in ((chg, False), (cum, False), (prj, e)):
            rows_html += ("".join(cell(grp[c], early=early) for c in cols)
                          + cell(total([grp[c] for c in have]), True, early=early))
        rows_html += "</tr>"

    st.markdown(f"<div class='card-title'>Daily change and linear month-end <span class='pill'>{MON}</span></div>"
                "<div class='card-desc'>Grey = day 1-10, too early to project.</div>", unsafe_allow_html=True)
    if not days:
        st.info(f"No data for {MON} yet.")
    else:
        n = len(cols) + 1
        st.markdown(
            "<div style='overflow-x:auto'><table class='dtab dtab-lg'>"
            f"<tr><th></th><th colspan='{n}' class='g1'>Change with Previous</th>"
            f"<th colspan='{n}' class='g2'>Cumulative Current Month</th><th colspan='{n}' class='g3'>Linear Month-end</th></tr>"
            "<tr class='sub'><th>Until</th>" + ("".join(f"<th>{c}</th>" for c in cols) + "<th>Total</th>") * 3 + "</tr>"
            + rows_html + "</table></div>",
            unsafe_allow_html=True)
    st.write("")


def history_table_html(comm):
    """Read-only: same month across years, cumulative by day (blank = Cecafe skipped), Adj daily for the selected year."""
    s = df[comm]
    years = [y for y in range(min_year, sel_y + 1) if not month_series(s, y, sel_m).empty]
    if not years:
        return ""
    ser = {y: month_series(s, y, sel_m) for y in years}
    ad = adjusted_daily(ser[sel_y]) if sel_y in ser else pd.Series(dtype=float)
    body = ""
    for d_ in range(1, month_dim(sel_y, sel_m) + 1):
        body += f"<tr><td class='dt'>{d_:02d}-{MONTHS[sel_m - 1]}</td>"
        body += "".join(f"<td class='{'b' if y == sel_y else ''}'>{fmt(ser[y][d_]) if d_ in ser[y].index else ''}</td>"
                        for y in years)
        body += f"<td>{fmt(ad[d_]) if d_ in ad.index else ''}</td></tr>"
    return (f"<div class='grid-head'>{comm}</div><table class='dtab'><tr class='sub'><th>Date</th>"
            + "".join(f"<th>{y}</th>" for y in years) + "<th>Adj daily</th></tr>" + body + "</table>")


def render_history_tables():
    st.markdown(f"<div class='chart-head' style='margin-top:6px'>{MONTHS[sel_m - 1]} by year, cumulative MTD</div>"
                "<div class='card-desc'>Blank = Cecafe skipped the day. Adj daily = skipped days split equally.</div>",
                unsafe_allow_html=True)
    comms = [c for c in ALL if not df[c].dropna().empty]
    widths = [sum(not month_series(df[c], y, sel_m).empty for y in range(min_year, sel_y + 1)) + 2 for c in comms]
    cs = st.columns(widths, gap="small")
    for col_, comm in zip(cs, comms):
        col_.markdown(f"<div style='overflow-x:auto'>{history_table_html(comm)}</div>", unsafe_allow_html=True)


def entry_grid(cols):
    """Selected month only: one row per day; cols = {grid label: CSV column}. Text cells keep blanks blank."""
    dim = month_dim(sel_y, sel_m)
    g = pd.DataFrame(index=[f"{d:02d}-{MONTHS[sel_m - 1]}" for d in range(1, dim + 1)])
    for label, col in cols.items():
        m = month_series(df[col], sel_y, sel_m)
        g[label] = [fmt(m[d]) if d in m.index else "" for d in range(1, dim + 1)]
    vals = g.apply(lambda col: col.map(parse_num))
    return g, [fmt(r.sum()) if r.notna().any() else "" for _, r in vals.iterrows()]      # totals: read-only


def grid_changes(before: pd.DataFrame, after: pd.DataFrame, cols, out=None):
    """{date: {CSV column: value}} for every changed cell. Raises ValueError on non-numbers."""
    out = {} if out is None else out
    for label, col in cols.items():
        for i, (a, b) in enumerate(zip(before[label], after[label])):
            a, b = parse_num(a), parse_num(b)
            if a != b:
                out.setdefault(pd.Timestamp(sel_y, sel_m, i + 1), {})[col] = b
    return out


GRID_KEY = "entry_grid"
GRIDS = {"Registered": {c: c for c in ALL}, "Dispatched": {f"Disp {c}": DISP[c] for c in ALL}}
TOTALS = {"Registered": "Total", "Dispatched": "Disp Total"}


def save_grid(changes):
    """changes: {date: {type: value}} -> one commit per date, other columns of that row kept."""
    with st.spinner("Saving..."):
        try:
            for d0, upd in sorted(changes.items()):
                old = ({c: (None if pd.isna(v) else float(v)) for c, v in df.loc[d0].items()}
                       if d0 in df.index else {c: None for c in COLS})
                vals = {**old, **upd}
                commit_change(lambda f, d0=d0, vals=vals: apply_entry(f, d0, vals),
                              f"Entry {d0:%Y-%m-%d} via dashboard | " + vals_text(vals, " | "))
        except (GitHubError, requests.RequestException) as ex:
            st.error(f"GitHub save failed: {ex}")
            return
    st.session_state.pop("pending_grid", None)
    st.session_state.pop(f"{GRID_KEY}_{sel_y}_{sel_m}", None)
    st.session_state["flash"] = f"Saved {len(changes)} date(s)."
    st.rerun()


def render_entry_grid():
    if st.session_state.get("flash"):
        st.toast(st.session_state.pop("flash"))
    editable = entry_enabled()
    st.markdown(f"<div class='card-title'>Entry <span class='pill'>{MON}</span></div>"
                "<div class='card-desc'>Cumulative MTD from Cecafe, bags. Disp = dispatched. "
                + ("Click a cell, type, Save." if editable else "Read-only: add github_token in Secrets.")
                + "</div>", unsafe_allow_html=True)
    # one grid, one Date column: registered block, then dispatched block, each with a read-only total
    parts = []
    for kind, cols in GRIDS.items():
        part, tot = entry_grid(cols)
        part[TOTALS[kind]] = tot
        parts.append(part)
    g = pd.concat(parts, axis=1)
    cfg = {c: st.column_config.TextColumn(c, alignment="right", width=80 if c in ALL else 108) for c in g.columns}
    for c in TOTALS.values():
        cfg[c] = st.column_config.TextColumn(c, alignment="right", width=88, disabled=True)
    cfg["_index"] = st.column_config.TextColumn("Date", width=58)
    key = f"{GRID_KEY}_{sel_y}_{sel_m}"
    keys = [key]
    changes = {}
    shown = g.style.set_properties(subset=list(TOTALS.values()),
                                   **{"background-color": "#e9ecf2", "font-weight": "600"})   # totals: light grey
    after = st.data_editor(shown, column_config=cfg, disabled=not editable, width="content",
                           row_height=26, height=len(g) * 26 + 52, key=key)
    try:
        for cols in GRIDS.values():
            grid_changes(g, after, cols, changes)
    except ValueError:
        st.error("Numbers only (commas are fine).")
        return
    if not editable:
        return
    bc = st.columns([1, 1, 4], vertical_alignment="center")
    save = bc[0].button("Save", type="primary", disabled=not changes, width="stretch")
    if bc[1].button("Undo", disabled=not changes, width="stretch"):
        for key in keys:
            st.session_state.pop(key, None)
        st.session_state.pop("pending_grid", None)
        st.rerun()
    if changes:
        bc[2].markdown(f"<div class='card-desc' style='margin:0'>{sum(len(v) for v in changes.values())} "
                       "unsaved cell(s).</div>", unsafe_allow_html=True)
    if save:
        notes = []
        for d0, upd in sorted(changes.items()):
            notes += value_notes(d0, upd)
        if not notes:
            save_grid(changes)
            return
        st.session_state["pending_grid"] = notes
    if st.session_state.get("pending_grid") and changes:
        cc = st.columns([3.2, 0.6, 0.6, 1.6], vertical_alignment="center")
        cc[0].warning(" ".join(st.session_state["pending_grid"]) + " Save anyway?")
        if cc[1].button("Override", type="primary", width="stretch", key="grid_override"):
            save_grid(changes)
        if cc[2].button("Cancel", width="stretch", key="grid_cancel"):
            st.session_state.pop("pending_grid", None)
            st.rerun()


def render_visuals():
    def same_month_fig(comm):
        s = df[comm]
        cur_s = month_series(s, sel_y, sel_m)
        dim = month_dim(sel_y, sel_m)
        pr = project(cur_s, sel_y, sel_m)
        fig = go.Figure()

        # bands from the previous LOOKBACK years (interpolated across Cecafe's blank days)
        band = {}
        for y in range(sel_y - LOOKBACK, sel_y):
            hm = month_series(s, y, sel_m)
            if not hm.empty:
                band[y] = full_curve(hm, month_dim(y, sel_m)).reindex(range(1, dim + 1))
        if len(band) >= 2:
            bd = pd.DataFrame(band)
            q = bd.agg(["min", "max", "mean"], axis=1)
            q["p25"], q["p75"] = bd.quantile(0.25, axis=1), bd.quantile(0.75, axis=1)
            for lo, hi, colr, name in [("min", "max", "rgba(31,138,156,0.10)", "Min-Max"),
                                       ("p25", "p75", "rgba(31,138,156,0.24)", "25th-75th pct")]:
                fig.add_trace(go.Scatter(x=q.index, y=q[hi], line=dict(width=0), showlegend=False, hoverinfo="skip"))
                fig.add_trace(go.Scatter(x=q.index, y=q[lo], fill="tonexty", fillcolor=colr, line=dict(width=0),
                                         name=name, hoverinfo="skip"))
            fig.add_trace(go.Scatter(x=q.index, y=q["mean"], mode="lines", name=f"{len(band)}y average",
                                     line=dict(color="#4a5578", width=1.5, dash="dot")))

        # older years: shown for the chosen range (Last 2 / All)
        older = [y for y in range(min_year, sel_y - 1) if not month_series(s, y, sel_m).empty]
        for i, y in enumerate(older):
            h = month_series(s, y, sel_m).reindex(range(1, month_dim(y, sel_m) + 1))
            fig.add_trace(go.Scatter(x=h.index, y=h.values, name=str(y), mode="lines+markers",
                                     line=dict(color=OTHER_YEARS[i % len(OTHER_YEARS)], width=1.5),
                                     marker=dict(size=4), connectgaps=connect))

        # last year red, current year navy bold
        h = month_series(s, sel_y - 1, sel_m)
        if not h.empty:
            h = h.reindex(range(1, month_dim(sel_y - 1, sel_m) + 1))
            fig.add_trace(go.Scatter(x=h.index, y=h.values, name=str(sel_y - 1), mode="lines+markers",
                                     line=dict(color=RED, width=2), marker=dict(size=5), connectgaps=connect))
        # Adj daily panel: last year (light red) next to this year
        ly = month_series(s, sel_y - 1, sel_m)
        if not ly.empty:
            ad_ly = adjusted_daily(ly)
            fig.add_trace(go.Bar(x=ad_ly.index, y=ad_ly.values, name=f"Adj daily {sel_y - 1}",
                                 marker_color="rgba(201,74,74,0.28)", hovertemplate="%{y:,.0f}", yaxis="y2"))
        if not cur_s.empty:
            ad = adjusted_daily(cur_s)
            fig.add_trace(go.Bar(x=ad.index, y=ad.values, name=f"Adj daily {sel_y}", marker_color="#8f9bb8",
                                 hovertemplate="%{y:,.0f}", yaxis="y2"))
            c = cur_s.reindex(range(1, dim + 1))
            fig.add_trace(go.Scatter(x=c.index, y=c.values, name=str(sel_y), mode="lines+markers",
                                     line=dict(color=NAVY, width=3), marker=dict(size=7), connectgaps=connect))
            if pr and 10 < pr[0] < dim:          # no projection line in the first 10 days
                fig.add_trace(go.Scatter(x=[pr[0], dim], y=[pr[1], pr[2]], name="Projection", mode="lines+markers",
                                         line=dict(color=NAVY, width=1.5, dash="dot"),
                                         marker=dict(size=7, symbol="diamond")))
        # average bags/day of this month in the previous LOOKBACK years (month-end / days in month)
        per_day = [month_final(s, y, sel_m) / month_dim(y, sel_m) for y in range(sel_y - LOOKBACK, sel_y)
                   if month_final(s, y, sel_m)]
        if per_day:
            avg_d = sum(per_day) / len(per_day)
            fig.add_trace(go.Scatter(x=[0.5, dim + 0.5], y=[avg_d, avg_d], mode="lines", yaxis="y2",
                                     name=f"{len(per_day)}y avg/day", hovertemplate="%{y:,.0f}",
                                     line=dict(color="#4a5578", width=1.5, dash="dot")))
        chart_layout(fig, height=600)
        visible = [tr for tr in fig.data if tr.yaxis != "y2" and tr.visible != "legendonly" and len(tr.y)]
        ymax = max([float(pd.Series(tr.y).max()) for tr in visible] or [1.0])
        # two stacked panels on one day axis: cumulative on top, Adj daily as a mini bar chart below
        fig.update_layout(
            yaxis=dict(domain=[0.3, 1], range=[0, ymax * 1.05]),
            yaxis2=dict(domain=[0, 0.22], anchor="x", tickformat=",", hoverformat=",.0f", nticks=3,
                        gridcolor="rgba(10,36,99,0.08)", color="#4a5578",
                        title=dict(text="Adj daily", font=dict(size=10, color="#7a86a8"))),
            xaxis=dict(anchor="y2"),
            barmode="group", bargap=0.25, bargroupgap=0.05,
        )
        order = [str(sel_y), str(sel_y - 1), *[str(y) for y in reversed(older)], "Projection",
                 f"{LOOKBACK}y average", "25th-75th pct", "Min-Max"]
        for tr in fig.data:
            tr.legendrank = (order.index(tr.name) if tr.name in order else 50) + (100 if tr.yaxis == "y2" else 0)
        bottom_legend(fig)
        return fig

    def last_months_fig(comm):
        s = df[comm]
        fig = go.Figure()
        seq, y, m = [], sel_y, sel_m
        for _ in range(6):                                      # selected month + 5 before it
            seq.append((y, m))
            m -= 1
            if m == 0:
                y, m = y - 1, 12
        for k, ((yy, mm), col) in enumerate(zip(seq[:5], [NAVY, RED, TEAL, AMBER, GREY])):
            h = month_series(s, yy, mm)
            if h.empty:
                continue
            h = h.reindex(range(1, month_dim(yy, mm) + 1))
            fig.add_trace(go.Scatter(x=h.index, y=h.values, name=f"{MONTHS[mm - 1]}'{str(yy)[2:]}",
                                     mode="lines+markers", line=dict(color=col, width=3 if k == 0 else 1.8),
                                     marker=dict(size=7 if k == 0 else 4), connectgaps=connect))

        # Adj daily panel: previous month (light yellow) next to the selected month, plus 5-month avg/day
        lab = lambda yy, mm: f"{MONTHS[mm - 1]}'{str(yy)[2:]}"
        for (yy, mm), colr in ((seq[1], "rgba(224,170,40,0.45)"), (seq[0], "#8f9bb8")):
            mser = month_series(s, yy, mm)
            if not mser.empty:
                ad = adjusted_daily(mser)
                fig.add_trace(go.Bar(x=ad.index, y=ad.values, name=f"Adj daily {lab(yy, mm)}", marker_color=colr,
                                     hovertemplate="%{y:,.0f}", yaxis="y2"))
        per_day = [month_final(s, yy, mm) / month_dim(yy, mm) for yy, mm in seq[1:] if month_final(s, yy, mm)]
        if per_day:
            avg_d = sum(per_day) / len(per_day)
            fig.add_trace(go.Scatter(x=[0.5, 31.5], y=[avg_d, avg_d], mode="lines", yaxis="y2",
                                     name=f"{len(per_day)}m avg/day", hovertemplate="%{y:,.0f}",
                                     line=dict(color="#4a5578", width=1.5, dash="dot")))
        chart_layout(fig, height=600)
        ymax = max([float(pd.Series(tr.y).max()) for tr in fig.data if tr.yaxis != "y2" and len(tr.y)] or [1.0])
        fig.update_layout(
            yaxis=dict(domain=[0.3, 1], range=[0, ymax * 1.05]),
            yaxis2=dict(domain=[0, 0.22], anchor="x", tickformat=",", hoverformat=",.0f", nticks=3,
                        gridcolor="rgba(10,36,99,0.08)", color="#4a5578",
                        title=dict(text="Adj daily", font=dict(size=10, color="#7a86a8"))),
            xaxis=dict(anchor="y2"),
            barmode="group", bargap=0.25, bargroupgap=0.05,
        )
        return bottom_legend(fig)

    # row 1: same month across years, Arabica | Robusta
    for col_, comm in zip(st.columns(len(COMMS)), COMMS):
        with col_:
            st.markdown(f"<div class='chart-head'>{comm}: {MON} vs same month, past years</div>"
                        "<div class='card-desc'>Bands = last 5 years. Bars = Adj daily, dotted = 5y avg/day.</div>",
                        unsafe_allow_html=True)
            st.plotly_chart(same_month_fig(comm), width="stretch")
    # row 2: last 4 months, Arabica | Robusta
    for col_, comm in zip(st.columns(len(COMMS)), COMMS):
        with col_:
            st.markdown(f"<div class='chart-head'>{comm}: {MON} vs last 4 months</div>"
                        "<div class='card-desc'>Bars = Adj daily, this vs previous month; dotted = avg/day of the 5 months before.</div>",
                        unsafe_allow_html=True)
            st.plotly_chart(last_months_fig(comm), width="stretch")

# ---------------------------------------------------------------------------------------------
# TAB: PROJECTION ACCURACY
# ---------------------------------------------------------------------------------------------
@st.cache_data(ttl=600)
def pct_history() -> pd.Series:
    """Dispatched / Registered (all types together) from the desk Excel, Feb-Sep 2026."""
    if not PCT_HIST.exists():
        return pd.Series(dtype=float)
    return pd.read_csv(PCT_HIST, parse_dates=["date"]).set_index("date")["pct"]


def pct_live(data: pd.DataFrame, kind: str) -> pd.Series:
    """Dispatched / Registered per date from the entry table. kind = Total or one type. Types need both numbers."""
    types = ALL if kind == "Total" else [kind]
    reg = pd.concat([data[c] for c in types], axis=1)
    dis = pd.concat([data[DISP[c]] for c in types], axis=1)
    ok = reg.notna().values & dis.notna().values                  # only types that have both numbers that day
    num = (dis.fillna(0).values * ok).sum(axis=1)
    den = (reg.fillna(0).values * ok).sum(axis=1)
    out = pd.Series(num / den.clip(min=1e-9), index=data.index)
    return out[(den > 0) & ok.any(axis=1)]


def pct_by_month(kind: str) -> dict:
    """{(year, month): Series(day -> fraction)}. Excel history first, live entries overwrite per date."""
    s = pct_live(df, kind)
    if kind == "Total":
        s = pd.concat([pct_history(), s])
        s = s[~s.index.duplicated(keep="last")].sort_index()
    return {(y, m): g.set_axis(g.index.day) for (y, m), g in s.groupby([s.index.year, s.index.month])}


PASTEL = ["#f2a9a0", "#f4cf86", "#f2a9a0", "#b4bde6", "#a6d8b6", "#d8b4e2", "#f6bfd6", "#c3cfb8"]   # soft lines
PCT_NAVY = NAVY                                                                                  # selected month


def disp_numbers(kind: str) -> dict:
    """{(year, month): Series(day -> dispatched cumulative bags)}.
    History = Excel % x registered cumulative of that day (Arabica + Robusta). From Oct'26 = the dispatched numbers entered."""
    types = ALL if kind == "Total" else [kind]
    reg = pd.concat([df[c] for c in types], axis=1)
    dis = pd.concat([df[DISP[c]] for c in types], axis=1)
    ok = reg.notna().values & dis.notna().values
    live = pd.Series((dis.fillna(0).values * ok).sum(axis=1), index=df.index)[ok.any(axis=1)]
    s = live
    if kind == "Total":
        hp = pct_history()
        both = df[["Arabica", "Robusta"]].dropna()
        hist = (hp.reindex(both.index) * both.sum(axis=1)).dropna()
        s = pd.concat([hist, live])
        s = s[~s.index.duplicated(keep="last")].sort_index()
    return {(y, m): g.set_axis(g.index.day) for (y, m), g in s.groupby([s.index.year, s.index.month])}


def month_chart(data: dict, seq, sel, prior, connect, as_pct):
    """One chart: selected month bold, pastel lines for the others, teal bands + dotted average of the earlier months."""
    days = range(1, 32)
    pool = pd.DataFrame({ym: data[ym].reindex(days).interpolate(limit_area="inside") for ym in prior if ym in data})
    show_band = pool.shape[1] >= 3
    fig = go.Figure()
    band = None
    if show_band:
        cnt = pool.notna().sum(axis=1)
        band = pd.DataFrame({"lo": pool.min(axis=1), "hi": pool.max(axis=1), "p25": pool.quantile(0.25, axis=1),
                             "p75": pool.quantile(0.75, axis=1), "avg": pool.mean(axis=1)}).where(cnt >= 3)
        for lo, hi, colr, name in [("lo", "hi", "rgba(31,138,156,0.10)", "Min-Max"),
                                   ("p25", "p75", "rgba(31,138,156,0.26)", "25th-75th pct")]:
            fig.add_trace(go.Scatter(x=band.index, y=band[hi], line=dict(width=0), showlegend=False, hoverinfo="skip"))
            fig.add_trace(go.Scatter(x=band.index, y=band[lo], fill="tonexty", fillcolor=colr, line=dict(width=0),
                                     name=name, hoverinfo="skip"))
        fig.add_trace(go.Scatter(x=band.index, y=band["avg"], mode="lines", name=f"Avg of {pool.shape[1]} months",
                                 line=dict(color="#4a5578", width=1.6, dash="dot")))
    latest = max(seq)                                              # newest month shown = bold navy
    others = [ym for ym in seq if ym != latest]
    for k, ym in enumerate(seq):
        yy, mm = ym
        first = ym == latest
        h = data[ym].reindex(range(1, month_dim(yy, mm) + 1))
        colr = PCT_NAVY if first else PASTEL[(others.index(ym) + 1) % len(PASTEL)]
        fig.add_trace(go.Scatter(x=h.index, y=h.values, name=f"{MONTHS[mm - 1]}'{str(yy)[2:]}", mode="lines+markers",
                                 line=dict(color=colr, width=4.5 if first else 2.2, shape="spline", smoothing=0.4),
                                 marker=dict(size=9 if first else 5, color=colr, line=dict(color="#ffffff", width=1)),
                                 connectgaps=connect))
    if as_pct:
        chart_layout(fig, height=480, yaxis=dict(tickformat=".0%", hoverformat=".1%", range=[0, 1.02]))
    else:
        chart_layout(fig, height=480, yaxis=dict(tickformat=",", hoverformat=",.0f", rangemode="tozero"))
    return bottom_legend(fig), band


def by_day_table(data: dict, cols, sel, band, as_pct, title, desc):
    sel = max(cols)                                                # newest month = bold
    body = ""
    for d_ in range(1, 32):
        body += f"<tr><td class='dt'>{d_}</td>"
        for ym in cols:
            v = data.get(ym, pd.Series(dtype=float)).get(d_)
            txt = "" if v is None or pd.isna(v) else (f"{v:.0%}" if as_pct else f"{v:,.0f}")
            body += f"<td class='{'b' if ym == sel else ''}'>{txt}</td>"
        if band is not None:
            a = band["avg"].get(d_)
            txt = "" if a is None or pd.isna(a) else (f"{a:.0%}" if as_pct else f"{a:,.0f}")
            body += f"<td class='avgc'>{txt}</td>"
        body += "</tr>"
    head = "".join(f"<th>{MONTHS[mm - 1]}'{str(yy)[2:]}</th>" for yy, mm in cols) + ("<th>Avg</th>" if band is not None else "")
    st.markdown(f"<div class='card-title'>{title}</div><div class='card-desc'>{desc}</div>"
                f"<div style='overflow-x:auto'><table class='dtab'><tr class='sub'><th>Day</th>{head}</tr>{body}</table></div>",
                unsafe_allow_html=True)


def render_dispatched():
    oc = st.columns([2.6, 1.7, 1.6, 4], vertical_alignment="center")
    with oc[0]:
        kind = st.radio("Type", ["Total", *ALL], horizontal=True, label_visibility="collapsed", key="pct_kind")
    with oc[1]:
        span = st.radio("Months", ["Last 2", "All months"], horizontal=True, label_visibility="collapsed",
                        key="pct_span")
    with oc[2]:
        connect = st.toggle("Connect gaps", value=True, key="pct_connect")
    pct = pct_by_month(kind)
    num = disp_numbers(kind)
    if not pct:
        st.info("No dispatched numbers yet. Add them in the Entry tab (Disp columns)." if kind != "Total"
                else "No data yet.")
        return
    sel = (sel_y, sel_m)

    def pick(data):
        prior = sorted(ym for ym in data if ym < sel)
        if span == "Last 2":
            seq, y, m = [], sel_y, sel_m
            for _ in range(3):
                seq.append((y, m))
                m -= 1
                if m == 0:
                    y, m = y - 1, 12
            seq = [ym for ym in seq if ym in data]
        else:
            seq = ([sel] if sel in data else []) + list(reversed(prior))
        return seq, prior

    seq_p, prior_p = pick(pct)
    seq_n, prior_n = pick(num)
    if not seq_p:
        st.info(f"No dispatched % for {MON} or the 2 months before it yet.")
        return

    finals = [pct[ym].iloc[-1] for ym in prior_p if pct[ym].index.max() >= month_dim(*ym) - 3]
    finals_n = [num[ym].iloc[-1] for ym in prior_n if num[ym].index.max() >= month_dim(*ym) - 3]
    fig_p, band_p = month_chart(pct, seq_p, sel, prior_p, connect, True)
    fig_n, band_n = month_chart(num, seq_n, sel, prior_n, connect, False) if seq_n else (None, None)

    c1, c2 = st.columns(2, gap="medium")
    with c1, st.container(border=True):
        avg_txt = f" Average month-end <b>{sum(finals) / len(finals):.0%}</b> ({len(finals)} complete months)." if finals else ""
        st.markdown(f"<div class='card-title'>Dispatched / Registered <span class='pill'>{kind}</span></div>"
                    f"<div class='card-desc'>Daily, cumulative. Bands = earlier months.{avg_txt}</div>",
                    unsafe_allow_html=True)
        st.plotly_chart(fig_p, width="stretch")
    with c2, st.container(border=True):
        avg_n = f" Average month-end <b>{sum(finals_n) / len(finals_n):,.0f}</b>." if finals_n else ""
        st.markdown(f"<div class='card-title'>Dispatched, cumulative bags <span class='pill'>{kind}</span></div>"
                    "<div class='card-desc'>History = Dispatched % &times; registered that day (Arabica + Robusta); "
                    f"from Oct'26 the entered numbers.{avg_n}</div>", unsafe_allow_html=True)
        if fig_n is None:
            st.info("No dispatched numbers for these months yet.")
        else:
            st.plotly_chart(fig_n, width="stretch")

    t1, t2 = st.columns(2, gap="medium")
    with t1, st.container(border=True):
        by_day_table(pct, sorted(pct), sel, band_p, True, "Dispatched %, by day", "All months. Blank = not published that day.")
    with t2, st.container(border=True):
        if num:
            by_day_table(num, sorted(num), sel, band_n, False, "Dispatched bags, by day",
                         "All months, cumulative. Blank = not published that day.")


def render_accuracy():
    scope = st.radio("Months", ["All months", f"{MONTHS[sel_m - 1]} only"], horizontal=True,
                     label_visibility="collapsed", key="acc_scope")
    st.markdown("<div class='card-desc'>Linear projection vs actual month-end, by day. "
                "Uses only data known that day.</div>", unsafe_allow_html=True)
    ac = st.columns(2)
    for col_, comm in zip(ac, COMMS):
        a = accuracy_table(df, comm)
        if scope != "All months" and not a.empty:
            a = a[a.month == sel_m]
        with col_:
            if a.empty:
                st.info(f"{comm}: no complete months to test.")
                continue
            g = a.groupby("day")["err"].agg(miss=lambda v: v.abs().median(), bias="median",
                                            lo=lambda v: v.quantile(0.1), hi=lambda v: v.quantile(0.9))
            n_months = a[["year", "month"]].drop_duplicates().shape[0]
            st.markdown(f"<div class='chart-head'>{comm}: miss % by day</div>"
                        f"<div class='card-desc'>{n_months} months. + = projection too high.</div>",
                        unsafe_allow_html=True)
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=g.index, y=g.hi, line=dict(width=0), showlegend=False, hoverinfo="skip"))
            fig.add_trace(go.Scatter(x=g.index, y=g.lo, line=dict(width=0), fill="tonexty",
                                     fillcolor="rgba(31,138,156,0.16)", name="80% of months"))
            fig.add_trace(go.Scatter(x=g.index, y=g.bias, name="Typical miss", mode="lines+markers",
                                     line=dict(color=NAVY, width=3), marker=dict(size=6)))
            fig.add_hline(y=0, line=dict(color=GREY, width=1))
            chart_layout(fig, height=360, yaxis=dict(ticksuffix="%", tickformat=".0f", hoverformat=".1f"))
            st.plotly_chart(fig, width="stretch")
            body_ = ""
            for d_ in (5, 10, 15, 20, 25):
                if d_ in g.index:
                    r = g.loc[d_]
                    body_ += (f"<tr><td class='dt'>Day {d_}</td><td class='b'>{r.miss:.1f}%</td><td>{r.bias:+.1f}%</td>"
                              f"<td>{r.lo:+.0f}% to {r.hi:+.0f}%</td></tr>")
            st.markdown("<table class='dtab'><tr class='sub'><th>As of</th><th>Avg miss</th><th>Bias</th>"
                        "<th>80% range</th></tr>" + body_ + "</table>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------------------------
# TAB: ENTRY - writes a row to the CSV in GitHub
# ---------------------------------------------------------------------------------------------
REPO, REPO_PATH = "virataryaa/Daily-Cecafe", "Database/cecafe_daily.csv"
GH_API = f"https://api.github.com/repos/{REPO}/contents/{REPO_PATH}"
GH_COMMITS = f"https://api.github.com/repos/{REPO}/commits"
TZ = "Europe/Amsterdam"


class GitHubError(Exception):
    def __init__(self, msg, status=None):
        super().__init__(msg)
        self.status = status


@st.cache_resource
def gh_session():
    """One keep-alive HTTPS session for all GitHub calls (saves the TLS handshake on every save)."""
    s = requests.Session()
    tok = str(st.secrets["github_token"]).strip().strip('"').strip("'")
    s.headers.update({"Authorization": f"Bearer {tok}", "Accept": "application/vnd.github+json"})
    return s


@st.cache_resource
def gh_state():
    """Last known file content + sha, shared across reruns: a save needs just one PUT, not GET + PUT."""
    return {}


def gh_check(r):
    if r.status_code >= 400:
        try:
            msg = r.json().get("message", "")
        except ValueError:
            msg = r.text[:200]
        hint = {401: "token is wrong or expired - re-paste github_token in Secrets",
                403: "token has no write access - give it Contents: Read and write on Daily-Cecafe",
                404: "token cannot see the Daily-Cecafe repo - add this repo to the token",
                409: "file changed meanwhile - press Save again"}.get(r.status_code, "")
        raise GitHubError(f"GitHub {r.status_code}: {msg}. {hint}", r.status_code)


def gh_read():
    r = gh_session().get(GH_API, params={"ref": "main"}, timeout=20)
    gh_check(r)
    j = r.json()
    frame = pd.read_csv(io.StringIO(base64.b64decode(j["content"]).decode("utf-8")))
    gh_state().update(csv=frame, sha=j["sha"])
    return frame.copy(), j["sha"]


def gh_write(frame: pd.DataFrame, sha: str, msg: str):
    body = {"message": msg, "branch": "main", "sha": sha,
            "content": base64.b64encode(frame.to_csv(index=False, lineterminator="\n").encode()).decode()}
    r = gh_session().put(GH_API, json=body, timeout=20)
    gh_check(r)
    j = r.json()
    gh_state().update(csv=frame.copy(), sha=j["content"]["sha"])
    hist = gh_state().setdefault("history", [])
    hist.insert(0, (j["commit"]["committer"]["date"], msg))


@st.cache_data(ttl=300, show_spinner=False)
def _fetch_history():
    r = gh_session().get(GH_COMMITS, params={"path": REPO_PATH, "per_page": 30}, timeout=20)
    gh_check(r)
    return [(c["commit"]["committer"]["date"], c["commit"]["message"].split("\n")[0]) for c in r.json()]


def save_history():
    """Recent saves: fetched once, then new saves are added locally (no extra call per save)."""
    st_ = gh_state()
    if "history" not in st_:
        st_["history"] = _fetch_history()
    return st_["history"]


def parse_num(txt):
    if txt is None or (isinstance(txt, float) and pd.isna(txt)):     # a cleared grid cell comes back as None/NaN
        return None
    if isinstance(txt, (int, float)):
        return float(txt)
    txt = str(txt).replace(",", "").strip()
    return float(txt) if txt else None


def entry_enabled():
    try:
        return "github_token" in st.secrets
    except Exception:                       # no secrets file at all (local run)
        return False


def apply_entry(frame, d0, vals):
    frame = frame.copy()
    frame["date"] = pd.to_datetime(frame["date"])
    existed = (frame.date == d0).any()
    frame = frame[frame.date != d0]
    if any(v is not None for v in vals.values()):
        frame = pd.concat([frame, pd.DataFrame([{"date": d0, **vals}])])
    frame = frame.sort_values("date")
    frame = frame.reindex(columns=["date", *COLS])
    frame["date"] = frame["date"].dt.strftime("%Y-%m-%d")
    return frame, existed


@st.cache_data(ttl=600)
def max_daily(data: pd.DataFrame, comm: str):
    """Biggest Adj daily (bags/day) in history; None until a type has ~3 months of data."""
    s = data[comm].dropna()
    if s.empty or len({(d.year, d.month) for d in s.index}) < 3:
        return None
    peaks = [adjusted_daily(month_series(s, y, m)).max() for y, m in {(d.year, d.month) for d in s.index}]
    return float(max(peaks))


def value_notes(d0, vals):
    """Checks that need a second look: cumulative falling, or an implied day far above anything seen (extra zero)."""
    notes = []
    same_m = df[(df.index.year == d0.year) & (df.index.month == d0.month) & (df.index < d0)]
    for name, v in vals.items():
        if v is None:
            continue
        prev_v = same_m[name].dropna()
        if not prev_v.empty and v < prev_v.iloc[-1] * 0.95:
            notes.append(f"{name} {d0:%d-%b} {v:,.0f} is below the previous day ({prev_v.iloc[-1]:,.0f}).")
        cap = max_daily(df, name)
        base, base_day = (prev_v.iloc[-1], prev_v.index[-1].day) if not prev_v.empty else (0.0, 0)
        per_day = (v - base) / max(d0.day - base_day, 1)
        if cap and per_day > 1.5 * cap:
            notes.append(f"{name} {d0:%d-%b} {v:,.0f} means ~{per_day:,.0f} bags/day; "
                         f"highest ever is ~{cap:,.0f}/day. Extra zero?")
    return notes


def vals_text(vals, sep=", "):
    """Registered always; dispatched only where there is a number."""
    return sep.join(f"{c} {fmt(vals.get(c))}" for c in COLS if c in ALL or vals.get(c) is not None)


def commit_change(change, msg):
    """change(frame) -> (new_frame, info). One PUT using the cached sha; re-read once if the file moved on."""
    state = gh_state()
    frame, sha = (state["csv"], state["sha"]) if "sha" in state else gh_read()
    new_csv, info = change(frame)
    try:
        gh_write(new_csv, sha, msg)
    except GitHubError as ex:
        if ex.status not in (409, 422):
            raise
        frame, sha = gh_read()
        new_csv, info = change(frame)
        gh_write(new_csv, sha, msg)
    new_csv.to_csv(DATA, index=False, lineterminator="\n")             # show it now, before Cloud redeploys
    load.clear()
    return info


def render_history():
    if not entry_enabled():
        return
    try:
        hist = save_history()
    except (GitHubError, requests.RequestException) as ex:
        st.markdown(f"<div class='card-desc'>Not available: {ex}</div>",
                    unsafe_allow_html=True)
        return
    rows = ""
    for ts, msg in hist:
        if not msg.startswith(("Entry ", "Data update")):
            continue
        when = pd.Timestamp(ts).tz_convert(TZ)
        parts = [x.strip() for x in msg.split("|")]
        if msg.startswith("Entry "):
            for_date = pd.Timestamp(parts[0].split()[1]).strftime("%d-%b")
            vals = {k: v for k, v in (x.split(" ", 1) for x in parts[1:])}
            src = "Dashboard"
        else:
            for_date, vals, src = "-", {}, "Local push"
        rows += (f"<tr><td class='ts'>{when:%d %b %H:%M}</td><td class='dt'>{for_date}</td>"
                 + "".join(f"<td>{vals.get(c, '-')}</td>" for c in ALL) + f"<td class='ts'>{src}</td></tr>")
        if rows.count("<tr>") >= 10:
            break
    if rows:
        st.markdown(""
                    "<div class='card-desc'>Last 10 saves, Amsterdam time (CET).</div>"
                    "<table class='dtab'><tr class='sub'><th>Saved at</th><th>For</th>"
                    + "".join(f"<th>{c}</th>" for c in ALL) + "<th>Via</th></tr>" + rows + "</table>", unsafe_allow_html=True)


# ---------------------------------------------------------------------------------------------
# LAYOUT
# ---------------------------------------------------------------------------------------------
# main tabs (one underlined row); each one gets its own `if main == ...` block below.
MAIN = ["Daily Cecafe", "Monthly Cecafe"]
with st.container(key="main"):
    main = st.radio("Section", MAIN, horizontal=True, label_visibility="collapsed", key="main_tab")

if main == "Daily Cecafe":
    st.markdown(f"<div class='page-title'>Cecafe daily registrations <span class='pill'>{MON}</span></div>",
                unsafe_allow_html=True)
    # one row: pill tabs on the left (a radio, so only the open page is computed), month dropdown on the right
    nav_l, nav_r = st.columns([3.6, 1.5], vertical_alignment="center")
    with nav_l, st.container(key="nav"):
        page = st.radio("Page", ["Entry", "Registrations", "Dispatched", "Advanced Study"], horizontal=True,
                        label_visibility="collapsed", key="page")
    with nav_r, st.container(key="monthsel"):
        st.selectbox("Month", MONTH_CHOICES, key="month_sel", label_visibility="collapsed",
                     format_func=lambda s: f"Month  |  {s}")
    if page == "Entry":
        le, ri = st.columns([1, 1.05], gap="medium")
        with le, st.container(border=True):
            render_entry_grid()
        with ri, st.container(border=True):
            render_table()
        if entry_enabled():
            with st.expander("Save history", expanded=False):
                render_history()
    elif page == "Registrations":
        oc = st.columns([1.2, 1.8, 5], vertical_alignment="center")
        with oc[0]:
            yrs = st.radio("Years", ["Last 2", "All"], horizontal=True, label_visibility="collapsed", key="years")
        with oc[1]:
            connect = st.toggle("Connect gaps", value=True, help="Draw lines across days Cecafe did not publish.")
        min_year = max(sel_y - 2, first_year) if yrs == "Last 2" else first_year          # charts: Last 2 / All
        render_visuals()
        min_year = first_year                                                              # tables: every year
        render_history_tables()
    elif page == "Dispatched":
        render_dispatched()
    else:
        render_accuracy()
        st.markdown(
            "<div class='card-desc' style='margin-top:14px; line-height:1.6'><b>How this is made.</b> "
            "For every past month that is complete, we take the linear projection as it stood on each day "
            "(registered so far &divide; day number &times; days in the month) and compare it with that month's real "
            "final total. Miss % = projection &divide; actual &minus; 1. Only numbers known on that day are used. "
            "The dark line is the typical (median) miss for that day across all months; the shaded band holds the "
            "middle 80% of months. In the table, <i>Avg miss</i> is the typical size of the error and <i>Bias</i> is its "
            "direction (+ means the projection was too high).</div>", unsafe_allow_html=True)
elif main == "Monthly Cecafe":
    import monthly
    monthly.render()

for _k in KEEP:                                                # remember the values for the next run
    if _k in st.session_state:
        st.session_state[f"_keep_{_k}"] = st.session_state[_k]
