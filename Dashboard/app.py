import base64
import calendar
import io
from pathlib import Path

import pandas as pd
import requests
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


LOOKBACK = 5          # years in the min-max band


def month_dim(year, month):
    return calendar.monthrange(year, month)[1]


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


def base_layout(fig, title, height=430):
    fig.update_layout(
        template="plotly_white", height=height, margin=dict(l=10, r=10, t=44, b=60),
        title=dict(text=title, x=0.01, font=dict(size=15, color=NAVY)),
        legend=dict(orientation="h", y=-0.1, x=0, xanchor="left", yanchor="top", font=dict(size=11)),
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
if st.session_state.get("month_sel") not in labels:
    st.session_state["month_sel"] = labels[-1]


def _step(k):
    i = labels.index(st.session_state["month_sel"]) + k
    st.session_state["month_sel"] = labels[min(max(i, 0), len(labels) - 1)]


tc = st.columns([5.2, 0.7, 1.4, 0.7], vertical_alignment="bottom")
_i = labels.index(st.session_state["month_sel"])
tc[1].button("< Prev", on_click=_step, args=(-1,), disabled=_i == 0, width="stretch")
tc[2].selectbox("Month", labels[::-1], key="month_sel", label_visibility="collapsed")
tc[3].button("Next >", on_click=_step, args=(1,), disabled=_i == len(labels) - 1, width="stretch")
sel = st.session_state["month_sel"]
tc[0].markdown(f"## Cecafe Daily Registrations: {sel.split()[0]}'{sel.split()[1][2:]}")

with st.sidebar:
    sel_y, sel_m = ym_all[labels.index(sel)]
    min_year = st.slider("History from", int(df.index.year.min()), sel_y - 1, max(sel_y - 5, int(df.index.year.min())))
    connect = st.toggle("Connect gaps", value=False)
    st.markdown(f"<div class='side-note'>Latest data: <b>{last_date:%d %b %Y}</b><br>"
                f"Cumulative month-to-date registrations, bags.<br>"
                f"Blank days are split equally in Adj daily.</div>", unsafe_allow_html=True)

t_daily, t_acc, t_entry = st.tabs(["Daily", "Projection Accuracy", "Entry"])

with t_daily:
    # --------------------------------------------------------------------------- daily table (Excel layout)
    dim_sel = calendar.monthrange(sel_y, sel_m)[1]
    cur = {c: month_series(df[c], sel_y, sel_m) for c in COMMS}
    days = sorted(set(cur["Arabica"].index) | set(cur["Robusta"].index))


    def cell(v, bold=False, early=False):
        return f"<td class='{'b' if bold else ''}{' early' if early else ''}'>{fmt(v)}</td>"


    rows_html = ""
    prev = {c: 0.0 for c in COMMS}
    last_val = {c: 0.0 for c in COMMS}
    for d_ in days:
        a, r = cur["Arabica"].get(d_), cur["Robusta"].get(d_)
        chg = {}
        for c, v in (("Arabica", a), ("Robusta", r)):
            if v is not None and pd.notna(v):
                chg[c] = v - prev[c]
                prev[c] = v
                last_val[c] = v
            else:
                chg[c] = None
        chg_tot = None if chg["Arabica"] is None or chg["Robusta"] is None else chg["Arabica"] + chg["Robusta"]
        cum_tot = None if a is None or r is None else a + r
        pa = None if a is None else a / d_ * dim_sel          # linear month-end projection as of that day
        pb = None if r is None else r / d_ * dim_sel
        pt = None if pa is None or pb is None else pa + pb
        rows_html += (f"<tr><td class='dt'>{d_:02d}-{MONTHS[sel_m - 1]}</td>"
                      + cell(chg["Arabica"]) + cell(chg["Robusta"]) + cell(chg_tot, True)
                      + cell(a) + cell(r) + cell(cum_tot, True)
                      + cell(pa, early=d_ <= 10) + cell(pb, early=d_ <= 10) + cell(pt, True, early=d_ <= 10) + "</tr>")

    st.markdown("""
    <style>
    .dtab { width: auto; border-collapse: collapse; font-size: 11.5px; line-height: 1.15; background: #fff; }
    .dtab th { text-align: center; padding: 2px 8px; font-weight: 600; white-space: nowrap; }
    .dtab .g1 { background: #fff; color: #1a1a2e; border: 1px solid #1a1a2e; }
    .dtab .g2 { background: #b8c4d9; color: #0a2463; border: 1px solid #1a1a2e; }
    .dtab .g3 { background: #e8f3ee; color: #0a2463; border: 1px solid #1a1a2e; }
    .dtab td.early { color: #b3b9c9; background: #f4f5f8; font-weight: 400; }
    .dtab .sub th { background: #0a2463; color: #fff; }
    .dtab td { text-align: right; padding: 1px 8px; border-bottom: 1px solid #eef0f6; white-space: nowrap; }
    .dtab td.dt { text-align: center; background: #f0f2f8; color: #1a1a2e; }
    .dtab td.b { font-weight: 700; background: #f6f7fb; }
    </style>""", unsafe_allow_html=True)
    st.markdown(
        "<table class='dtab'>"
        "<tr><th></th><th colspan='3' class='g1'>Change with Previous</th><th colspan='3' class='g2'>Cumulative Current Month</th><th colspan='3' class='g3'>Linear Month-end</th></tr>"
        "<tr class='sub'><th>Until</th><th>Arabica</th><th>Robusta</th><th>Total</th><th>Arabica</th><th>Robusta</th><th>Total</th><th>Arabica</th><th>Robusta</th><th>Total</th></tr>"
        + rows_html + "</table>"
        "<div class='side-note' style='margin-top:4px'>Grey = day 1-10, too early to project.</div>", unsafe_allow_html=True)
    st.write("")


    # --------------------------------------------------------------------------- charts: Arabica row, Robusta row
    def render_charts(comm):
        s = df[comm]
        cur_s = month_series(s, sel_y, sel_m)
        dim = calendar.monthrange(sel_y, sel_m)[1]
        pr = project(cur_s, sel_y, sel_m)
        c1, c2 = st.columns(2)

        fig = go.Figure()
        band = {}
        for y in range(sel_y - LOOKBACK, sel_y):
            hm = month_series(s, y, sel_m)
            if not hm.empty:
                band[y] = full_curve(hm, month_dim(y, sel_m)).reindex(range(1, dim + 1))
        if len(band) >= 2:
            bd = pd.DataFrame(band)
            fig.add_trace(go.Scatter(x=bd.index, y=bd.max(axis=1), mode="lines", line=dict(width=0),
                                     hoverinfo="skip", showlegend=False))
            fig.add_trace(go.Scatter(x=bd.index, y=bd.min(axis=1), mode="lines", line=dict(width=0),
                                     fill="tonexty", fillcolor="rgba(31,138,156,0.14)",
                                     name=f"{len(band)}y min-max", hoverinfo="skip"))
        years = [y for y in range(min_year, sel_y) if not month_series(s, y, sel_m).empty]
        for i, y in enumerate(years):
            h = month_series(s, y, sel_m).reindex(range(1, calendar.monthrange(y, sel_m)[1] + 1))
            back = len(years) - i
            col = HIST_COLORS[-back] if back <= len(HIST_COLORS) else GREY
            fig.add_trace(go.Scatter(x=h.index, y=h.values, name=str(y), mode="lines+markers",
                                     line=dict(color=col, width=2), marker=dict(size=5, symbol="x"),
                                     connectgaps=connect))
        if not cur_s.empty:
            c = cur_s.reindex(range(1, dim + 1))
            ad = adjusted_daily(cur_s)
            fig.add_trace(go.Bar(x=ad.index, y=ad.values, name="Adj daily", marker_color="#c9ced9",
                                 opacity=0.85, yaxis="y2"))
            fig.add_trace(go.Scatter(x=c.index, y=c.values, name=str(sel_y), mode="lines+markers",
                                     line=dict(color=NAVY, width=3.5),
                                     marker=dict(size=8, color="#f2c200", line=dict(color=NAVY, width=1.5)),
                                     connectgaps=connect))
            if pr and 10 < pr[0] < dim:          # no projection line in the first 10 days
                fig.add_trace(go.Scatter(x=[pr[0], dim], y=[pr[1], pr[2]], name="Projection", mode="lines+markers",
                                         line=dict(color=NAVY, width=2, dash="dot"),
                                         marker=dict(size=7, symbol="diamond")))
            fig.update_layout(yaxis2=dict(overlaying="y", side="right", range=[0, max(ad.max() * 5, 1)],
                                          showgrid=False, visible=False))
        base_layout(fig, f"{comm}: {MONTHS[sel_m - 1]} vs same month, previous years")
        ymax = max([float(pd.Series(tr.y).max()) for tr in fig.data if tr.yaxis != "y2" and len(tr.y)] or [1.0])
        fig.update_yaxes(range=[0, ymax * 1.05], selector=dict(anchor="x"))   # zero line = bar baseline
        with c1:
            st.plotly_chart(fig, width="stretch")

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


    for comm in COMMS:
        render_charts(comm)


# --------------------------------------------------------------------------- projection accuracy
with t_acc:
    scope = st.radio("Months", ["All months", f"{MONTHS[sel_m - 1]} only"], horizontal=True,
                     label_visibility="collapsed")
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
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=g.index, y=g.hi, mode="lines", line=dict(width=0),
                                     hoverinfo="skip", showlegend=False))
            fig.add_trace(go.Scatter(x=g.index, y=g.lo, mode="lines", line=dict(width=0), fill="tonexty",
                                     fillcolor="rgba(31,138,156,0.14)", name="80% of months"))
            fig.add_trace(go.Scatter(x=g.index, y=g.bias, name="Typical miss (+ = too high)", mode="lines+markers",
                                     line=dict(color=NAVY, width=3), marker=dict(size=6)))
            fig.add_hline(y=0, line=dict(color=GREY, width=1))
            base_layout(fig, f"{comm}: linear projection miss % by day ({n_months} months)", height=360)
            fig.update_yaxes(ticksuffix="%", tickformat=".0f")
            st.plotly_chart(fig, width="stretch")
            body_ = ""
            for d_ in (5, 10, 15, 20, 25):
                if d_ in g.index:
                    r = g.loc[d_]
                    body_ += (f"<tr><td class='dt'>Day {d_}</td><td class='b'>{r.miss:.1f}%</td><td>{r.bias:+.1f}%</td>"
                              f"<td>{r.lo:+.0f}% to {r.hi:+.0f}%</td></tr>")
            st.markdown("<table class='dtab'><tr class='sub'><th>As of</th><th>Avg miss</th><th>Bias</th>"
                        "<th>80% range</th></tr>" + body_ + "</table>", unsafe_allow_html=True)


