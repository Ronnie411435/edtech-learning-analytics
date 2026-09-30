"""
Build a local SQLite database (data/edtech.db) from the cleaned CSVs,
using the same schema and views as the MySQL version.

Run:  python scripts/build_database.py
"""
from pathlib import Path
import sqlite3
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "edtech.db"
ORDER = ["schools", "teachers", "batches", "batch_subject_teacher", "topics", "students",
         "attendance", "tests", "test_results", "homework", "homework_submissions"]

if DB.exists():
    DB.unlink()
con = sqlite3.connect(DB)
con.executescript((ROOT / "sql" / "01_schema.sql").read_text())
for name in ORDER:
    df = pd.read_csv(ROOT / "data" / "clean" / f"{name}.csv")
    df.to_sql(name, con, if_exists="append", index=False)
    print(f"loaded {name:24s} {len(df):>8,d} rows")
con.executescript((ROOT / "sql" / "03_views.sql").read_text())
con.commit()
con.close()
print(f"Database ready: {DB.relative_to(ROOT)}")
