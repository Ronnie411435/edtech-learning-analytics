"""
Clean the raw CSVs and write analysis-ready files to data/clean/.

Data-quality issues handled:
  1. Duplicate rows in test_results (same test / student / topic)
  2. Missing time_spent_min values -> filled with that student's median time
  3. Inconsistent gender codes ('m' / 'f') -> upper-case 'M' / 'F'
  4. Basic validity checks (correct + wrong == attempted, marks formula, dates)

Run:  python scripts/clean_data.py
"""
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW, CLEAN = ROOT / "data" / "raw", ROOT / "data" / "clean"
CLEAN.mkdir(parents=True, exist_ok=True)

tables = {p.stem: pd.read_csv(p) for p in sorted(RAW.glob("*.csv"))}
log = []

# 1. duplicates
tr = tables["test_results"]
before = len(tr)
tr = tr.drop_duplicates(subset=["test_id", "student_id", "topic_id"])
log.append(f"test_results: removed {before - len(tr)} duplicate rows")

# 2. missing time values
missing = tr.time_spent_min.isna().sum()
tr["time_spent_min"] = tr.time_spent_min.fillna(
    tr.groupby("student_id").time_spent_min.transform("median")).round(1)
log.append(f"test_results: filled {missing} missing time_spent_min values with student median")

# 4. validity checks
assert (tr.correct + tr.wrong == tr.attempted).all(), "correct + wrong must equal attempted"
assert (tr.marks == 4 * tr.correct - tr.wrong).all(), "marks must follow +4 / -1 scheme"
assert (tr.attempted <= tr.questions).all()
tables["test_results"] = tr

# 3. gender codes
st = tables["students"]
bad = (~st.gender.isin(["M", "F"])).sum()
st["gender"] = st.gender.str.upper()
log.append(f"students: standardised {bad} gender codes to upper case")
assert (pd.to_datetime(st.dropout_date).fillna(pd.Timestamp.max) >= pd.to_datetime(st.join_date)).all()
tables["students"] = st

for name, df in tables.items():
    df.to_csv(CLEAN / f"{name}.csv", index=False)

print("\n".join(log))
print(f"Wrote {len(tables)} clean files to {CLEAN.relative_to(ROOT)}")