# --------------------------------------------------------------------------- entry: write a row to GitHub
REPO, REPO_PATH = "virataryaa/Daily-Cecafe", "Database/cecafe_daily.csv"
GH_API = f"https://api.github.com/repos/{REPO}/contents/{REPO_PATH}"


def gh_headers():
    tok = str(st.secrets["github_token"]).strip().strip('"').strip("'")
    return {"Authorization": f"Bearer {tok}", "Accept": "application/vnd.github+json"}


class GitHubError(Exception):
    pass


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
        raise GitHubError(f"GitHub {r.status_code}: {msg}. {hint}")


def gh_read():
    r = requests.get(GH_API, headers=gh_headers(), params={"ref": "main"}, timeout=20)
    gh_check(r)
    j = r.json()
    return pd.read_csv(io.StringIO(base64.b64decode(j["content"]).decode("utf-8"))), j["sha"]


def gh_write(frame: pd.DataFrame, sha: str, msg: str):
    body = {"message": msg, "branch": "main", "sha": sha,
            "content": base64.b64encode(frame.to_csv(index=False, lineterminator="\n").encode()).decode()}
    r = requests.put(GH_API, headers=gh_headers(), json=body, timeout=20)
    gh_check(r)


def parse_num(txt):
    txt = (txt or "").replace(",", "").strip()
    if not txt:
        return None
    return float(txt)


