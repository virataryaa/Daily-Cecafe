"""Exports To Destination: Brazil green coffee exports by Type x Destination (Cecafe monthly), crop year Jul-Jun.

Same visuals as the Monthly Cecafe tab (monthly.py) plus a destination ranking. Data = Database/cecafe_destinations.csv,
built from Database/Cecafe Monthly.xlsx by Automator/build_destinations.py (run by publish_update.bat). Bags in K.
"""
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

DATA = Path(__file__).resolve().parent.parent / "Database" / "cecafe_destinations.csv"
TOTAL = "Total"
EUROPE_LABEL = "Europe (UK incl.)"
EUROPE_MEMBERS = ["Belgium", "Germany", "Italy", "Netherlands", "Spain", "UK"]

MONTHS = ["Jul", "Aug", "Sep", "Oct", "Nov", "Dec", "Jan", "Feb", "Mar", "Apr", "May", "Jun"]   # crop month 1-12
CAL = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
START = 7                                                          # calendar month the crop year starts in
CY_PRESETS = {"Jul–Jun": 7, "Oct–Sep": 10, "Apr–Mar": 4}           # Cecafe / ICO / Conab
TYPES = {"Arabica": ["Arabica"], "Robusta": ["Robusta"], "Arabica + Robusta": ["Arabica", "Robusta"]}
UNITS = {"'000 bags": (1.0, ",.0f"), "Bags": (1e3, ",.0f"), "Million bags": (1e-3, ",.2f")}   # source is K bags
PROJ_METHODS = ["Off", "YoY %", "Seasonal share", "Monthly value", "Full-year target"]

NAVY, TEAL, GREEN, RED, AMBER, GREY = "#0a2463", "#1f8a9c", "#1f9d6f", "#c94a4a", "#c98a1f", "#8a94a8"
INK, AXIS, GRID = "#1a1a2e", "#4a5578", "rgba(10,36,99,0.08)"
OLDER = [TEAL, AMBER, GREEN, "#6b7fb8", GREY, "#8fc7d0", "#e2c38a", "#9fd1bb", "#b9c3de"]
SEQ = ["#ffffff", "#f2f9f5", "#e3f3ea", "#cfeadc", "#b6dec9", "#99cfb3", "#7bbf9c"]   # soft greens

CSS = """
<style>
[data-testid="stAppViewContainer"], [data-testid="stMain"], .main { background: #fafafa !important; }
[data-testid="stHeader"] { background: #fafafa !important; }
body, .main { color: #1a1a2e; }
h1, h2, h3, h4, h5, h6 { color: #0a2463 !important; }
.block-container { padding-top: 2.2rem; max-width: 1700px; }

div[role="radiogroup"] { background: #eef0f6; padding: 4px; border-radius: 999px; gap: 2px; display: inline-flex; flex-wrap: wrap; }
div[role="radiogroup"] label { background: transparent !important; border-radius: 999px !important; padding: 4px 12px !important; margin: 0 !important; }
div[role="radiogroup"] label[data-baseweb="radio"] > div:first-child { display: none; }
div[role="radiogroup"] label div[data-testid="stMarkdownContainer"] p { font-size: 12px !important; color: #5a6688; }
div[role="radiogroup"] label:has(input:checked) { background: #0a2463 !important; }
div[role="radiogroup"] label:has(input:checked) div[data-testid="stMarkdownContainer"] p { color: #ffffff !important; font-weight: 600; }

[data-baseweb="popover"] [data-baseweb="menu"] { background: #ffffff !important; }
[data-baseweb="popover"] [data-baseweb="menu"] li, [data-baseweb="popover"] [data-baseweb="menu"] li * { color: #1a1a2e !important; }
[data-baseweb="select"] > div { background: #ffffff !important; color: #1a1a2e !important; }

.card-desc { color: #5a6688; font-size: 0.82rem; margin-top: -6px; margin-bottom: 10px; }
.chart-head { color: #0a2463; font-weight: 600; font-size: 0.95rem; margin-bottom: 0; }

.tbl-wrap { overflow-x: auto; border: 1px solid #dfe3ee; border-radius: 8px; background: #ffffff;
    width: fit-content; max-width: 100%; margin: 0 auto 4px; }
.tbl { border-collapse: collapse; font-size: 11.5px; line-height: 1.25; font-variant-numeric: tabular-nums; }
.tbl th { background: #eef0f6; color: #0a2463; font-weight: 600; padding: 3px 9px; font-size: 11px; text-align: center; white-space: nowrap; }
.tbl th:first-child { text-align: left; }
.tbl td { padding: 2px 9px; text-align: center; white-space: nowrap; border-bottom: 1px solid #f0f2f6; color: #1a1a2e; }
.tbl td.lbl { text-align: left; font-weight: 600; background: #f7f8fb; border-right: 1px solid #dfe3ee; color: #0a2463; }
.tbl td.x { border-left: 2px solid #dfe3ee; font-weight: 700; background: #f7f8fb; }
.tbl tr.ref td { background: #f4f6fa; color: #4a5578; font-style: italic; }
.tbl tr.sep td { height: 3px; padding: 0; background: #eef0f6; border: none; }
.tbl tr.hl td { background: #eef2fb; }
.tbl td.up { color: #1f9d6f; font-weight: 700; }
.tbl td.down { color: #c94a4a; font-weight: 700; }
.tbl-head { text-align: center; margin-top: 4px; }

.st-key-dx_filters [data-testid="stWidgetLabel"] { min-height: 0; margin-bottom: 4px; }
.st-key-dx_filters [data-testid="stWidgetLabel"] p, .dx-lbl { font-size: 10.5px !important; font-weight: 700;
    letter-spacing: .08em; text-transform: uppercase; color: #0a2463 !important; margin: 0 0 4px; }
.st-key-dx_filters { background: #ffffff; border: 1px solid #e6eaf2 !important; border-radius: 12px !important; }
.st-key-dx_proj button { min-height: 34px !important; border-radius: 999px !important; padding: 4px 16px !important;
    background: #f8f9fc !important; border: 1px solid #e3e7ef !important; box-shadow: none !important; }
.st-key-dx_proj button p { font-size: 12.5px !important; font-weight: 600; color: #3d4a6b !important; }
.st-key-dxproj_on .st-key-dx_proj button { background: #eef2fb !important; border-color: #b9c6e6 !important; }
.st-key-dxproj_on .st-key-dx_proj button p { color: #0a2463 !important; }
[data-testid="stVerticalBlock"]:has(> .st-key-dx_view), [data-testid="stVerticalBlock"]:has(> .st-key-dx_cumview),
[data-testid="stVerticalBlock"]:has(> .st-key-dx_roll) { align-items: flex-end; }

.dx-rule { border-top: 1px solid #dfe3ee; margin: 22px 0 0; }
.dx-sec { font-size: 18px; font-weight: 700; color: #0a2463; text-align: center; letter-spacing: .01em; margin: 6px 0 8px; }

.dx-hero { background: linear-gradient(135deg, #050f2c 0%, #0a1d4d 100%); border-radius: 14px; padding: 14px 22px;
    margin-bottom: 10px; box-shadow: 0 2px 10px rgba(10,36,99,.18); display: flex; align-items: baseline;
    justify-content: space-between; flex-wrap: wrap; gap: 8px; }
.dx-hero-t { color: #ffffff; font-size: 24px; font-weight: 700; letter-spacing: .01em; line-height: 1.3; }
.dx-hero-s { color: #c9d3ea; font-size: 12.5px; }
.dx-hero-s b { color: #ffffff; }
[class*="st-key-dx_card_"] { background: #ffffff; border: 1px solid #e6eaf2 !important; border-radius: 12px !important;
    padding: 12px 16px 6px !important; box-shadow: 0 1px 3px rgba(10,36,99,.05); }
[class*="st-key-dx_card_"] .card-desc { margin-bottom: 0; }
</style>
"""


