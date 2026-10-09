"""Monthly Cecafe: Brazil monthly coffee exports by crop year (Jul-Jun).

Monthly (seasonal) - Cumulative - YTD - Rolling - Tabular view, with the optional projection. The visuals follow the
TDM Pro Comprehensive overview page (views/overview.py); data = Database/cecafe_exports.csv, built from the
"... Exports" sheets of Cecafe Daily History.xlsx by Automator/build_exports.py.
"""
import io
import json
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import ghstore as gh

DATA = Path(__file__).resolve().parent.parent / "Database" / "cecafe_exports.csv"
MONTHS = ["Jul", "Aug", "Sep", "Oct", "Nov", "Dec", "Jan", "Feb", "Mar", "Apr", "May", "Jun"]   # crop month 1-12
ROOT = Path(__file__).resolve().parent.parent
SETTINGS = ROOT / "Database" / "cecafe_settings.json"
EXPORTS_PATH, SETTINGS_PATH = "Database/cecafe_exports.csv", "Database/cecafe_settings.json"      # paths in the repo
TYPES = {"Arabica": ["Arabica"], "Robusta": ["Robusta"], "Soluble": ["Soluble"],
         "Arabica + Robusta": ["Arabica", "Robusta"], "Robusta + Soluble": ["Robusta", "Soluble"],
         "Arabica + Robusta + Soluble": ["Arabica", "Robusta", "Soluble"]}
COMMS = list(TYPES)
BASE = ["Arabica", "Robusta", "Soluble"]
TZ = "Europe/Amsterdam"
UNITS = {"'000 bags": (1e-3, ",.0f"), "Bags": (1.0, ",.0f"), "Million bags": (1e-6, ",.2f")}
PROJ_METHODS = ["Off", "YoY %", "Seasonal share", "Monthly value", "Full-year target"]

# ── Palette (same as the Daily pages) ─────────────────────────────────────────
NAVY, TEAL, GREEN, RED, AMBER, GREY = "#0a2463", "#1f8a9c", "#1f9d6f", "#c94a4a", "#c98a1f", "#8a94a8"
INK, AXIS, GRID = "#1a1a2e", "#4a5578", "rgba(10,36,99,0.08)"
OLDER = [TEAL, AMBER, GREEN, "#6b7fb8", GREY, "#8fc7d0", "#e2c38a", "#9fd1bb", "#b9c3de"]
SEQ = ["#ffffff", "#edf8f2", "#d2eee1", "#aee0c9", "#80cbab", "#52b28a", "#2f9870", "#1f7d5b", "#135f45"]
DIV = ["#c94a4a", "#dc8585", "#edbcbc", "#f7e2e2", "#ffffff", "#e2f3eb", "#aee0c9", "#52b28a", "#1f7d5b"]

CSS = """
<style>
.tbl-wrap { overflow-x: auto; border: 1px solid #dfe3ee; border-radius: 8px; background: #ffffff; margin-bottom: 4px; }
.tbl { border-collapse: collapse; width: 100%; font-size: 12.5px; font-variant-numeric: tabular-nums; }
.tbl th { background: #eef0f6; color: #0a2463; font-weight: 600; padding: 6px 8px; text-align: center; white-space: nowrap; }
.tbl th:first-child { text-align: left; }
.tbl.fixed { table-layout: fixed; }
.tbl.fixed th:first-child { width: 96px; }
.tbl td { padding: 4px 8px; text-align: right; white-space: nowrap; border-bottom: 1px solid #f0f2f6; color: #1a1a2e; }
.tbl td.lbl { text-align: left; font-weight: 600; background: #f7f8fb; border-right: 1px solid #dfe3ee; color: #0a2463; }
.tbl td.x { border-left: 2px solid #dfe3ee; font-weight: 600; background: #f7f8fb; }
.tbl tr.ref td { background: #f4f6fa; color: #4a5578; font-style: italic; }
.tbl tr.sep td { height: 3px; padding: 0; background: #eef0f6; border: none; }
.tbl td.up { color: #1f9d6f; font-weight: 700; }
.tbl td.down { color: #c94a4a; font-weight: 700; }
/* Filter card: one row, small navy caps labels over each group */
.st-key-mc_filters [data-testid="stWidgetLabel"] { min-height: 0; margin-bottom: 4px; }
.st-key-mc_filters [data-testid="stWidgetLabel"] p, .mc-lbl { font-size: 10.5px !important; font-weight: 700;
    letter-spacing: .08em; text-transform: uppercase; color: #0a2463 !important; margin: 0 0 4px; }
/* Projection: a small chip, grey when off, navy-tinted when a method is on */
.st-key-mc_proj button { min-height: 34px !important; border-radius: 999px !important; padding: 4px 16px !important;
    background: #f8f9fc !important; border: 1px solid #e3e7ef !important; box-shadow: none !important; }
.st-key-mc_proj button p { font-size: 12.5px !important; font-weight: 600; color: #3d4a6b !important; }
.st-key-mcproj_on .st-key-mc_proj button { background: #eef2fb !important; border-color: #b9c6e6 !important; }
.st-key-mcproj_on .st-key-mc_proj button p { color: #0a2463 !important; }
/* Chart title line: toggle flush right */
[data-testid="stVerticalBlock"]:has(> .st-key-mc_view), [data-testid="stVerticalBlock"]:has(> .st-key-mc_cumview),
[data-testid="stVerticalBlock"]:has(> .st-key-mc_roll) { align-items: flex-end; }
/* Section dividers: rule + centred label */
.mc-rule { border-top: 1px solid #dfe3ee; margin: 22px 0 0; }
.mc-sec { font-size: 18px; font-weight: 700; color: #8b1a1a; text-align: center; letter-spacing: .01em; margin: 6px 0 8px; }
/* Compact table: smaller type, tight cells, values centred */
.tbl { font-size: 11.5px; line-height: 1.25; }
.tbl th { padding: 3px 5px; font-size: 11px; }
.tbl td { padding: 2px 5px; text-align: center; }
.tbl td.lbl { text-align: left; }
.tbl.fixed th:first-child { width: 84px; }
</style>
"""


