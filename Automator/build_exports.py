"""Monthly exports: the three "... Exports" sheets of Database/Cecafe Daily History.xlsx -> Database/cecafe_exports.csv

Each sheet: rows = crop year ("11/12" = Jul 2011 - Jun 2012), columns = Jul..Jun, values = bags.
Output (long): commodity, crop_year, cm (crop month 1-12, 1 = July), bags
One-off seed. From now on the dashboard "Input" view edits cecafe_exports.csv directly (GitHub + local), so
do NOT re-run this unless you want the Excel values to overwrite the file.
"""
import shutil, tempfile
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "Database" / "Cecafe Daily History.xlsx"
OUT = ROOT / "Database" / "cecafe_exports.csv"
SHEETS = {"Arabica": "Arabica Exports", "Robusta": "Robusta Exports", "Soluble": "Soluble Exports"}


def main():
    tmp = Path(tempfile.gettempdir()) / "cecafe_exports_src.xlsx"      # Excel may have the file locked
    shutil.copy(SRC, tmp)
    parts = []
    for comm, sheet in SHEETS.items():
        d = pd.read_excel(tmp, sheet_name=sheet, index_col=0)
        d.index = d.index.astype(str).str.strip()
        d.columns = range(1, 13)                                         # Jul..Jun -> crop month 1..12
        long = d.stack().rename("bags").reset_index()                    # stack() drops the empty cells
        long.columns = ["crop_year", "cm", "bags"]
        long.insert(0, "commodity", comm)
        parts.append(long)
    out = pd.concat(parts, ignore_index=True)
    out["bags"] = pd.to_numeric(out["bags"], errors="coerce")
    out = out.dropna(subset=["bags"])
    out.to_csv(OUT, index=False)
    print(f"wrote {OUT}  rows={len(out)}")
    print(out.groupby("commodity").agg(first=("crop_year", "min"), last=("crop_year", "max"), n=("bags", "size")).to_string())


if __name__ == "__main__":
    main()
