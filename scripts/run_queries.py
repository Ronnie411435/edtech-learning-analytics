"""
Run every query in sql/04_analysis_queries.sql against data/edtech.db
and save each result to outputs/query_results/Q<n>.csv

Run:  python scripts/run_queries.py
"""
from pathlib import Path
import re, sqlite3
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "query_results"
OUT.mkdir(parents=True, exist_ok=True)
sql = (ROOT / "sql" / "04_analysis_queries.sql").read_text()
blocks = re.split(r"\n(?=-- Q\d+:)", sql)
con = sqlite3.connect(ROOT / "data" / "edtech.db")
pd.set_option("display.width", 160, "display.max_columns", 20)
for block in blocks:
    m = re.match(r"-- (Q\d+): (.*)", block)
    if not m:
        continue
    qid, title = m.groups()
    df = pd.read_sql(block, con)
    df.to_csv(OUT / f"{qid}.csv", index=False)
    print(f"\n=== {qid}: {title}  ({len(df)} rows)")
    print(df.head(12).to_string(index=False))