# ── Colour helpers ────────────────────────────────────────────────────────────
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


def div_color(v, lim):
    return DIV[4] if lim <= 0 else _lerp(DIV, (v + lim) / (2 * lim))


def text_on(bg):
    r, g, b = (int(bg[k:k + 2], 16) for k in (1, 3, 5))
    return INK if (0.299 * r + 0.587 * g + 0.114 * b) / 255 > 0.58 else "#ffffff"


def rgba(hex_, a):
    r, g, b = (int(hex_[k:k + 2], 16) for k in (1, 3, 5))
    return f"rgba({r},{g},{b},{a})"


def year_styles(years):
    """Latest = navy bold, previous = red, older = muted (thin)."""
    ys = sorted(years, reverse=True)
    out = {y: (OLDER[i % len(OLDER)], 1.3) for i, y in enumerate(ys[2:])}
    if len(ys) >= 2:
        out[ys[1]] = (RED, 2.0)
    if ys:
        out[ys[0]] = (NAVY, 3.0)
    return out


# ── Table + chart helpers ─────────────────────────────────────────────────────
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
    st.markdown(f"<div class='tbl-wrap'><table class='tbl fixed'>{head}{''.join(rows)}</table></div>",
                unsafe_allow_html=True)


def heading(title, desc=""):
    d = f"<div class='card-desc'>{desc}</div>" if desc else ""
    st.markdown(f"<div class='chart-head'>{title}</div>{d}", unsafe_allow_html=True)


def chart_head(title, desc, control):
    """Title with its toggle on the same line (right), description underneath at full width."""
    h, w = st.columns([1, 1], vertical_alignment="center")
    h.markdown(f"<div class='chart-head'>{title}</div>", unsafe_allow_html=True)
    out = control(w)
    st.markdown(f"<div class='card-desc'>{desc}</div>", unsafe_allow_html=True)
    return out


def section(label=""):
    lab = f"<div class='mc-sec'>{label}</div>" if label else ""
    st.markdown(f"<div class='mc-rule'></div>{lab}", unsafe_allow_html=True)


def style(fig, height=340, legend="bottom", months=None, unified=False, fmt=",.0f", **extra):
    xaxis = dict(gridcolor=GRID, color=AXIS, showgrid=False)
    if months:
        xaxis.update(categoryorder="array", categoryarray=months)
    xaxis.update(extra.pop("xaxis", {}))
    yaxis = dict(gridcolor=GRID, color=AXIS, hoverformat=fmt, tickformat=fmt, separatethousands=True)
    yaxis.update(extra.pop("yaxis", {}))
    margin = dict(t=30, b=30, l=10, r=10)
    leg = dict(bgcolor="rgba(0,0,0,0)", orientation="h", x=0, font=dict(size=10), itemwidth=30)
    if legend == "bottom":
        leg.update(y=-0.15, yanchor="top")
        margin["b"] = 60
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
def load() -> pd.DataFrame:
    return pd.read_csv(DATA)