# ── Colour / table / chart helpers (same as Cecafe Daily monthly.py) ──────────
def _lerp(pal, t):
    t = max(0.0, min(1.0, t))
    n = len(pal) - 1
    i = min(int(t * n), n - 1)
    f = t * n - i
    a = [int(pal[i][k:k + 2], 16) for k in (1, 3, 5)]
    b = [int(pal[i + 1][k:k + 2], 16) for k in (1, 3, 5)]
    return "#" + "".join(f"{int(x + f * (y - x)):02x}" for x, y in zip(a, b))


def seq_color(v, lo, hi):
    return SEQ[0] if hi <= lo else _lerp(SEQ, (v - lo) / (hi - lo))


def text_on(bg):
    r, g, b = (int(bg[k:k + 2], 16) for k in (1, 3, 5))
    return INK if (0.299 * r + 0.587 * g + 0.114 * b) / 255 > 0.58 else "#ffffff"


def rgba(hex_, a):
    r, g, b = (int(hex_[k:k + 2], 16) for k in (1, 3, 5))
    return f"rgba({r},{g},{b},{a})"


def year_styles(years):
    """Latest = navy bold, previous = red, older = muted (thin)."""
    ys = sorted(years, key=_cy_y0, reverse=True)
    out = {y: (OLDER[i % len(OLDER)], 1.3) for i, y in enumerate(ys[2:])}
    if len(ys) >= 2:
        out[ys[1]] = (RED, 2.0)
    if ys:
        out[ys[0]] = (NAVY, 3.0)
    return out


def t_cell(text="", cls="", bg=None):
    style = f" style='background:{bg};color:{text_on(bg)}'" if bg else ""
    c = f" class='{cls}'" if cls else ""
    return f"<td{c}{style}>{text}</td>"


def t_row(label, cells, kind=""):
    k = f" class='{kind}'" if kind else ""
    return f"<tr{k}><td class='lbl'>{label}</td>{''.join(cells)}</tr>"


def t_sep(ncols):
    return f"<tr class='sep'><td colspan='{ncols}'></td></tr>"


def t_render(header, rows, corner=""):
    head = "<tr>" + f"<th>{corner}</th>" + "".join(f"<th>{h}</th>" for h in header) + "</tr>"
    st.markdown(f"<div class='tbl-wrap'><table class='tbl'>{head}{''.join(rows)}</table></div>",
                unsafe_allow_html=True)


def chart_head(title, desc, control):
    h, w = st.columns([1, 1], vertical_alignment="center")
    h.markdown(f"<div class='chart-head'>{title}</div>", unsafe_allow_html=True)
    out = control(w)
    st.markdown(f"<div class='card-desc'>{desc}</div>", unsafe_allow_html=True)
    return out


def card_head(title, desc=""):
    st.markdown(f"<div class='tbl-head'><div class='chart-head'>{title}</div>"
                + (f"<div class='card-desc'>{desc}</div>" if desc else "") + "</div>", unsafe_allow_html=True)


def section(label=""):
    lab = f"<div class='dx-sec'>{label}</div>" if label else ""
    st.markdown(f"<div class='dx-rule'></div>{lab}", unsafe_allow_html=True)


def style(fig, height=340, legend="bottom", months=None, unified=False, fmt=",.0f", short=False, **extra):
    xaxis = dict(gridcolor=GRID, color=AXIS, showgrid=False)
    if months:
        xaxis.update(categoryorder="array", categoryarray=months)
    xaxis.update(extra.pop("xaxis", {}))
    yaxis = dict(gridcolor=GRID, color=AXIS, hoverformat=fmt, tickformat="~s" if short else fmt,
                 separatethousands=True)
    yaxis.update(extra.pop("yaxis", {}))
    margin = dict(t=14, b=30, l=10, r=10)
    leg = dict(bgcolor="rgba(0,0,0,0)", orientation="h", x=0, font=dict(size=10), itemwidth=30)
    if legend == "bottom":
        leg.update(y=-0.15, yanchor="top")
        margin["b"] = 60
    elif legend == "top":
        leg.update(y=1.0, yanchor="bottom")
        margin["t"] = 30
    fig.update_layout(template="plotly_white", height=height, paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)", font=dict(color=INK), legend=leg, showlegend=legend is not None,
                      xaxis=xaxis, yaxis=yaxis, margin=margin, hovermode="x unified" if unified else "closest", **extra)
    return fig


def show(fig, key):
    return st.plotly_chart(fig, width="stretch", key=key,
                           config={"displaylogo": False, "modeBarButtonsToRemove": ["select2d", "lasso2d"]})


def seed(key, value):
    if key not in st.session_state:
        st.session_state[key] = value


# ── Data ──────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=600)
def load_raw() -> pd.DataFrame:
    df = pd.read_csv(DATA)
    df["CropYear"] = [f"{(y if m >= 7 else y - 1) % 100:02d}/{(y + 1 if m >= 7 else y) % 100:02d}"
                      for y, m in zip(df["Year"], df["Month"])]
    return df


def destinations_for_type(df, type_):
    """Destinations with at least one reported month for this Type (Arabica never ships to Vietnam, etc.)."""
    d = df[(df["Type"] == type_) & df["Bags (K)"].notna()]["Destination"].unique()
    return sorted(x for x in d if x != TOTAL)


def _cy_y0(cy: str) -> int:
    """First calendar year of a crop-year label: '26/27' -> 2026, '2026' (Jan-Dec basis) -> 2026."""
    return int(cy) if len(cy) == 4 else 2000 + int(cy[:2])


@st.cache_data(ttl=600)
def long_for(dest: str) -> pd.DataFrame:
    """One destination (Europe = sum of its members) -> commodity, crop_year (Jul-Jun), cm (1 = Jul), bags (K)."""
    df = load_raw()
    mask = df["Destination"].isin(EUROPE_MEMBERS) if dest == EUROPE_LABEL else df["Destination"] == dest
    d = (df[mask & df["Bags (K)"].notna()].groupby(["Type", "CropYear", "Month"], as_index=False)["Bags (K)"].sum())
    return pd.DataFrame({"commodity": d["Type"], "crop_year": d["CropYear"],
                         "cm": (d["Month"] - 7) % 12 + 1, "bags": d["Bags (K)"]})


