"""Exports by destination: Database/Cecafe Monthly.xlsx (sheet "Database") -> Database/cecafe_destinations.csv

Columns: Year, Month, Type, Destination, Bags (K). The Excel is edited by hand; publish_update.bat validates it
(validate_destinations.py), runs this, and pushes the CSV (the repo ignores *.xlsx).
"""
import shutil, tempfile
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "Database" / "Cecafe Monthly.xlsx"
OUT = ROOT / "Database" / "cecafe_destinations.csv"
COLS = ["Year", "Month", "Type", "Destination", "Bags (K)"]


def main():
    tmp = Path(tempfile.gettempdir()) / "cecafe_destinations_src.xlsx"      # Excel may have the file locked
    shutil.copy(SRC, tmp)
    d = pd.read_excel(tmp, sheet_name="Database")[COLS]
    d = d.dropna(subset=["Bags (K)"]).sort_values(["Type", "Destination", "Year", "Month"])
    d[["Year", "Month"]] = d[["Year", "Month"]].astype(int)
    d.to_csv(OUT, index=False, lineterminator="\n")
    print(f"Wrote {len(d)} rows to {OUT.name} ({d['Year'].min()}-{d['Year'].max()})")


if __name__ == "__main__":
    main()