@st.cache_data(ttl=600)
def load_settings() -> dict:
    s = {"soluble_gbe": 2.1}
    try:
        s.update(json.loads(SETTINGS.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        pass
    return s


def pivot(raw: pd.DataFrame, comm: str, factor: float, gbe: float) -> pd.DataFrame:
    """crop year x crop month (1-12), in the chosen unit. NaN = no data.
    Combinations add the types month by month; Soluble is multiplied by the GBE multiplier first.
    A cell is NaN if any type in the combination is missing there."""
    types = TYPES[comm]

    def one(c):
        d = raw[raw["commodity"] == c]
        p = (d.pivot_table(index="crop_year", columns="cm", values="bags", aggfunc="sum")
               .reindex(columns=range(1, 13)))
        return p * (gbe if c == "Soluble" and len(types) > 1 else 1.0)
    frames = [one(c) for c in types]
    idx = frames[0].index
    for f in frames[1:]:
        idx = idx.union(f.index)
    piv = frames[0].reindex(idx)
    for f in frames[1:]:
        piv = piv + f.reindex(idx)
    return (piv.dropna(how="all") * factor).sort_index()


def month_dates(cy: str, cm: int) -> pd.Timestamp:
    y0 = 2000 + int(cy[:2])
    return pd.Timestamp(y0, 6 + cm, 1) if cm <= 6 else pd.Timestamp(y0 + 1, cm - 6, 1)


# ── Page ──────────────────────────────────────────────────────────────────────
def render():
    st.markdown(CSS, unsafe_allow_html=True)
    raw = load()
    gbe = float(load_settings()["soluble_gbe"])
    if st.session_state.get("mc_page") in ("Charts", "Table", "Advanced Study"):   # sections that no longer exist
        st.session_state["mc_page"] = "Charts & Table"
    with st.container(key="nav"):                                    # same pill row as Daily; Entry first
        page = st.radio("Section", ["Entry", "Charts & Table"], horizontal=True,
                        label_visibility="collapsed", key="mc_page")
    if page == "Entry":
        render_input(raw, gbe)
    else:
        _views(raw, gbe, page)


def _context(raw, gbe, comm, unit, span):
    """Everything the charts and the table need for one selection. None when there is no data."""
    factor, fmt = UNITS[unit]
    piv = pivot(raw, comm, factor, gbe)
    if piv.empty:
        return None
    years = piv.index.tolist()
    latest_cy = years[-1]
    valid = piv.loc[latest_cy].dropna().index
    common = int(valid.max()) if len(valid) else 12
    ytd = piv[list(range(1, common + 1))].sum(axis=1, min_count=1)
    n_show = {"Last 5": 5, "Last 10": 10, "All": len(years)}[span]
    parts = {}
    if len(TYPES[comm]) > 1:                                       # breakup of a combination, shown in Rolling
        for c in TYPES[comm]:
            pc = pivot(raw, c, factor, 1.0) * (gbe if c == "Soluble" else 1.0)
            parts[c] = pc.reindex(piv.index).where(piv.notna())
    return dict(parts=parts, gbe=gbe, 
        comm=comm, unit=unit, span=span, fmt=fmt, piv=piv, years=years, latest_cy=latest_cy,
        prev_cy=years[-2] if len(years) >= 2 else None, common=common,
        ref=[y for y in years if y != latest_cy][-10:],              # last 10 complete crop years
        ytd=ytd, yoy=ytd.pct_change(fill_method=None) * 100, cut=f"{MONTHS[0]}–{MONTHS[common - 1]}", shown=years[-n_show:],
        sc=f"{comm} · {unit}" + (f" · Soluble x{gbe:g} GBE" if "Soluble" in TYPES[comm] and len(TYPES[comm]) > 1 else ""),
        sig=(comm, unit, latest_cy, common))


def _views(raw, gbe, page):
    """Charts & Table: one set of controls (Type, Unit, Years, Projection) drives the charts row and the table."""
    pre = "ch"
    with st.container(border=True, key="mc_filters"):
        b0, b1, b2, b3 = st.columns([4.6, 1.9, 1.5, 1.4], vertical_alignment="bottom")
        comm = b0.radio("Type", COMMS, horizontal=True, key=f"mc_{pre}_comm")
        unit = b1.radio("Unit", list(UNITS), horizontal=True, key=f"mc_{pre}_unit")
        span = b2.radio("Years", ["Last 5", "Last 10", "All"], horizontal=True, key="mc_ch_span")
        ctx = _context(raw, gbe, comm, unit, span)
        proj = {}
        if ctx is not None:
            with b3:
                st.markdown("<div class='mc-lbl'>Projection</div>", unsafe_allow_html=True)
                with st.container(key=f"mcproj_{'off' if st.session_state.get('mc_pj_method', 'Off') == 'Off' else 'on'}"):
                    proj = _projection(ctx["piv"], ctx["latest_cy"], ctx["prev_cy"], ctx["common"], ctx["ref"],
                                       unit, ctx["fmt"])
    if ctx is None:
        st.info("No data for this selection.")
        return
    section()
    _charts(ctx, proj)
    section()
    _table(ctx)


def _charts(ctx, proj):
    piv, years, latest_cy, prev_cy, common, ref, ytd, yoy, cut, shown, sc, unit, fmt = (
        ctx[k_] for k_ in ("piv", "years", "latest_cy", "prev_cy", "common", "ref", "ytd", "yoy", "cut", "shown",
                           "sc", "unit", "fmt"))
    styles = year_styles(sorted(set(shown) | set(years[-3:])))
    ht = f"%{{y:{fmt}}} {unit}"
    k = "mc"
    gbe_txt = f"{ctx['gbe']:g}"

    comm = ctx["comm"]
    u_desc = sc.split(" · ", 1)[1]                                  # unit (+ GBE note); the type is in the title
    H = 520                                                        # one height for the three charts in the row
    l, mid, r = st.columns(3, gap="medium")
    with l:
        view = chart_head(f"{comm} Monthly Exports", f"{u_desc} · bands = L{len(ref)}Y min-max and percentiles",
                          lambda w: w.radio("Seasonal view", ["Latest vs range", "All years"], horizontal=True,
                                            key=f"{k}_view", label_visibility="collapsed"))
        plot_years = shown if view == "All years" else [y for y in shown if y in (latest_cy, prev_cy)]
        fig = go.Figure()
        _band(fig, piv.loc[ref], len(ref), fmt) if len(ref) >= 2 else None
        for y in plot_years:
            c, wd = styles[y]
            s = piv.loc[y].dropna()
            fig.add_trace(go.Scatter(x=[MONTHS[m - 1] for m in s.index], y=s.values, name=y, mode="lines",
                                     line=dict(color=c, width=wd), hovertemplate=ht))
        if proj and latest_cy in shown:
            xs = [MONTHS[common - 1]] + [MONTHS[m - 1] for m in proj]
            fig.add_trace(_proj_trace(xs, [piv.loc[latest_cy, common]] + list(proj.values()), latest_cy, ht))
        show(style(fig, height=H, months=MONTHS, unified=True, fmt=fmt), key=f"{k}_seasonal")

    with mid:
        cview = chart_head(f"{comm} Cumulative Exports", f"{u_desc} · bands = L{len(ref)}Y cumulative",
                           lambda w: w.radio("Cumulative view", ["Last 4", "All"], horizontal=True,
                                             key=f"{k}_cumview", label_visibility="collapsed"))
        fig = go.Figure()
        if len(ref) >= 2:
            _band(fig, piv.loc[ref].cumsum(axis=1), len(ref), fmt)
        cum_years = years[-4:] if cview == "Last 4" else years
        older = [y for y in cum_years if y not in (latest_cy, prev_cy)]
        for y in cum_years:
            if y in (latest_cy, prev_cy):
                c, wd = styles[y]
            else:
                c, wd = OLDER[older.index(y) % len(OLDER)], 1.3
            s = piv.loc[y].dropna().cumsum()
            fig.add_trace(go.Scatter(x=[MONTHS[m - 1] for m in s.index], y=s.values, name=y, mode="lines",
                                     line=dict(color=c, width=wd), hovertemplate=ht))
        if proj:
            run = float(ytd[latest_cy])
            xs, ys = [MONTHS[common - 1]], [run]
            for m, v in proj.items():
                run += v
                xs.append(MONTHS[m - 1])
                ys.append(run)
            fig.add_trace(_proj_trace(xs, ys, latest_cy, ht))
        show(style(fig, height=H, months=MONTHS, unified=True, fmt=fmt), key=f"{k}_cum")

    with r:
        seed(f"{k}_roll", "12m")
        win = chart_head(f"{comm} Rolling Exports", f"{u_desc} · trailing sum",
                         lambda w: w.radio("Window", ["1m", "3m", "6m", "12m"], horizontal=True, key=f"{k}_roll",
                                           label_visibility="collapsed"))
        def rolling(pv):
            stack = pv.stack().dropna()
            mon = pd.Series(stack.values, index=[month_dates(cy, int(cm)) for cy, cm in stack.index]).sort_index()
            return mon.rolling(int(win[:-1])).sum().dropna()
        parts = ctx["parts"]
        roll = rolling(piv)
        floor = float(roll.min()) - 0.05 * float(roll.max() - roll.min())     # shade to just under the low, not to 0
        fig = go.Figure(go.Scatter(x=roll.index, y=[floor] * len(roll), mode="lines", line=dict(width=0),
                                   showlegend=False, hoverinfo="skip"))
        fig.add_trace(go.Scatter(x=roll.index, y=roll.values, mode="lines", line=dict(color=TEAL, width=2),
                                 fill="tonexty", fillcolor=rgba(TEAL, 0.08), name="Combined" if parts else "Rolling",
                                 hovertemplate=f"%{{x|%b-%y}}: %{{y:{fmt}}} {unit}<extra></extra>"))
        pal = {"Arabica": NAVY, "Robusta": AMBER, "Soluble": GREEN}
        for c, pv in parts.items():                                # breakup: one line per type in the combination
            rc = rolling(pv)
            nm = f"{c} (x{gbe_txt})" if c == "Soluble" else c
            fig.add_trace(go.Scatter(x=rc.index, y=rc.values, mode="lines", name=nm, line=dict(color=pal[c], width=1.8),
                                     hovertemplate=f"{nm} %{{x|%b-%y}}: %{{y:{fmt}}} {unit}<extra></extra>"))
        show(style(fig, height=(300 if parts else 265), legend="bottom" if parts else None, fmt=fmt,
                   yaxis=dict(autorange=True, rangemode="normal")), key=f"{k}_rolling")

        # YTD under Rolling, same column, so the right side of the row ends level with the other two charts
        heading(f"{comm} YTD {cut}", f"{u_desc} · label = YoY")
        yy = [y for y in years if y in shown or y == latest_cy]
        colors = [NAVY if y == latest_cy else "#c3cbe0" for y in yy]
        labels = [f"{yoy[y]:+.1f}%" if pd.notna(yoy[y]) else "" for y in yy]
        fig = go.Figure(go.Bar(x=yy, y=ytd[yy].values, marker_color=colors, text=labels, textposition="outside",
                               textfont=dict(size=10, color=AXIS), cliponaxis=False,
                               hovertemplate=f"%{{x}}: %{{y:{fmt}}} {unit}<extra></extra>"))
        show(style(fig, height=(185 if parts else 205), legend=None, fmt=fmt, yaxis=dict(rangemode="tozero")),
             key=f"{k}_ytd")


def _table(ctx):
    piv, years, latest_cy, common, ref, ytd, yoy, cut, sc, fmt = (
        ctx[k_] for k_ in ("piv", "years", "latest_cy", "common", "ref", "ytd", "yoy", "cut", "sc", "fmt"))
    # rows follow the Years filter (Last 5 / Last 10 / All) so the whole page fits one screen
    heading(f"{ctx['comm']} Monthly Exports",
            f"{sc} · {ctx['span'].lower()} crop years · {latest_cy} to {MONTHS[common - 1]} · Min/Avg/Max L{len(ref)}Y")
    _heatmap(piv, ctx["shown"], latest_cy, common, ytd, yoy, ref, fmt, cut)




# ── Pieces ────────────────────────────────────────────────────────────────────
def _band(fig, b, n, fmt):
    """b = DataFrame (reference years x crop months). Light teal bands: min-max, 10th-90th and 25th-75th percentile."""
    if len(b) < 2:
        return
    x = MONTHS
    for lo, hi, a, name in [(b.min(), b.max(), 0.08, f"Min–Max L{n}Y"),
                            (b.quantile(0.10), b.quantile(0.90), 0.16, "10th–90th pct"),
                            (b.quantile(0.25), b.quantile(0.75), 0.30, "25th–75th pct")]:
        fig.add_trace(go.Scatter(x=x, y=hi.values, mode="lines", showlegend=False, line=dict(width=0),
                                 hoverinfo="skip", legendgroup="band"))
        fig.add_trace(go.Scatter(x=x, y=lo.values, name=f"L{n}Y range", mode="lines", line=dict(width=0),
                                 fill="tonexty", fillcolor=rgba(TEAL, a), hoverinfo="skip", legendgroup="band",
                                 showlegend=(a == 0.30)))          # one legend entry toggles all three bands
    fig.add_trace(go.Scatter(x=x, y=b.mean().values, name="Avg", mode="lines",
                             line=dict(color=AXIS, width=1.5, dash="dot"), hovertemplate=f"%{{y:{fmt}}}"))


def _proj_trace(xs, ys, cy, ht):
    return go.Scatter(x=xs, y=ys, name=f"{cy} proj", mode="lines+markers", hovertemplate=ht,
                      line=dict(color=NAVY, width=2, dash="dot"), marker=dict(size=6, symbol="circle-open", color=NAVY))


def _projection(piv, latest_cy, prev_cy, common, ref, unit, fmt):
    """Popover with the projection method for the months still to come; returns {crop month: projected value}."""
    rem = list(range(common + 1, 13))
    if not rem:
        st.caption(f"{latest_cy} complete")
        return {}
    k_method = "mc_pj_method"
    seed(k_method, "Off")
    method = st.session_state[k_method]
    out = {}
    ks = f"mc_{piv.shape[0]}_{abs(hash((latest_cy, common, unit)) ) % 10**8}"      # new selection -> fresh defaults
    with st.popover(f"{method}" if method != "Off" else "Off", key="mc_proj"):
        method = st.radio("Method", PROJ_METHODS, key=k_method)
        done = list(range(1, common + 1))
        ytd_now = float(piv.loc[latest_cy, done].sum())
        props = None
        if ref:
            rr = piv.loc[ref[-5:]]
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
            for m in rem:
                out[m] = implied * float(props[m])
        elif method == "Monthly value":
            seed(f"{ks}_mv", 0.0)
            v = st.number_input(f"Per remaining month ({unit})", min_value=0.0, step=1.0, format="%.2f",
                                key=f"{ks}_mv")
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


def _heatmap(piv, shown, latest_cy, common, ytd, yoy, ref, fmt, cut):
    hdr = MONTHS + ["Total", "Total YoY", f"YTD ({cut})", "YTD YoY"]
    body = piv.loc[[y for y in shown if y in piv.index]]
    vals = body.to_numpy(dtype=float)
    vals = vals[~np.isnan(vals) & (vals > 0)]
    lo, hi = (float(vals.min()), float(vals.max())) if vals.size else (0.0, 1.0)
    tot_all = piv.sum(axis=1, min_count=1)
    if common < 12:
        tot_all.loc[latest_cy] = np.nan                                  # the running year has no full-year total yet
    tyoy = tot_all.pct_change(fill_method=None) * 100

    def month_cells(s, heat=True):
        return [t_cell("") if pd.isna(s[m]) or s[m] == 0
                else t_cell(format(s[m], fmt), bg=seq_color(s[m], lo, hi) if heat else None) for m in range(1, 13)]

    def yoy_cell(v):
        return t_cell("" if pd.isna(v) else f"{v:+.1f}%", "up" if pd.notna(v) and v >= 0 else "down")

    rows = []
    for y in body.index:
        s = body.loc[y]
        total = "" if y == latest_cy and common < 12 else format(s.sum(), fmt)
        cells = month_cells(s) + [t_cell(total, "x"), yoy_cell(tyoy.get(y, np.nan)),
                                  t_cell(format(ytd[y], fmt), "x"), yoy_cell(yoy.get(y, np.nan))]
        rows.append(t_row(y, cells))
        if y == latest_cy and len(ref) >= 2:
            avg = piv.loc[ref].mean()
            dev = [(s[m] / avg[m] - 1) * 100 if pd.notna(s[m]) and s[m] > 0 and avg[m] > 0 else np.nan
                   for m in range(1, 13)]
            lim = max([abs(v) for v in dev if pd.notna(v)] or [20])
            dc = [t_cell("") if pd.isna(v) else t_cell(f"{v:+.0f}%", bg=div_color(v, lim)) for v in dev]
            rows.append(t_row(f"vs Avg L{len(ref)}Y", dc + [t_cell("", "x")] * 3 + [t_cell("")], "ref"))

    if len(ref) >= 2:
        rows.append(t_sep(len(hdr) + 1))
        rb = piv.loc[ref]
        tot, ytd_r = rb.sum(axis=1), ytd[ref]
        for name, agg in [("Min", "min"), ("Avg", "mean"), ("Max", "max")]:
            cells = month_cells(getattr(rb, agg)(), heat=False) + [
                t_cell(format(getattr(tot, agg)(), fmt), "x"), t_cell(""),
                t_cell(format(getattr(ytd_r, agg)(), fmt), "x"), t_cell("")]
            rows.append(t_row(f"{name} L{len(ref)}Y", cells, "ref"))

    t_render(hdr, rows, corner="Crop year")


# ── Input form: edit any month, saved to GitHub (and the local copy), with a log ──────────────────────────────
def _num(txt):
    if txt is None or (isinstance(txt, float) and pd.isna(txt)):
        return None
    if isinstance(txt, (int, float)):
        return float(txt)
    txt = str(txt).replace(",", "").strip()
    return float(txt) if txt else None


def _fmt0(v):
    return "" if v is None or pd.isna(v) else f"{v:,.0f}"


CAL = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
LAST_YEAR = 2030                                                   # the input matrix runs up to here
FIRST_YEAR = 2011                                                  # data starts Jul 2011


def _to_crop(y: int, mo: int):
    """Calendar (year, month 1-12) -> (crop year label, crop month 1-12). Jul 2026 -> ('26/27', 1)."""
    if mo >= 7:
        return f"{y % 100:02d}/{(y + 1) % 100:02d}", mo - 6
    return f"{(y - 1) % 100:02d}/{y % 100:02d}", mo + 6


def _cal_values(raw: pd.DataFrame) -> dict:
    """{(commodity, year, month): bags} in calendar terms."""
    out = {}
    for c, cy, cm, v in raw[["commodity", "crop_year", "cm", "bags"]].itertuples(index=False):
        d = month_dates(cy, int(cm))
        out[(c, d.year, d.month)] = float(v)
    return out


def _edit_grid(vals: dict, comm: str, years: list) -> pd.DataFrame:
    """Rows = calendar years (oldest first), columns Jan..Dec (text cells)."""
    g = pd.DataFrame({CAL[m - 1]: [_fmt0(vals.get((comm, y, m))) for y in years] for m in range(1, 13)},
                     index=[str(y) for y in years])
    g.index.name = "Year"
    return g


def _changes(comm, before: pd.DataFrame, after: pd.DataFrame) -> list:
    """[(comm, year, month, old, new)] for every edited cell. Raises ValueError on non-numbers."""
    out = []
    for y in before.index:
        for m in range(1, 13):
            old, new = _num(before.loc[y, CAL[m - 1]]), _num(after.loc[y, CAL[m - 1]])
            if old != new:
                out.append((comm, int(y), m, old, new))
    return out


def _save_exports(changes: list, who: str = "dashboard"):
    lines = [f"{c} {CAL[m - 1]} {y}: {_fmt0(o) or '-'} -> {_fmt0(n) or '-'}" for c, y, m, o, n in changes]
    msg = f"Monthly exports | {len(changes)} change(s)\n\n" + "\n".join(lines)

    def apply(text):
        d = pd.read_csv(io.StringIO(text))
        for c, y, m, o, n in changes:
            cy, cm = _to_crop(y, m)
            hit = (d["commodity"] == c) & (d["crop_year"] == cy) & (d["cm"] == cm)
            d = d[~hit]
            if n is not None:
                d = pd.concat([d, pd.DataFrame([{"commodity": c, "crop_year": cy, "cm": cm, "bags": n}])])
        d["_o"] = d["commodity"].map({c: i for i, c in enumerate(BASE)})
        d = d.sort_values(["_o", "crop_year", "cm"]).drop(columns="_o")
        d["bags"] = d["bags"].round().astype("int64")
        return d.to_csv(index=False, lineterminator="\n"), None
    new_text, _ = gh.commit(EXPORTS_PATH, apply, msg)
    with open(DATA, "w", encoding="utf-8", newline="") as f:             # local copy, so the disc has it too
        f.write(new_text)
    load.clear()


HIGH, LOW = 1.8, 0.4                         # a month this many times above / below its usual level gets a question


def _sanity_notes(changes: list, vals: dict, raw: pd.DataFrame) -> list:
    """Questions for entries that look too big or too small.
    Usual level = median of the same calendar month in the 3 years before and after (whatever exists, at least 2).
    Also: above the biggest month ever seen for that type (extra zero), or below 1,000 (typed in '000 bags?)."""
    notes = []
    for c, y, m, o, n in changes:
        if n is None:
            continue
        lab = f"{c} {CAL[m - 1]} {y}"
        near = sorted(v for y2 in range(y - 3, y + 4) if y2 != y and (v := vals.get((c, y2, m))) is not None)
        cap = raw.loc[raw["commodity"] == c, "bags"].max()
        if cap and n > 1.6 * cap:
            notes.append(f"{lab}: {n:,.0f} is far above anything seen (max {cap:,.0f}). Extra zero?")
        elif len(near) >= 2:
            ref = near[len(near) // 2] if len(near) % 2 else (near[len(near) // 2 - 1] + near[len(near) // 2]) / 2
            if ref > 0 and n > HIGH * ref:
                notes.append(f"{lab}: {n:,.0f} is {n / ref:.1f}x the usual {ref:,.0f} for that month. Too big?")
            elif ref > 0 and n < LOW * ref:
                notes.append(f"{lab}: {n:,.0f} is only {n / ref:.0%} of the usual {ref:,.0f} for that month. Too small?")
        if n < 1000:
            notes.append(f"{lab}: {n:,.0f} bags looks tiny. Typed in '000 bags?")
    return notes


def _save_gbe(old: float, new: float):
    msg = f"Setting | Soluble GBE multiplier: {old:g} -> {new:g}"
    text, _ = gh.commit(SETTINGS_PATH, lambda _t: (json.dumps({"soluble_gbe": new}, indent=2) + "\n", None), msg)
    with open(SETTINGS, "w", encoding="utf-8", newline="") as f:
        f.write(text)
    load_settings.clear()


def render_input(raw: pd.DataFrame, gbe: float):
    if st.session_state.get("mc_flash"):
        st.toast(st.session_state.pop("mc_flash"))
    editable = gh.enabled()
    vals = _cal_values(raw)
    last_data = max(y for (_, y, _) in vals) if vals else 2026
    show_n = st.radio("Years shown", ["Recent", f"All ({FIRST_YEAR}-{LAST_YEAR})"], horizontal=True,
                      label_visibility="collapsed", key="mc_edit_years")
    hi_y = min(LAST_YEAR, max(last_data, pd.Timestamp.today().year))
    yr_list = (list(range(FIRST_YEAR, LAST_YEAR + 1)) if show_n.startswith("All")
               else list(range(max(FIRST_YEAR, hi_y - 2), hi_y + 1)))                              # Recent = last 3 years

    with st.container(border=True):
        st.markdown("<div class='card-title'>Monthly exports, bags</div>"
                    "<div class='card-desc'>Calendar years, Jan to Dec, oldest first, ready up to 2030. "
                    + ("Click a cell, type, then Save. Blank removes the value."
                       if editable else "Read-only: add github_token in Secrets to edit.") + "</div>",
                    unsafe_allow_html=True)
        cfg = {CAL[m - 1]: st.column_config.TextColumn(CAL[m - 1], alignment="right", width=74) for m in range(1, 13)}
        cfg["_index"] = st.column_config.TextColumn("Year", width=64)
        before, after, keys = {}, {}, []
        for comm in BASE:
            g = _edit_grid(vals, comm, yr_list)
            key = f"mc_edit_{comm}_{show_n[:3]}"
            keys.append(key)
            st.markdown(f"<div class='grid-head'>{comm}</div>", unsafe_allow_html=True)
            before[comm] = g
            after[comm] = st.data_editor(g, column_config=cfg, disabled=not editable, width="content",
                                         row_height=26, height=len(g) * 26 + 48, key=key)
        if editable:
            try:
                changes = [c for comm in BASE for c in _changes(comm, before[comm], after[comm])]
            except ValueError:
                st.error("Numbers only (commas are fine).")
                changes = []
            neg = [c for c in changes if c[4] is not None and c[4] < 0]
            if neg:
                st.error("Values cannot be negative.")
                changes = []
            bc = st.columns([1, 1, 4], vertical_alignment="center")
            save = bc[0].button("Save", type="primary", disabled=not changes, width="stretch", key="mc_save")
            if bc[1].button("Undo", disabled=not changes, width="stretch", key="mc_undo"):
                for k in keys:
                    st.session_state.pop(k, None)
                st.session_state.pop("mc_pending", None)
                st.rerun()
            if changes:
                bc[2].markdown(f"<div class='card-desc' style='margin:0'>{len(changes)} unsaved cell(s).</div>",
                               unsafe_allow_html=True)
            if save:
                notes = _sanity_notes(changes, vals, raw)
                if not notes:
                    _do_save(changes, keys)
                st.session_state["mc_pending"] = notes
            if st.session_state.get("mc_pending") and changes:
                cc = st.columns([3.2, 0.6, 0.6, 1.6], vertical_alignment="center")
                cc[0].warning(" ".join(st.session_state["mc_pending"]) + " Save anyway?")
                if cc[1].button("Override", type="primary", width="stretch", key="mc_override"):
                    _do_save(changes, keys)
                if cc[2].button("Cancel", width="stretch", key="mc_cancel"):
                    st.session_state.pop("mc_pending", None)
                    st.rerun()

    # Soluble GBE multiplier, further down
    with st.container(border=True):
        st.markdown("<div class='card-title'>Soluble GBE multiplier</div>"
                    "<div class='card-desc'>Soluble is multiplied by this (green bean equivalent) before it is added to "
                    "Arabica or Robusta.</div>", unsafe_allow_html=True)
        gc = st.columns([1.2, 1, 5], vertical_alignment="center")
        newg = gc[0].number_input("GBE multiplier", min_value=0.1, max_value=10.0, value=float(gbe), step=0.05,
                                  format="%.2f", label_visibility="collapsed", key="mc_gbe", disabled=not editable)
        if gc[1].button("Save multiplier", disabled=(not editable) or abs(newg - gbe) < 1e-9, width="stretch",
                        key="mc_gbe_save"):
            try:
                with st.spinner("Saving..."):
                    _save_gbe(gbe, round(float(newg), 4))
            except (gh.GitHubError, Exception) as ex:
                st.error(f"GitHub save failed: {ex}")
            else:
                st.session_state["mc_flash"] = f"Soluble GBE multiplier set to {newg:g}."
                st.rerun()

    if editable:
        with st.expander("Save history", expanded=False):
            _history()


def _do_save(changes, keys):
    try:
        with st.spinner("Saving..."):
            _save_exports(changes)
    except (gh.GitHubError, Exception) as ex:
        st.error(f"GitHub save failed: {ex}")
        return
    for k in keys:
        st.session_state.pop(k, None)
    st.session_state.pop("mc_pending", None)
    st.session_state["mc_flash"] = f"Saved {len(changes)} change(s)."
    st.rerun()


def _history():
    try:
        items = gh.history(EXPORTS_PATH) + gh.history(SETTINGS_PATH)
    except Exception as ex:
        st.markdown(f"<div class='card-desc'>Not available: {ex}</div>", unsafe_allow_html=True)
        return
    rows = []
    for ts, msg in sorted(items, key=lambda x: x[0], reverse=True):
        when = pd.Timestamp(ts).tz_convert(TZ)
        first, _, body = msg.partition("\n")
        if first.startswith("Monthly exports |"):
            for ln in [x for x in body.splitlines() if x.strip()]:
                what, _, vals = ln.partition(": ")
                old, _, new = vals.partition(" -> ")
                rows.append((when, what, old, new, "Dashboard"))
        elif first.startswith("Setting |"):
            what, _, vals = first[len("Setting | "):].partition(": ")
            old, _, new = vals.partition(" -> ")
            rows.append((when, what, old, new, "Dashboard"))
        else:
            rows.append((when, first[:60], "", "", "Local push"))
    rows = rows[:20]
    body = "".join(f"<tr><td class='ts'>{w:%d %b %H:%M}</td><td class='dt'>{what}</td><td>{o}</td><td class='b'>{n}</td>"
                   f"<td class='ts'>{via}</td></tr>" for w, what, o, n, via in rows)
    st.markdown("<div class='card-desc'>Latest 20 changes, Amsterdam time (CET).</div>"
                "<table class='dtab'><tr class='sub'><th>Saved at</th><th>What</th><th>Old</th><th>New</th><th>Via</th></tr>"
                f"{body}</table>", unsafe_allow_html=True)
