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


def style(fig, height=340, legend="bottom", months=None, unified=False, fmt=",.0f", **extra):
    xaxis = dict(gridcolor=GRID, color=AXIS, showgrid=False)
    if months:
        xaxis.update(categoryorder="array", categoryarray=months)
    xaxis.update(extra.pop("xaxis", {}))
    yaxis = dict(gridcolor=GRID, color=AXIS, hoverformat=fmt, tickformat=fmt, separatethousands=True)
    yaxis.update(extra.pop("yaxis", {}))
    margin = dict(t=30, b=30, l=10, r=10)
    leg = dict(bgcolor="rgba(0,0,0,0)", orientation="h", x=0, font=dict(size=11))
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

    with st.container(border=True):
        a1, a2 = st.columns([2.6, 8], vertical_alignment="center")
        mode = a1.radio("View", ["Visuals", "Tabular view", "Input"], horizontal=True, label_visibility="collapsed",
                        key="mc_mode")
        if mode == "Input":
            a2.markdown("<div class='card-desc' style='margin:0'>Edit any month. Charts and tables use the same data.</div>",
                        unsafe_allow_html=True)
        else:
            comm = a2.radio("Type", COMMS, horizontal=True, label_visibility="collapsed", key="mc_comm")
            b1, b2, b3, _ = st.columns([2.8, 2.2, 1.8, 6], vertical_alignment="center")
            unit = b1.radio("Unit", list(UNITS), horizontal=True, label_visibility="collapsed", key="mc_unit")
            span = b2.radio("Years", ["Last 5", "Last 10", "All"], horizontal=True, label_visibility="collapsed",
                            key="mc_span")
    if mode == "Input":
        render_input(raw, gbe)
        return

    factor, fmt = UNITS[unit]
    piv = pivot(raw, comm, factor, gbe)
    if piv.empty:
        st.info("No data for this selection.")
        return

    years = piv.index.tolist()
    latest_cy = years[-1]
    prev_cy = years[-2] if len(years) >= 2 else None
    valid = piv.loc[latest_cy].dropna().index
    common = int(valid.max()) if len(valid) else 12
    ref = [y for y in years if y != latest_cy][-10:]                  # last 10 complete crop years
    ytd = piv[list(range(1, common + 1))].sum(axis=1, min_count=1)
    yoy = ytd.pct_change() * 100
    cut = f"{MONTHS[0]}–{MONTHS[common - 1]}"
    n_show = {"Last 5": 5, "Last 10": 10, "All": len(years)}[span]
    shown = years[-n_show:]
    sc = f"{comm} · {unit}" + (f" · Soluble x{gbe:g} GBE" if "Soluble" in TYPES[comm] and len(TYPES[comm]) > 1 else "")
    with b3:
        proj = _projection(piv, latest_cy, prev_cy, common, ref, unit, fmt)

    ytd_now = ytd.get(latest_cy)
    yo = yoy.get(latest_cy)
    line = [f"Crop year <b>{latest_cy}</b> to {MONTHS[common - 1]}", f"YTD <b>{format(ytd_now, fmt)}</b>"]
    if pd.notna(yo):
        line.append(f"{yo:+.1f}% YoY")
    if proj:
        line.append(f"Projected full year <b>{format(ytd_now + sum(proj.values()), fmt)}</b>")
    st.markdown(f"<div class='card-desc' style='margin:6px 0 2px'>{' · '.join(line)}</div>", unsafe_allow_html=True)

    styles = year_styles(sorted(set(shown) | set(years[-3:])))
    ht = f"%{{y:{fmt}}} {unit}"
    k = "mc"

    if mode == "Visuals":
        l, r = st.columns(2, gap="medium")
        with l:
            h, w = st.columns([1.4, 1], vertical_alignment="bottom")
            with h:
                heading("Monthly exports", f"{sc} · band = L{len(ref)}Y range")
            view = w.radio("Seasonal view", ["Latest vs range", "All years"], horizontal=True, key=f"{k}_view",
                           label_visibility="collapsed")
            plot_years = shown if view == "All years" else [y for y in shown if y in (latest_cy, prev_cy)]
            fig = go.Figure()
            _band(fig, piv, ref, fmt)
            for y in plot_years:
                c, wd = styles[y]
                s = piv.loc[y].dropna()
                fig.add_trace(go.Scatter(x=[MONTHS[m - 1] for m in s.index], y=s.values, name=y, mode="lines",
                                         line=dict(color=c, width=wd), hovertemplate=ht))
            if proj and latest_cy in shown:
                xs = [MONTHS[common - 1]] + [MONTHS[m - 1] for m in proj]
                fig.add_trace(_proj_trace(xs, [piv.loc[latest_cy, common]] + list(proj.values()), latest_cy, ht))
            show(style(fig, height=360, months=MONTHS, unified=True, fmt=fmt), key=f"{k}_seasonal")

        with r:
            heading("Cumulative exports", f"{sc} · last 5 CY vs L{len(ref)}Y avg")
            fig = go.Figure()
            if len(ref) >= 2:
                avg_cum = piv.loc[ref].mean().cumsum()
                fig.add_trace(go.Scatter(x=MONTHS, y=avg_cum.values, name=f"Avg L{len(ref)}Y", mode="lines",
                                         line=dict(color=AXIS, width=1.5, dash="dot"), hovertemplate=ht))
            light = ["#dde2ec", "#c9d0e0", "#b3bdd4"]
            last5 = years[-5:]
            for i, y in enumerate(last5):
                c, wd = styles[y] if y in (latest_cy, prev_cy) else (light[-(len(last5) - 2) + i], 1.4)
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
            show(style(fig, height=360, months=MONTHS, unified=True, fmt=fmt), key=f"{k}_cum")

        l, r = st.columns(2, gap="medium")
        with l:
            heading(f"YTD {cut}", f"{sc} · label = YoY")
            yy = [y for y in years if y in shown or y == latest_cy]
            colors = [NAVY if y == latest_cy else "#c3cbe0" for y in yy]
            labels = [f"{yoy[y]:+.1f}%" if pd.notna(yoy[y]) else "" for y in yy]
            fig = go.Figure(go.Bar(x=yy, y=ytd[yy].values, marker_color=colors, text=labels, textposition="outside",
                                   textfont=dict(size=11, color=AXIS), cliponaxis=False,
                                   hovertemplate=f"%{{x}}: %{{y:{fmt}}} {unit}<extra></extra>"))
            show(style(fig, height=300, legend=None, fmt=fmt, yaxis=dict(rangemode="tozero")), key=f"{k}_ytd")
        with r:
            h, w = st.columns([1.6, 1], vertical_alignment="bottom")
            with h:
                heading("Rolling exports", f"{sc} · trailing sum")
            seed(f"{k}_roll", "12m")
            win = w.radio("Window", ["1m", "3m", "6m", "12m"], horizontal=True, key=f"{k}_roll",
                          label_visibility="collapsed")
            stack = piv.stack().dropna()
            mon = pd.Series(stack.values, index=[month_dates(cy, int(cm)) for cy, cm in stack.index]).sort_index()
            roll = mon.rolling(int(win[:-1])).sum().dropna()
            fig = go.Figure(go.Scatter(x=roll.index, y=roll.values, mode="lines", line=dict(color=TEAL, width=2),
                                       fill="tozeroy", fillcolor=rgba(TEAL, 0.08),
                                       hovertemplate=f"%{{x|%b-%y}}: %{{y:{fmt}}} {unit}<extra></extra>"))
            show(style(fig, height=300, legend=None, fmt=fmt), key=f"{k}_rolling")
    else:
        heading("Monthly exports", f"{sc} · {latest_cy} to {MONTHS[common - 1]} · Min/Avg/Max L{len(ref)}Y")
        _heatmap(piv, shown, latest_cy, common, ytd, yoy, ref, fmt)


