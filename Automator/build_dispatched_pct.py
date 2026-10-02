"""One-off: Dispatched% sheet of Database/Cecafe Daily History.xlsx (untouched) -> Database/dispatched_pct_history.csv

Sheet layout: column A = day of month, columns B.. = months (header like "Feb'26"), value = Dispatched / Registrations
(all types together, as a fraction). #N/A or blank = Cecafe showed nothing that day.
Output: date, pct  (one row per real calendar date with a value)
"""
import shutil, tempfile
from pathlib import Path

import openpyxl
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "Database" / "Cecafe Daily History.xlsx"
OUT = ROOT / "Database" / "dispatched_pct_history.csv"
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def main():
    tmp = Path(tempfile.gettempdir()) / "cecafe_pct_src.xlsx"          # Excel may have the file locked
    shutil.copy(SRC, tmp)
    ws = openpyxl.load_workbook(tmp, data_only=True)["Dispatched%"]
    rows = list(ws.iter_rows(values_only=True))
    head = rows[0]
    cols = {}
    for i, h in enumerate(head[1:], start=1):
        if isinstance(h, str) and "'" in h:
            mon, yy = h.split("'")
            cols[i] = (2000 + int(yy), MONTHS.index(mon) + 1)
    out = []
    for r in rows[1:]:
        day = r[0]
        if not isinstance(day, (int, float)):
            continue
        for i, (y, m) in cols.items():
            v = r[i]
            if isinstance(v, (int, float)):
                try:
                    out.append((pd.Timestamp(y, m, int(day)), float(v)))
                except ValueError:                                      # e.g. 30-Feb
                    pass
    df = pd.DataFrame(out, columns=["date", "pct"]).sort_values("date")
    df.to_csv(OUT, index=False, date_format="%Y-%m-%d")
    print(f"wrote {OUT}  rows={len(df)}  {df.date.min().date()} -> {df.date.max().date()}")
    print(df.groupby(df.date.dt.to_period("M")).size().to_string())


if __name__ == "__main__":
    main()
