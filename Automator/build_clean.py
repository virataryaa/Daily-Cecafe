"""One-off: turn the desk Excel (Database/Cecafe Daily History.xlsx, untouched) into the clean entry CSV.

Output: Database/cecafe_daily.csv  ->  date, Arabica, Robusta  (cumulative month-to-date registrations, bags)
One row per real calendar date that has at least one observation. Blank = Cecafe showed nothing that day.
"""
import shutil, tempfile
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "Database" / "Cecafe Daily History.xlsx"
OUT = ROOT / "Database" / "cecafe_daily.csv"


def load_sheet(path, sheet):
    d = pd.read_excel(path, sheet_name=sheet)
    d = d.rename(columns={"Unnamed: 2": "2020"})          # Arabica 2020 column has no header
    d.columns = [str(c) for c in d.columns]
    d["Date"] = pd.to_datetime(d["Date"])
    rows = []
    for y in [c for c in d.columns if c.isdigit()]:
        for _, r in d.iterrows():
            try:
                dt = pd.Timestamp(int(y), r["Month"], r["Date"].day)
            except ValueError:                             # Feb 29 in non-leap
                continue
            v = pd.to_numeric(r[y], errors="coerce")       # '#N/A', '-' -> NaN
            if pd.notna(v):
                rows.append((dt, float(v)))
    return pd.Series(dict(rows)).sort_index()


def main():
    tmp = Path(tempfile.gettempdir()) / "cecafe_daily_src.xlsx"   # Excel may have the file locked
    shutil.copy(SRC, tmp)
    ser = {c: load_sheet(tmp, c) for c in ["Arabica", "Robusta"]}
    df = pd.DataFrame(ser)
    df.index.name = "date"
    df = df[df.index <= "2026-09-30"]
    flags = []
    for c in df.columns:
        for m, g in df[c].dropna().groupby([df[c].dropna().index.year, df[c].dropna().index.month]):
            bad = g[g.diff() < 0]
            for dt in bad.index:
                flags.append((c, dt.date(), g.shift(1)[dt], g[dt]))
    df.to_csv(OUT)
    print(f"wrote {OUT}  rows={len(df)}  {df.index.min().date()} -> {df.index.max().date()}")
    print(df.notna().sum().to_string())
    print("Decreasing cumulative (prev -> value):")
    for f in flags:
        print("  ", f)


if __name__ == "__main__":
    main()