# ── Pieces ────────────────────────────────────────────────────────────────────
def _band(fig, piv, ref, fmt):
    if len(ref) < 2:
        return
    b = piv.loc[ref]
    fig.add_trace(go.Scatter(x=MONTHS, y=b.max().values, name="Max", mode="lines", showlegend=False,
                             line=dict(width=0), hovertemplate=f"%{{y:{fmt}}}"))
    fig.add_trace(go.Scatter(x=MONTHS, y=b.min().values, name=f"Min–Max L{len(ref)}Y", mode="lines",
                             line=dict(width=0), fill="tonexty", fillcolor=rgba(NAVY, 0.07),
                             hovertemplate=f"%{{y:{fmt}}}"))
    fig.add_trace(go.Scatter(x=MONTHS, y=b.mean().values, name=f"Avg L{len(ref)}Y", mode="lines",
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
    with st.popover(f"Projection: {method}", width="stretch"):
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


def _heatmap(piv, shown, latest_cy, common, ytd, yoy, ref, fmt):
    hdr = MONTHS + ["Total", "YTD", "YoY"]
    body = piv.loc[[y for y in shown if y in piv.index]]
    vals = body.to_numpy(dtype=float)
    vals = vals[~np.isnan(vals) & (vals > 0)]
    lo, hi = (float(vals.min()), float(vals.max())) if vals.size else (0.0, 1.0)

    def month_cells(s, heat=True):
        return [t_cell("") if pd.isna(s[m]) or s[m] == 0
                else t_cell(format(s[m], fmt), bg=seq_color(s[m], lo, hi) if heat else None) for m in range(1, 13)]

    rows = []
    for y in body.index:
        s = body.loc[y]
        total = "" if y == latest_cy and common < 12 else format(s.sum(), fmt)
        yv = yoy.get(y, np.nan)
        cells = month_cells(s) + [t_cell(total, "x"), t_cell(format(ytd[y], fmt), "x"),
                                  t_cell("" if pd.isna(yv) else f"{yv:+.1f}%", "up" if yv >= 0 else "down")]
        rows.append(t_row(y, cells))
        if y == latest_cy and len(ref) >= 2:
            avg = piv.loc[ref].mean()
            dev = [(s[m] / avg[m] - 1) * 100 if pd.notna(s[m]) and s[m] > 0 and avg[m] > 0 else np.nan
                   for m in range(1, 13)]
            lim = max([abs(v) for v in dev if pd.notna(v)] or [20])
            dc = [t_cell("") if pd.isna(v) else t_cell(f"{v:+.0f}%", bg=div_color(v, lim)) for v in dev]
            rows.append(t_row(f"vs Avg L{len(ref)}Y", dc + [t_cell("", "x")] * 2 + [t_cell("")], "ref"))

    if len(ref) >= 2:
        rows.append(t_sep(len(hdr) + 1))
        rb = piv.loc[ref]
        tot, ytd_r = rb.sum(axis=1), ytd[ref]
        for name, agg in [("Min", "min"), ("Avg", "mean"), ("Max", "max")]:
            cells = month_cells(getattr(rb, agg)(), heat=False) + [
                t_cell(format(getattr(tot, agg)(), fmt), "x"), t_cell(format(getattr(ytd_r, agg)(), fmt), "x"),
                t_cell("")]
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


def _next_cy(cy: str) -> str:
    a, b = int(cy[:2]), int(cy[3:])
    return f"{(a + 1) % 100:02d}/{(b + 1) % 100:02d}"


def _edit_grid(raw: pd.DataFrame, comm: str, crop_years: list) -> pd.DataFrame:
    d = raw[raw["commodity"] == comm].pivot_table(index="crop_year", columns="cm", values="bags", aggfunc="sum")
    d = d.reindex(index=crop_years, columns=range(1, 13))
    g = pd.DataFrame({MONTHS[m - 1]: [_fmt0(d.loc[cy, m]) for cy in crop_years] for m in range(1, 13)}, index=crop_years)
    g["Total"] = [_fmt0(d.loc[cy].sum()) if d.loc[cy].notna().any() else "" for cy in crop_years]     # read-only
    g.index.name = "Crop year"
    return g


def _changes(raw, comm, before: pd.DataFrame, after: pd.DataFrame) -> list:
    """[(comm, crop year, crop month, old, new)] for every edited cell. Raises ValueError on non-numbers."""
    out = []
    for cy in before.index:
        for m in range(1, 13):
            col = MONTHS[m - 1]
            old, new = _num(before.loc[cy, col]), _num(after.loc[cy, col])
            if old != new:
                out.append((comm, cy, m, old, new))
    return out


def _save_exports(changes: list, who: str = "dashboard"):
    lines = [f"{c} {cy} {MONTHS[m - 1]}: {_fmt0(o) or '-'} -> {_fmt0(n) or '-'}" for c, cy, m, o, n in changes]
    msg = f"Monthly exports | {len(changes)} change(s)\n\n" + "\n".join(lines)

    def apply(text):
        d = pd.read_csv(io.StringIO(text))
        for c, cy, m, o, n in changes:
            hit = (d["commodity"] == c) & (d["crop_year"] == cy) & (d["cm"] == m)
            d = d[~hit]
            if n is not None:
                d = pd.concat([d, pd.DataFrame([{"commodity": c, "crop_year": cy, "cm": m, "bags": n}])])
        d["_o"] = d["commodity"].map({c: i for i, c in enumerate(BASE)})
        d = d.sort_values(["_o", "crop_year", "cm"]).drop(columns="_o")
        d["bags"] = d["bags"].round().astype("int64")
        return d.to_csv(index=False, lineterminator="\n"), None
    new_text, _ = gh.commit(EXPORTS_PATH, apply, msg)
    with open(DATA, "w", encoding="utf-8", newline="") as f:             # local copy, so the disc has it too
        f.write(new_text)
    load.clear()


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
    all_cy = sorted(raw["crop_year"].unique())
    nxt = _next_cy(all_cy[-1])
    show_n = st.radio("Crop years shown", ["Last 6", "All"], horizontal=True, label_visibility="collapsed", key="mc_edit_n")
    cy_list = (all_cy + [nxt])[-(7 if show_n == "Last 6" else len(all_cy) + 1):][::-1]          # newest first

    with st.container(border=True):
        st.markdown("<div class='card-title'>Monthly exports, bags</div>"
                    "<div class='card-desc'>Crop years Jul to Jun, newest first (the next crop year is ready at the top). "
                    + ("Click a cell, type, then Save. Blank removes the value."
                       if editable else "Read-only: add github_token in Secrets to edit.") + "</div>",
                    unsafe_allow_html=True)
        cfg = {MONTHS[m - 1]: st.column_config.TextColumn(MONTHS[m - 1], alignment="right", width=74) for m in range(1, 13)}
        cfg["Total"] = st.column_config.TextColumn("Total", alignment="right", width=88, disabled=True)
        cfg["_index"] = st.column_config.TextColumn("Crop year", width=92)
        before, after, keys = {}, {}, []
        for comm in BASE:
            g = _edit_grid(raw, comm, cy_list)
            key = f"mc_edit_{comm}_{show_n}"
            keys.append(key)
            st.markdown(f"<div class='grid-head'>{comm}</div>", unsafe_allow_html=True)
            before[comm] = g
            shown = g.style.set_properties(subset=["Total"], **{"background-color": "#e9ecf2", "font-weight": "600"})
            after[comm] = st.data_editor(shown, column_config=cfg, disabled=not editable, width="content",
                                         row_height=26, height=len(g) * 26 + 48, key=key)
        if editable:
            try:
                changes = [c for comm in BASE for c in _changes(raw, comm, before[comm], after[comm])]
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
                notes = []
                for c, cy, m, o, n in changes:                       # extra-zero check against the type's biggest month
                    cap = raw.loc[raw["commodity"] == c, "bags"].max()
                    if n is not None and cap and n > 1.6 * cap:
                        notes.append(f"{c} {cy} {MONTHS[m - 1]} {n:,.0f} is far above anything seen (max {cap:,.0f}). Extra zero?")
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