def recrop(raw: pd.DataFrame, start: int) -> pd.DataFrame:
    """Re-label the Jul-Jun rows onto a crop year starting in calendar month `start`.
    A leading crop year the data only partly covers is dropped."""
    if start == 7 or raw.empty:
        return raw
    d = raw.copy()
    y0 = d["crop_year"].map(_cy_y0)
    cal = (d["cm"] + 5) % 12 + 1
    year = y0 + (d["cm"] > 6).astype(int)
    ny0 = year - (cal < start).astype(int)
    d["cm"] = (cal - start) % 12 + 1
    d["crop_year"] = ny0.map(lambda y: f"{y % 100:02d}/{(y + 1) % 100:02d}")
    first = min(d["crop_year"], key=_cy_y0)
    if d.loc[d["crop_year"] == first, "cm"].min() > 1:
        d = d[d["crop_year"] != first]
    return d


def pivot(raw: pd.DataFrame, comm: str, factor: float) -> pd.DataFrame:
    """crop year x crop month (1-12) in the chosen unit. A combination adds the types month by month
    (a type with no shipments to this destination counts as 0); NaN = nothing reported."""
    d = raw[raw["commodity"].isin(TYPES[comm])]
    if d.empty:
        return pd.DataFrame(columns=range(1, 13), dtype=float)
    p = d.pivot_table(index="crop_year", columns="cm", values="bags", aggfunc="sum").reindex(columns=range(1, 13))
    p = p.loc[sorted(p.index, key=_cy_y0)]
    return p.dropna(how="all") * factor