with t_entry:
    try:
        _has_secrets = "github_token" in st.secrets
    except Exception:                       # no secrets file at all (local run)
        _has_secrets = False
    if not _has_secrets:
        st.info("Entry is off: add github_token in Streamlit Secrets.")
    else:
        st.markdown("<div class='card-desc'>Cumulative month-to-date from Cecafe. Leave blank if not shown.</div>",
                    unsafe_allow_html=True)
        with st.form("entry", clear_on_submit=False):
            ec = st.columns([1.2, 1, 1])
            e_date = ec[0].date_input("Date", value=pd.Timestamp.today().date(), format="DD/MM/YYYY")
            e_ara = ec[1].text_input("Arabica", placeholder="e.g. 151,804")
            e_rob = ec[2].text_input("Robusta", placeholder="e.g. 77,905")
            ok = st.form_submit_button("Save", type="primary")
        if ok:
            try:
                va, vr = parse_num(e_ara), parse_num(e_rob)
            except ValueError:
                va = vr = "bad"
            errors = []
            if va == "bad":
                errors.append("Numbers only (commas are fine).")
            elif va is None and vr is None:
                errors.append("Enter at least one number.")
            if not errors:
                try:
                    cur_csv, sha = gh_read()
                except (GitHubError, requests.RequestException) as ex:
                    st.error(str(ex))
                    st.stop()
                cur_csv["date"] = pd.to_datetime(cur_csv["date"])
                d0 = pd.Timestamp(e_date)
                same_m = cur_csv[(cur_csv.date.dt.year == d0.year) & (cur_csv.date.dt.month == d0.month)
                                 & (cur_csv.date < d0)]
                for name, v in (("Arabica", va), ("Robusta", vr)):
                    prev_v = same_m[name].dropna()
                    if v is not None and not prev_v.empty and v < prev_v.iloc[-1] * 0.95:
                        errors.append(f"{name} {v:,.0f} is below the previous day ({prev_v.iloc[-1]:,.0f}). "
                                      "Cumulative should not fall.")
            if errors:
                for e in errors:
                    st.error(e)
            else:
                existed = (cur_csv.date == d0).any()
                cur_csv = cur_csv[cur_csv.date != d0]
                cur_csv = pd.concat([cur_csv, pd.DataFrame([{"date": d0, "Arabica": va, "Robusta": vr}])])
                cur_csv = cur_csv.sort_values("date")
                cur_csv["date"] = cur_csv["date"].dt.strftime("%Y-%m-%d")
                try:
                    gh_write(cur_csv, sha, f"Entry {d0:%Y-%m-%d} via dashboard")
                except (GitHubError, requests.RequestException) as ex:
                    st.error(f"GitHub save failed: {ex}")
                else:
                    cur_csv.to_csv(DATA, index=False, lineterminator="\n")   # show it now, before redeploy
                    st.cache_data.clear()
                    st.success(f"{'Updated' if existed else 'Saved'} {d0:%d %b %Y}: "
                               f"Arabica {fmt(va)}, Robusta {fmt(vr)}.")
        last5 = df.dropna(how="all").tail(5).iloc[::-1]
        st.markdown("<div class='card-desc' style='margin-top:10px'>Last 5 entries</div>", unsafe_allow_html=True)
        st.markdown("<table class='dtab'><tr class='sub'><th>Date</th><th>Arabica</th><th>Robusta</th></tr>"
                    + "".join(f"<tr><td class='dt'>{i:%d-%b-%y}</td>{cell(r.Arabica)}{cell(r.Robusta)}</tr>"
                              for i, r in last5.iterrows()) + "</table>", unsafe_allow_html=True)
