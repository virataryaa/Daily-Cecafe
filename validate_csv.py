"""Sanity-check Database/cecafe_daily.csv before pushing. Exit code 1 = problems found."""
import sys
from pathlib import Path

import pandas as pd

CSV = Path(__file__).resolve().parent / "Database" / "cecafe_daily.csv"
problems = []

try:
    d = pd.read_csv(CSV)
except Exception as e:
    print("Cannot read CSV:", e)
    sys.exit(1)

if list(d.columns) != ["date", "Arabica", "Robusta"]:
    problems.append(f"Columns must be date,Arabica,Robusta - found {list(d.columns)}")
else:
    dt = pd.to_datetime(d["date"], errors="coerce")
    for i in d.index[dt.isna()]:
        problems.append(f"Row {i + 2}: bad date '{d.loc[i, 'date']}' (use YYYY-MM-DD)")
    for dup in dt[dt.duplicated() & dt.notna()].dt.date.unique():
        problems.append(f"Duplicate date {dup}")
    for c in ["Arabica", "Robusta"]:
        v = pd.to_numeric(d[c], errors="coerce")
        for i in d.index[v.isna() & d[c].notna()]:
            problems.append(f"Row {i + 2}: {c} is not a number ('{d.loc[i, c]}')")
        d["_v"], d["_dt"] = v, dt
        recent = d[d["_dt"] >= d["_dt"].max() - pd.Timedelta(days=45)]   # history has known old revisions
        for (y, m), g in recent.dropna(subset=["_v", "_dt"]).sort_values("_dt").groupby(
                [recent["_dt"].dt.year, recent["_dt"].dt.month]):
            drop = g[g["_v"].diff() < -0.05 * g["_v"].shift(1)]
            for _, r in drop.iterrows():
                problems.append(f"{c} {r['_dt']:%Y-%m-%d}: cumulative fell more than 5% vs the previous day ({r['_v']:,.0f})")

if problems:
    print("PROBLEMS FOUND:")
    for p in problems:
        print("  -", p)
    sys.exit(1)

last = pd.to_datetime(d["date"]).max()
print(f"OK: {len(d)} rows, latest date {last:%Y-%m-%d}")