def month_dates(cy: str, cm: int) -> pd.Timestamp:
    k = START - 1 + cm - 1
    return pd.Timestamp(_cy_y0(cy) + k // 12, k % 12 + 1, 1)


def _cv(v, unit, fmt):
    """Compact value for on-chart labels: 10.7M in Bags, else the unit's own format."""
    return f"{v / 1e6:.1f}M" if unit == "Bags" else format(v, fmt)


# ── Page ──────────────────────────────────────────────────────────────────────
def render():
    global MONTHS, START
    st.markdown(CSS, unsafe_allow_html=True)
    df = load_raw()
    last = df.loc[df["Bags (K)"].notna()].sort_values(["Year", "Month"]).iloc[-1]
    hero = st.empty()

    with st.container(border=True, key="dx_filters"):
        b0, b2, b3, b4, b5 = st.columns([2.2, 1.45, 1.75, 1.6, 0.8], vertical_alignment="bottom")
        comm = b0.radio("Type", list(TYPES), horizontal=True, key="dx_comm")
        dests = [TOTAL, EUROPE_LABEL] + sorted(set().union(*[destinations_for_type(df, t) for t in TYPES[comm]]))
        if st.session_state.get("dx_dest") not in dests:
            st.session_state["dx_dest"] = "Belgium" if "Belgium" in dests else TOTAL
        span = b2.radio("Years", ["Last 5", "Last 10", "All"], horizontal=True, key="dx_span")
        unit = b3.radio("Unit", list(UNITS), horizontal=True, key="dx_unit")
        basis = b4.radio("Crop year", list(CY_PRESETS), horizontal=True, key="dx_cy")
        dest = st.radio("Destination", dests, horizontal=True, key="dx_dest",
                        format_func=lambda d: "All (Total)" if d == TOTAL else d)

    start = CY_PRESETS[basis]
    START, MONTHS = start, [CAL[(start - 1 + i) % 12] for i in range(12)]
    where = "all destinations" if dest == TOTAL else dest
    hero.markdown(f"<div class='dx-hero'><span class='dx-hero-t'>{comm} Exports · {where}</span>"
                  f"<span class='dx-hero-s'>Cecafe · Brazil green coffee · data to "
                  f"<b>{pd.Timestamp(int(last['Year']), int(last['Month']), 1):%b %Y}</b></span></div>",
                  unsafe_allow_html=True)

    raw = recrop(long_for(dest), start)
    ctx = _context(raw, comm, unit, span, dest)
    if ctx is None:
        st.info("No data for this selection.")
        return
    with b5:
        st.markdown("<div class='dx-lbl'>Projection</div>", unsafe_allow_html=True)
        with st.container(key=f"dxproj_{'off' if st.session_state.get('dx_pj_method', 'Off') == 'Off' else 'on'}"):
            proj = _projection(ctx)

    _charts(ctx, proj)
    t_col, p_col, y_col = st.columns([2.7, 0.9, 0.9], gap="medium")
    with t_col, st.container(border=True, key="dx_card_table"):
        card_head(f"{comm} Monthly Exports · {where}", ctx["u_desc"])
        _heatmap(ctx)
    with p_col, st.container(border=True, key="dx_card_pace"):
        _pace(ctx, proj)
    with y_col, st.container(border=True, key="dx_card_ytd"):
        _ytd(ctx)

    section("Destinations")
    _destinations(df, comm, unit, start)
    _split(df, comm, unit, start)

    section("Excess vs Normal")
    _excess(df)


def _context(raw, comm, unit, span, dest):
    factor, fmt = UNITS[unit]
    piv = pivot(raw, comm, factor)
    if piv.empty:
        return None
    years = piv.index.tolist()
    latest_cy = years[-1]
    valid = piv.loc[latest_cy].dropna().index
    common = int(valid.max()) if len(valid) else 12
    ytd = piv[list(range(1, common + 1))].sum(axis=1, min_count=1)
    n_show = {"Last 5": 5, "Last 10": 10, "All": len(years)}[span]
    parts = {}
    if len(TYPES[comm]) > 1:
        for c in TYPES[comm]:
            pc = pivot(raw, c, factor)
            if not pc.empty:
                parts[c] = pc.reindex(piv.index).where(piv.notna())
    ref = [y for y in years if y != latest_cy and piv.loc[y].notna().sum() >= 10][-10:]   # last 10 (near-)full years
    return dict(parts=parts, comm=comm, dest=dest, unit=unit, fmt=fmt, piv=piv, years=years, latest_cy=latest_cy,
                prev_cy=years[-2] if len(years) >= 2 else None, common=common, ref=ref, ytd=ytd,
                yoy=ytd.pct_change(fill_method=None) * 100, cut=f"{MONTHS[0]}–{MONTHS[common - 1]}",
                shown=years[-n_show:], u_desc=unit)


def _last_dot(fig, x, y, text, pos):
    fig.add_trace(go.Scatter(x=[x], y=[y], mode="markers+text", text=[text], textposition=pos,
                             marker=dict(color=NAVY, size=8, line=dict(color="#ffffff", width=1.5)),
                             textfont=dict(size=10.5, color=NAVY), showlegend=False, hoverinfo="skip",
                             cliponaxis=False))


def _charts(ctx, proj):
    piv, years, latest_cy, prev_cy, common, ref, ytd, shown, unit, fmt, comm = (
        ctx[k_] for k_ in ("piv", "years", "latest_cy", "prev_cy", "common", "ref", "ytd", "shown", "unit", "fmt",
                           "comm"))
    styles = year_styles(sorted(set(shown) | set(years[-3:])))
    ht = f"%{{y:{fmt}}} {unit}"
    short = unit == "Bags"
    grey = "<span style='color:#7a86a8'>{}</span>"
    H = 500
    l, mid, r = st.columns(3, gap="medium")
    with l, st.container(border=True, key="dx_card_monthly"):
        view = chart_head(f"{comm} Monthly Exports", f"{unit} · bands = L{len(ref)}Y min-max and percentiles",
                          lambda w: w.radio("Seasonal view", ["Latest vs range", "All years"], horizontal=True,
                                            key="dx_view", label_visibility="collapsed"))
        plot_years = shown if view == "All years" else [y for y in shown if y in (latest_cy, prev_cy)]
        fig = go.Figure()
        if len(ref) >= 2:
            _band(fig, piv.loc[ref], len(ref), fmt)
        for y in plot_years:
            c, wd = styles[y]
            s_ = piv.loc[y].dropna()
            fig.add_trace(go.Scatter(x=[MONTHS[m - 1] for m in s_.index], y=s_.values, name=y, mode="lines",
                                     line=dict(color=c, width=wd), hovertemplate=ht))
        if proj and latest_cy in shown:
            xs = [MONTHS[common - 1]] + [MONTHS[m - 1] for m in proj]
            fig.add_trace(_proj_trace(xs, [piv.loc[latest_cy, common]] + list(proj.values()), latest_cy, ht))
        if latest_cy in plot_years:
            s_ = piv.loc[latest_cy].dropna()
            m = int(s_.index.max())
            _last_dot(fig, MONTHS[m - 1], s_[m], f"<b>{_cv(s_[m], unit, fmt)}</b> {grey.format(MONTHS[m - 1])}",
                      "top right")
        show(style(fig, height=H, legend="top", months=MONTHS, unified=True, fmt=fmt, short=short), key="dx_seasonal")

    with mid, st.container(border=True, key="dx_card_cum"):
        cview = chart_head(f"{comm} Cumulative Exports", f"{unit} · bands = L{len(ref)}Y cumulative",
                           lambda w: w.radio("Cumulative view", ["Last 4", "All"], horizontal=True,
                                             key="dx_cumview", label_visibility="collapsed"))
        fig = go.Figure()
        if len(ref) >= 2:
            _band(fig, piv.loc[ref].cumsum(axis=1), len(ref), fmt)
        cum_years = years[-4:] if cview == "Last 4" else years
        older = [y for y in cum_years if y not in (latest_cy, prev_cy)]
        for y in cum_years:
            c, wd = styles[y] if y in (latest_cy, prev_cy) else (OLDER[older.index(y) % len(OLDER)], 1.3)
            s_ = piv.loc[y].dropna().cumsum()
            fig.add_trace(go.Scatter(x=[MONTHS[m - 1] for m in s_.index], y=s_.values, name=y, mode="lines",
                                     line=dict(color=c, width=wd), hovertemplate=ht))
        if proj:
            run = float(ytd[latest_cy])
            xs, ys = [MONTHS[common - 1]], [run]
            for m, v in proj.items():
                run += v
                xs.append(MONTHS[m - 1])
                ys.append(run)
            fig.add_trace(_proj_trace(xs, ys, latest_cy, ht))
        s_ = piv.loc[latest_cy].dropna().cumsum()
        if len(s_):
            m = int(s_.index.max())
            _last_dot(fig, MONTHS[m - 1], s_[m], f"<b>{_cv(s_[m], unit, fmt)}</b> {grey.format(MONTHS[m - 1])}",
                      "top left")
        show(style(fig, height=H, legend="top", months=MONTHS, unified=True, fmt=fmt, short=short), key="dx_cum")

    with r, st.container(border=True, key="dx_card_rolling"):
        seed("dx_roll", "12m")
        win = chart_head(f"{comm} Rolling Exports", f"{unit} · trailing sum",
                         lambda w: w.radio("Window", ["1m", "3m", "6m", "12m"], horizontal=True, key="dx_roll",
                                           label_visibility="collapsed"))

        def rolling(pv):
            stack = pv.stack().dropna()
            mon = pd.Series(stack.values, index=[month_dates(cy, int(cm)) for cy, cm in stack.index]).sort_index()
            mon = mon.reindex(pd.date_range(mon.index.min(), mon.index.max(), freq="MS"), fill_value=0.0)
            return mon.rolling(int(win[:-1])).sum().dropna()
        parts = ctx["parts"]
        roll = rolling(piv)
        floor = float(roll.min()) - 0.05 * float(roll.max() - roll.min())
        fig = go.Figure(go.Scatter(x=roll.index, y=[floor] * len(roll), mode="lines", line=dict(width=0),
                                   showlegend=False, hoverinfo="skip"))
        fig.add_trace(go.Scatter(x=roll.index, y=roll.values, mode="lines", line=dict(color=TEAL, width=2),
                                 fill="tonexty", fillcolor=rgba(TEAL, 0.08), name="Combined" if parts else "Rolling",
                                 hovertemplate=f"%{{x|%b-%y}}: %{{y:{fmt}}} {unit}<extra></extra>"))
        pal = {"Arabica": NAVY, "Robusta": AMBER}
        if len(parts) > 1:
            for c, pv in parts.items():
                rc = rolling(pv)
                fig.add_trace(go.Scatter(x=rc.index, y=rc.values, mode="lines", name=c, line=dict(color=pal[c], width=1.8),
                                         hovertemplate=f"{c} %{{x|%b-%y}}: %{{y:{fmt}}} {unit}<extra></extra>"))
        if len(roll):
            _last_dot(fig, roll.index[-1], roll.iloc[-1],
                      f"<b>{_cv(roll.iloc[-1], unit, fmt)}</b> {grey.format(f'{roll.index[-1]:%b-%y}')}", "top left")
        show(style(fig, height=H, legend="top" if len(parts) > 1 else None, fmt=fmt, short=short,
                   yaxis=dict(autorange=True, rangemode="normal")), key="dx_rolling")


def _ytd(ctx):
    years, latest_cy, ytd, yoy, cut, shown, unit, fmt = (
        ctx[k_] for k_ in ("years", "latest_cy", "ytd", "yoy", "cut", "shown", "unit", "fmt"))
    card_head(f"{ctx['comm']} YTD {cut}", f"{unit} · label = YoY")
    yy = [y for y in years if y in shown or y == latest_cy]
    colors = [NAVY if y == latest_cy else "#c3cbe0" for y in yy]
    fig = go.Figure(go.Bar(x=yy, y=ytd[yy].values, marker_color=colors,
                           hovertemplate=f"%{{x}}: %{{y:{fmt}}} {unit}<extra></extra>"))
    for y in yy:
        v = ytd[y]
        if pd.isna(v):
            continue
        latest = y == latest_cy
        lab = f"{yoy[y]:+.1f}%" if pd.notna(yoy[y]) else ""
        tot_txt = f"<b>{_cv(v, unit, fmt)}</b>" if latest else _cv(v, unit, fmt)
        yo_txt = (f"<br><span style='color:{GREEN if lab.startswith('+') else RED};font-size:10px'><b>{lab}</b></span>"
                  if lab else "")
        fig.add_annotation(x=y, y=v, text=tot_txt + yo_txt, showarrow=False, yanchor="bottom", yshift=3,
                           font=dict(size=11 if latest else 9.5, color=NAVY if latest else AXIS))
    show(style(fig, height=max(260, 40 + (len(yy) + 5) * 18), legend=None, fmt=fmt, short=unit == "Bags",
               bargap=0.45, yaxis=dict(rangemode="tozero")), key="dx_ytd")


def _pace(ctx, proj):
    """Full-year totals. The running year = YTD (solid) + projected rest (light): the Projection when one is on,
    otherwise seasonal share (L5Y). Whisker = 10th-90th pct of YTD / each complete year's share by now."""
    piv, years, latest_cy, common, ref, ytd, shown, unit, fmt = (
        ctx[k_] for k_ in ("piv", "years", "latest_cy", "common", "ref", "ytd", "shown", "unit", "fmt"))
    c = lambda v: _cv(v, unit, fmt)
    full = [y for y in ref if piv.loc[y].notna().all()]
    yy = [y for y in years if y in shown or y == latest_cy]
    tot = piv.sum(axis=1, min_count=1)
    now = float(ytd[latest_cy]) if pd.notna(ytd[latest_cy]) else 0.0

    center, lo, hi, method = np.nan, np.nan, np.nan, ""
    if common < 12 and len(full) >= 2:
        tf = piv.loc[full].sum(axis=1)
        shares = piv.loc[full, list(range(1, common + 1))].sum(axis=1) / tf
        est = now / shares[shares > 0]
        if len(est):
            lo, hi = float(est.quantile(0.10)), float(est.quantile(0.90))
            if proj:
                center, method = now + float(sum(proj.values())), f"projection: {st.session_state.get('dx_pj_method', '')}"
            else:
                sh5 = float(shares[full[-5:]].mean())
                center, method = (now / sh5 if sh5 > 0 else np.nan), "seasonal share (L5Y)"

    card_head(f"{ctx['comm']} Full-Year Totals",
              f"{latest_cy} = YTD + {method}" if pd.notna(center) else "Complete crop years")
    full_yy = [y for y in yy if y != latest_cy or common >= 12]
    fig = go.Figure(go.Bar(x=full_yy, y=tot[full_yy].values, marker=dict(color="#c3cbe0", line=dict(width=0)),
                           text=[c(tot[y]) if pd.notna(tot[y]) else "" for y in full_yy],
                           textposition="outside", textfont=dict(size=9, color=AXIS), cliponaxis=False,
                           hovertemplate=f"%{{x}}: %{{y:{fmt}}} {unit}<extra></extra>", name="Full year"))
    if pd.notna(center):
        fig.add_trace(go.Bar(x=[latest_cy], y=[now], marker=dict(color=NAVY, line=dict(width=0)), name="YTD",
                             hovertemplate=f"YTD: %{{y:{fmt}}} {unit}<extra></extra>"))
        fig.add_trace(go.Bar(x=[latest_cy], y=[max(center - now, 0)], name="Projected",
                             marker=dict(color=rgba(NAVY, 0.22), line=dict(color=NAVY, width=1)),
                             error_y=dict(type="data", symmetric=False, array=[max(hi - center, 0)],
                                          arrayminus=[max(center - lo, 0)], color=NAVY, thickness=1.5, width=6),
                             text=[f"<b>{c(center)}</b>"], textposition="outside", textfont=dict(size=10, color=NAVY),
                             cliponaxis=False,
                             hovertemplate=(f"Projected full year: {format(center, fmt)} {unit}<br>"
                                            f"Range: {format(lo, fmt)} – {format(hi, fmt)}<extra></extra>")))
    show(style(fig, height=max(260, 40 + (len(yy) + 5) * 18), legend=None, fmt=fmt, short=unit == "Bags",
               barmode="stack", bargap=0.35, yaxis=dict(rangemode="tozero")), key="dx_pace")
    if pd.notna(center):
        st.markdown(f"<div class='card-desc' style='text-align:center'>Low–high {c(lo)} – {c(hi)} "
                    f"(10th–90th pct, last {len(full)} years' seasonality)</div>", unsafe_allow_html=True)


def _band(fig, b, n, fmt):
    """Light teal bands: min-max, 10th-90th and 25th-75th percentile, plus the average."""
    x = MONTHS
    for lo, hi, a in [(b.min(), b.max(), 0.08), (b.quantile(0.10), b.quantile(0.90), 0.16),
                      (b.quantile(0.25), b.quantile(0.75), 0.30)]:
        fig.add_trace(go.Scatter(x=x, y=hi.values, mode="lines", showlegend=False, line=dict(width=0),
                                 hoverinfo="skip", legendgroup="band"))
        fig.add_trace(go.Scatter(x=x, y=lo.values, name=f"L{n}Y range", mode="lines", line=dict(width=0),
                                 fill="tonexty", fillcolor=rgba(TEAL, a), hoverinfo="skip", legendgroup="band",
                                 showlegend=(a == 0.30)))
    fig.add_trace(go.Scatter(x=x, y=b.mean().values, name="Avg", mode="lines",
                             line=dict(color=AXIS, width=1.5, dash="dot"), hovertemplate=f"%{{y:{fmt}}}"))


def _proj_trace(xs, ys, cy, ht):
    return go.Scatter(x=xs, y=ys, name=f"{cy} proj", mode="lines+markers", hovertemplate=ht,
                      line=dict(color=NAVY, width=2, dash="dot"), marker=dict(size=6, symbol="circle-open", color=NAVY))


def _projection(ctx):
    """Popover with the projection method for the months still to come; returns {crop month: projected value}."""
    piv, latest_cy, prev_cy, common, ref, unit, fmt = (
        ctx[k_] for k_ in ("piv", "latest_cy", "prev_cy", "common", "ref", "unit", "fmt"))
    rem = list(range(common + 1, 13))
    if not rem:
        st.caption(f"{latest_cy} complete")
        return {}
    seed("dx_pj_method", "Off")
    method = st.session_state["dx_pj_method"]
    out = {}
    ks = f"dx_{abs(hash((ctx['comm'], ctx['dest'], latest_cy, common, unit))) % 10**8}"   # new selection -> fresh defaults
    with st.popover(method, key="dx_proj"):
        method = st.radio("Method", PROJ_METHODS, key="dx_pj_method")
        done = list(range(1, common + 1))
        ytd_now = float(piv.loc[latest_cy, done].sum())
        props = None
        full = [y for y in ref if piv.loc[y].notna().all()]
        if full:
            rr = piv.loc[full[-5:]]
            props = rr.div(rr.sum(axis=1).replace(0, np.nan), axis=0).mean()
        implied = ytd_now / props[done].sum() if props is not None and props[done].sum() > 0 else 0.0

        if method == "YoY %":
            dflt = 0.0
            if prev_cy:
                py = float(piv.loc[prev_cy, done].sum())
                dflt = round((ytd_now / py - 1) * 100, 1) if py > 0 else 0.0
            seed(f"{ks}_yoy", dflt)
            g = st.number_input(f"YoY % vs {prev_cy} (default = current YTD pace)", step=0.5, format="%.1f",
                                key=f"{ks}_yoy")
            for m in rem:
                base = float(piv.loc[prev_cy, m]) if prev_cy and pd.notna(piv.loc[prev_cy, m]) else 0.0
                if base <= 0 and ref:
                    base = float(piv.loc[ref[-5:], m].mean())
                out[m] = base * (1 + g / 100)
        elif method == "Seasonal share" and props is not None:
            out = {m: implied * float(props[m]) for m in rem}
        elif method == "Monthly value":
            seed(f"{ks}_mv", 0.0)
            v = st.number_input(f"Per remaining month ({unit})", min_value=0.0, step=1.0, format="%.2f", key=f"{ks}_mv")
            out = {m: v for m in rem}
        elif method == "Full-year target" and props is not None:
            seed(f"{ks}_fy", float(round(implied, 1)))
            tgt = st.number_input(f"Full crop year ({unit})", min_value=0.0, step=1.0, format="%.1f", key=f"{ks}_fy")
            left = max(0.0, tgt - ytd_now)
            w = props[rem] / props[rem].sum() if props[rem].sum() > 0 else pd.Series(1 / len(rem), index=rem)
            out = {m: left * float(w[m]) for m in rem}
        if out:
            st.caption(f"YTD {format(ytd_now, fmt)} + projected {format(sum(out.values()), fmt)} = "
                       f"**{format(ytd_now + sum(out.values()), fmt)} {unit}**")
        st.caption("Seasonal shares use the last 5 complete years.")
    return out


def _heatmap(ctx):
    piv, shown, latest_cy, common, ytd, yoy, ref, fmt, cut = (
        ctx[k_] for k_ in ("piv", "shown", "latest_cy", "common", "ytd", "yoy", "ref", "fmt", "cut"))
    hdr = MONTHS + ["Total", "Total YoY", f"YTD ({cut})", "YTD YoY"]
    body = piv.loc[[y for y in shown if y in piv.index]]
    vals = body.to_numpy(dtype=float)
    vals = vals[~np.isnan(vals) & (vals > 0)]
    lo, hi = (float(vals.min()), float(vals.max())) if vals.size else (0.0, 1.0)
    tot_all = piv.sum(axis=1, min_count=1)
    if common < 12:
        tot_all.loc[latest_cy] = np.nan
    tyoy = tot_all.pct_change(fill_method=None) * 100

    def month_cells(s, heat=True):
        return [t_cell("") if pd.isna(s[m]) or s[m] == 0
                else t_cell(format(s[m], fmt), bg=seq_color(s[m], lo, hi) if heat else None) for m in range(1, 13)]

    def yoy_cell(v):
        return t_cell("" if pd.isna(v) else f"{v:+.1f}%", "up" if pd.notna(v) and v >= 0 else "down")

    rows = []
    for y in body.index:
        s = body.loc[y]
        total = "" if (y == latest_cy and common < 12) or s.isna().all() else format(s.sum(), fmt)
        ytd_txt = format(ytd[y], fmt) if pd.notna(ytd[y]) else ""
        cells = month_cells(s) + [t_cell(total, "x"), yoy_cell(tyoy.get(y, np.nan)),
                                  t_cell(ytd_txt, "x"), yoy_cell(yoy.get(y, np.nan))]
        rows.append(t_row(y, cells))
        if y == latest_cy and len(ref) >= 2:
            avg = piv.loc[ref].mean()
            dev = [(s[m] / avg[m] - 1) * 100 if pd.notna(s[m]) and s[m] > 0 and avg[m] > 0 else np.nan
                   for m in range(1, 13)]
            dc = [t_cell("") if pd.isna(v) else t_cell(f"{v:+.0f}%", "up" if v > 0 else "down") for v in dev]
            rows.append(t_row(f"vs Avg L{len(ref)}Y", dc + [t_cell("", "x")] * 3 + [t_cell("")], "ref"))

    if len(ref) >= 2:
        rows.append(t_sep(len(hdr) + 1))
        rb = piv.loc[ref]
        tot, ytd_r = rb.sum(axis=1, min_count=1), ytd[ref]
        for name, agg in [("Min", "min"), ("Avg", "mean"), ("Max", "max")]:
            cells = month_cells(getattr(rb, agg)(), heat=False) + [
                t_cell(format(getattr(tot, agg)(), fmt), "x"), t_cell(""),
                t_cell(format(getattr(ytd_r, agg)(), fmt), "x"), t_cell("")]
            rows.append(t_row(f"{name} L{len(ref)}Y", cells, "ref"))
    t_render(hdr, rows, corner="Crop year")


# ── Destinations: ranking for the selected Type, same YTD window as the Total ─
def _destinations(df, comm, unit, start):
    factor, fmt = UNITS[unit]
    tot_piv = pivot(recrop(long_for(TOTAL), start), comm, factor)
    if tot_piv.empty:
        return
    latest = tot_piv.index[-1]
    prev = tot_piv.index[-2] if len(tot_piv) > 1 else None
    valid = tot_piv.loc[latest].dropna().index
    common = int(valid.max()) if len(valid) else 12
    done = list(range(1, common + 1))
    cut = f"{MONTHS[0]}–{MONTHS[common - 1]}"
    m_lab = MONTHS[common - 1]
    tot_ytd = float(tot_piv.loc[latest, done].sum())

    names = sorted(set().union(*[destinations_for_type(df, t) for t in TYPES[comm]])) + [EUROPE_LABEL]
    recs = []
    for d in names:
        p = pivot(recrop(long_for(d), start), comm, factor)
        if latest not in p.index:
            continue
        cur = float(p.loc[latest, done].sum())
        pre = float(p.loc[prev, done].sum()) if prev in p.index else np.nan
        mon = p.loc[latest, common]
        mon_p = p.loc[prev, common] if prev in p.index else np.nan
        recs.append(dict(name=d, mon=mon, mon_yoy=(mon / mon_p - 1) * 100 if pd.notna(mon) and mon_p and mon_p > 0 else np.nan,
                         cur=cur, pre=pre, chg=cur - pre if pd.notna(pre) else np.nan,
                         yoy=(cur / pre - 1) * 100 if pre and pre > 0 else np.nan,
                         share=cur / tot_ytd * 100 if tot_ytd else np.nan))
    if not recs:
        return
    r = pd.DataFrame(recs)
    named = r[r["name"] != EUROPE_LABEL].sort_values("cur", ascending=False)
    rows_df = pd.concat([named, r[r["name"] == EUROPE_LABEL]])

    t_col, c_col = st.columns([1.25, 1], gap="medium")
    with t_col, st.container(border=True, key="dx_card_dest"):
        card_head(f"{comm} by Destination · {latest} YTD {cut}", f"{unit} · vs same months of {prev}")
        hdr = [f"{m_lab} {latest}", "YoY", f"YTD {latest}", f"YTD {prev}", "Change", "YoY", "Share"]
        cmax = float(named["cur"].max()) if len(named) else 1.0

        def yc(v):
            return t_cell("" if pd.isna(v) else f"{v:+.1f}%", "up" if pd.notna(v) and v >= 0 else "down")

        rows = []
        for i, x in enumerate(rows_df.itertuples()):
            if x.name == EUROPE_LABEL:
                rows.append(t_sep(len(hdr) + 1))
            cells = [t_cell("" if pd.isna(x.mon) else format(x.mon, fmt)), yc(x.mon_yoy),
                     t_cell(format(x.cur, fmt), "x", bg=seq_color(x.cur, 0, cmax) if x.name != EUROPE_LABEL else None),
                     t_cell("" if pd.isna(x.pre) else format(x.pre, fmt)),
                     t_cell("" if pd.isna(x.chg) else f"{x.chg:+,.{fmt[-2]}f}",
                            "up" if pd.notna(x.chg) and x.chg >= 0 else "down"),
                     yc(x.yoy), t_cell("" if pd.isna(x.share) else f"{x.share:.1f}%")]
            rows.append(t_row(x.name, cells, "ref" if x.name == EUROPE_LABEL else ""))
        other = tot_ytd - float(named["cur"].sum())
        rows.append(t_row("Total", [t_cell(format(tot_piv.loc[latest, common], fmt)), t_cell(""),
                                    t_cell(format(tot_ytd, fmt), "x"), t_cell(""), t_cell(""), t_cell(""),
                                    t_cell("100%")], "hl"))
        t_render(hdr, rows, corner="Destination")
        st.markdown(f"<div class='card-desc' style='text-align:center;margin-top:6px'>Named destinations are a subset; "
                    f"other = {format(other, fmt)} ({other / tot_ytd * 100 if tot_ytd else 0:.0f}%)</div>",
                    unsafe_allow_html=True)

    with c_col, st.container(border=True, key="dx_card_destchg"):
        card_head(f"YTD Change by Destination", f"{unit} · {latest} vs {prev}, {cut}")
        ch = named.dropna(subset=["chg"]).sort_values("chg")
        fig = go.Figure(go.Bar(y=ch["name"], x=ch["chg"], orientation="h",
                               marker_color=[GREEN if v >= 0 else RED for v in ch["chg"]],
                               text=[f"{v:+,.{fmt[-2]}f}" for v in ch["chg"]], textposition="outside",
                               textfont=dict(size=10, color=AXIS), cliponaxis=False,
                               customdata=ch["yoy"],
                               hovertemplate=f"%{{y}}: %{{x:+,.{fmt[-2]}f}} {unit} (%{{customdata:+.1f}}%)<extra></extra>"))
        show(style(fig, height=max(320, 60 + 30 * len(ch)), legend=None, fmt=fmt,
                   xaxis=dict(showgrid=True, zeroline=True, zerolinecolor="#c3cbe0", tickformat=fmt),
                   yaxis=dict(tickformat=None, showgrid=False), bargap=0.35), key="dx_destchg")


# ── Excess vs Normal: actual minus a normal baseline, per destination, in K bags and exchange lots ──────────
BAGS_PER_LOT = {"Arabica": 283.5, "Robusta": 10_000 / 60}
BASELINES = {"6M": "avg of the 6 months before", "1Y": "same month last year", "3Y": "same month, prior 3 years avg",
             "5Y": "same month, prior 5 years avg", "10Y": "same month, prior 10 years avg"}


def _baseline(sub, year, month, method):
    """Normal level at (year, month). 6M = trailing 6 months; nY = same calendar month over the prior n years."""
    if method == "6M":
        key = sub["Year"] * 12 + sub["Month"]
        cur = year * 12 + month
        win = sub[(key < cur) & (key >= cur - 6)]
    else:
        n = int(method[:-1])
        win = sub[(sub["Month"] == month) & (sub["Year"] < year) & (sub["Year"] >= year - n)]
    v = win["Bags (K)"].dropna()
    return float(v.mean()) if len(v) else np.nan


def _ex_row(name, actual, base, per_lot):
    ex = actual - base if pd.notna(actual) and pd.notna(base) else np.nan
    return dict(name=name, actual=actual, base=base, ex=ex,
                pct=ex / base * 100 if pd.notna(ex) and base else np.nan,
                lots=ex * 1000 / per_lot if pd.notna(ex) else np.nan)


def _excess_rows(df, type_, year, month, method):
    per_lot = BAGS_PER_LOT[type_]
    typed = df[(df["Type"] == type_) & df["Bags (K)"].notna()]
    rows = []
    for d in sorted(x for x in typed["Destination"].unique() if x != TOTAL):
        sub = typed[typed["Destination"] == d]
        cur = sub.loc[(sub["Year"] == year) & (sub["Month"] == month), "Bags (K)"]
        rows.append(_ex_row(d, float(cur.iloc[0]) if len(cur) else np.nan, _baseline(sub, year, month, method), per_lot))
    rows.sort(key=lambda r: r["ex"] if pd.notna(r["ex"]) else -np.inf, reverse=True)
    eu = [r for r in rows if r["name"] in EUROPE_MEMBERS]
    tots = []
    if eu:
        tots.append(_ex_row(EUROPE_LABEL, np.nansum([r["actual"] for r in eu]), np.nansum([r["base"] for r in eu]), per_lot))
    tots.append(_ex_row("Named destinations", np.nansum([r["actual"] for r in rows]),
                        np.nansum([r["base"] for r in rows]), per_lot))
    sub = typed[typed["Destination"] == TOTAL]                       # true Brazil total, incl. unnamed buyers
    cur = sub.loc[(sub["Year"] == year) & (sub["Month"] == month), "Bags (K)"]
    if len(cur):
        tots.append(_ex_row("Brazil total", float(cur.iloc[0]), _baseline(sub, year, month, method), per_lot))
    return rows, tots


def _excess(df):
    months = sorted({(int(y), int(m)) for y, m in df.loc[df["Bags (K)"].notna(), ["Year", "Month"]].itertuples(index=False)})
    labels = [f"{CAL[m - 1]} {y}" for y, m in months]
    c1, c2, _ = st.columns([1.2, 2.6, 3], vertical_alignment="bottom")
    with c1, st.container(key="dx_exmonth_wrap"):
        lab = st.selectbox("Month", labels[::-1], key="dx_exmonth")
    method = c2.radio("Normal", list(BASELINES), index=3, horizontal=True, key="dx_exbase")
    year, month = months[labels.index(lab)]
    st.markdown(f"<div class='card-desc'>Normal = {BASELINES[method]}. Lots: Arabica 283.5 bags, Robusta 166.7 bags.</div>",
                unsafe_allow_html=True)

    def num(v, sign=False):
        return "" if pd.isna(v) else (f"{v:+,.0f}" if sign else f"{v:,.0f}")

    def ud(v):
        return "up" if pd.notna(v) and v >= 0 else "down"

    cols = st.columns(2, gap="medium")
    for col, t in zip(cols, ["Arabica", "Robusta"]):
        rows, tots = _excess_rows(df, t, year, month, method)
        with col, st.container(border=True, key=f"dx_card_ex_{t}"):
            card_head(f"{t} · Excess vs Normal · {lab}", f"K bags and lots · normal = {method}")
            body = [t_row(r["name"], [t_cell(num(r["actual"])), t_cell(num(r["base"])),
                                      t_cell(num(r["ex"], True), ud(r["ex"])), t_cell(num(r["lots"], True), ud(r["lots"])),
                                      t_cell("" if pd.isna(r["pct"]) else f"{r['pct']:+.0f}%", ud(r["pct"]))])
                    for r in rows]
            body.append(t_sep(6))
            body += [t_row(r["name"], [t_cell(num(r["actual"]), "x"), t_cell(num(r["base"])),
                                       t_cell(num(r["ex"], True), ud(r["ex"])), t_cell(num(r["lots"], True), ud(r["lots"])),
                                       t_cell("" if pd.isna(r["pct"]) else f"{r['pct']:+.0f}%", ud(r["pct"]))], "hl")
                     for r in tots]
            t_render(["Actual", "Normal", "Excess", "Lots", "vs Normal"], body, corner="Destination")
            pr = [r for r in rows if pd.notna(r["lots"])][::-1]
            if pr:
                fig = go.Figure(go.Bar(y=[r["name"] for r in pr], x=[r["lots"] for r in pr], orientation="h",
                                       marker_color=[GREEN if r["lots"] >= 0 else RED for r in pr],
                                       text=[f"{r['lots']:+,.0f}" for r in pr], textposition="outside",
                                       textfont=dict(size=10, color=AXIS), cliponaxis=False,
                                       hovertemplate="%{y}: %{x:+,.0f} lots<extra></extra>"))
                show(style(fig, height=max(260, 50 + 26 * len(pr)), legend=None,
                           xaxis=dict(showgrid=True, zeroline=True, zerolinecolor="#c3cbe0", title="lots"),
                           yaxis=dict(tickformat=None, showgrid=False), bargap=0.35), key=f"dx_exbar_{t}")


# ── Destination split over time: stacked bars, named destinations + Others (= Brazil total - named) ──────────
SPLIT_PAL = [NAVY, TEAL, AMBER, GREEN, RED, "#6b7fb8", "#8fc7d0", "#e2c38a", "#9fd1bb", "#b9c3de", "#d9a3a3", "#4a5578"]
OTHERS_C = "#d5d9e3"


def _split(df, comm, unit, start):
    factor, fmt = UNITS[unit]
    d = df[df["Type"].isin(TYPES[comm]) & df["Bags (K)"].notna()]
    d = d.assign(date=pd.to_datetime(dict(year=d["Year"], month=d["Month"], day=1)))
    wide = d.pivot_table(index="date", columns="Destination", values="Bags (K)", aggfunc="sum").sort_index()
    if TOTAL not in wide:
        return
    named = [c for c in wide.columns if c != TOTAL]
    wide["Others"] = (wide[TOTAL] - wide[named].fillna(0).sum(axis=1)).clip(lower=0)
    wide = wide.drop(columns=TOTAL).fillna(0) * factor

    with st.container(border=True, key="dx_card_split"):
        h, w1, w2 = st.columns([2.2, 1.3, 1], vertical_alignment="center")
        h.markdown(f"<div class='chart-head'>{comm} Exports by Destination</div>", unsafe_allow_html=True)
        per = w1.radio("Period", ["Monthly", "Crop year"], horizontal=True, key="dx_split_per", label_visibility="collapsed")
        mode = w2.radio("Show", ["Volume", "Share %"], horizontal=True, key="dx_split_mode", label_visibility="collapsed")
        if per == "Monthly":
            data = wide.iloc[-36:]
            x = [f"{t:%b-%y}" for t in data.index]
            note = "last 36 months"
        else:
            cy0 = [t.year if t.month >= start else t.year - 1 for t in wide.index]
            data = wide.groupby(cy0).sum()
            data = data.iloc[1:] if len(data) > 1 else data                # first crop year is partial (data from Oct 2007)
            n_last = sum(1 for c in cy0 if c == data.index[-1])
            x = [f"{y % 100:02d}/{(y + 1) % 100:02d}" + (" YTD" if y == data.index[-1] and n_last < 12 else "")
                 for y in data.index]
            note = "crop years, latest = YTD"
        order = [c for c in data.drop(columns="Others").sum().sort_values(ascending=False).index if data[c].sum() > 0]
        cols = order + ["Others"]
        vals = data[cols]
        if mode == "Share %":
            vals = vals.div(vals.sum(axis=1).replace(0, np.nan), axis=0) * 100
        st.markdown(f"<div class='card-desc'>{unit if mode == 'Volume' else '% of Brazil total'} · {note} · "
                    f"Others = Brazil total minus named destinations</div>", unsafe_allow_html=True)
        fig = go.Figure()
        for i, c in enumerate(cols):
            col = OTHERS_C if c == "Others" else SPLIT_PAL[i % len(SPLIT_PAL)]
            hv = "%{y:.1f}%" if mode == "Share %" else f"%{{y:{fmt}}} {unit}"
            fig.add_trace(go.Bar(x=x, y=vals[c].values, name=c, marker=dict(color=col, line=dict(width=0)),
                                 hovertemplate=f"{c}: {hv}<extra></extra>"))
        fig.update_layout(legend_traceorder="normal")
        show(style(fig, height=460, legend="top", unified=True, fmt=".1f" if mode == "Share %" else fmt,
                   short=unit == "Bags" and mode == "Volume", barmode="stack", bargap=0.18,
                   xaxis=dict(type="category", tickangle=-45 if per == "Monthly" else 0),
                   yaxis=dict(ticksuffix="%" if mode == "Share %" else "", range=[0, 100] if mode == "Share %" else None)),
             key="dx_split")
