"""
Generate a synthetic (but realistic) dataset for an EdTech coaching platform.

The data mimics a coaching institute running JEE / NEET / Foundation batches
with weekly Computer-Based Tests (CBTs), daily attendance and homework.
All names and records are FAKE and generated with a fixed random seed so the
results are fully reproducible.

Run:  python scripts/generate_data.py
Output: data/raw/*.csv
"""
from pathlib import Path
import numpy as np
import pandas as pd

SEED = 42
rng = np.random.default_rng(SEED)
OUT = Path(__file__).resolve().parents[1] / "data" / "raw"
OUT.mkdir(parents=True, exist_ok=True)

START, END = pd.Timestamp("2025-07-07"), pd.Timestamp("2025-12-27")  # 25 weeks
N_STUDENTS = 1500

# ---------------------------------------------------------------- reference
PROGRAMS = {
    "JEE":        ["Physics", "Chemistry", "Mathematics"],
    "NEET":       ["Physics", "Chemistry", "Biology"],
    "Foundation": ["Physics", "Chemistry", "Mathematics", "Biology"],
}
TOPICS = {  # (topic, difficulty 1-3)
    "Physics": [("Kinematics", 1), ("Laws of Motion", 2), ("Work, Energy & Power", 2),
                ("Rotational Motion", 3), ("Gravitation", 2), ("Electrostatics", 3),
                ("Current Electricity", 2), ("Optics", 2)],
    "Chemistry": [("Mole Concept", 1), ("Atomic Structure", 1), ("Chemical Bonding", 2),
                  ("Thermodynamics", 3), ("Equilibrium", 3), ("Organic Basics (GOC)", 3),
                  ("Periodic Table", 1), ("Redox Reactions", 2)],
    "Mathematics": [("Quadratic Equations", 1), ("Trigonometry", 2), ("Sequences & Series", 2),
                    ("Permutations & Combinations", 3), ("Straight Lines", 1),
                    ("Limits & Continuity", 2), ("Differentiation", 2), ("Probability", 3)],
    "Biology": [("Cell Biology", 1), ("Plant Physiology", 2), ("Human Physiology", 2),
                ("Genetics", 3), ("Ecology", 1), ("Biomolecules", 2),
                ("Reproduction", 2), ("Evolution", 1)],
}
FIRST_M = ["Aarav","Vivaan","Aditya","Arjun","Sai","Reyansh","Krishna","Ishaan","Rohan","Kabir",
           "Rahul","Karthik","Nikhil","Varun","Harsh","Manish","Pranav","Siddharth","Yash","Akash"]
FIRST_F = ["Ananya","Diya","Aadhya","Saanvi","Kavya","Isha","Meera","Riya","Sneha","Pooja",
           "Divya","Neha","Shreya","Tanvi","Aditi","Lakshmi","Priya","Nandini","Keerthi","Bhavya"]
FIRST = FIRST_M + FIRST_F
LAST = ["Sharma","Rao","Reddy","Nair","Kumar","Shetty","Iyer","Patil","Gowda","Hegde",
        "Menon","Singh","Verma","Joshi","Kulkarni","Bhat","Das","Pillai","Naik","Prabhu"]
SCHOOLS = [("SCH01","Green Valley Public School","Mangaluru"),
           ("SCH02","Sunrise High School","Udupi"),
           ("SCH03","Lakeview Vidyalaya","Mangaluru"),
           ("SCH04","Coastal Heritage School","Mangaluru"),
           ("SCH05","Bluebell International School","Bengaluru"),
           ("SCH06","Riverside English School","Mangaluru"),
           ("SCH07","Silver Oak Academy","Udupi"),
           ("SCH08","Pinecrest Residential School","Bengaluru")]

# ---------------------------------------------------------------- teachers
teachers, tid = [], 1
for subj in ["Physics", "Chemistry", "Mathematics", "Biology"]:
    for _ in range(4):
        teachers.append({"teacher_id": f"T{tid:03d}",
                         "teacher_name": f"{rng.choice(FIRST)} {rng.choice(LAST)}",
                         "subject": subj,
                         "experience_years": int(rng.integers(1, 16))})
        tid += 1
teachers = pd.DataFrame(teachers)
# hidden teacher effect (some teachers get better results)
teacher_effect = dict(zip(teachers.teacher_id, rng.normal(0, 0.18, len(teachers))))

# ---------------------------------------------------------------- batches
batches, bid = [], 1
for program, grades in [("JEE", [11, 12]), ("NEET", [11, 12]), ("Foundation", [9, 10])]:
    for grade in grades:
        for section in ["A", "B", "C"]:
            batches.append({"batch_id": f"B{bid:02d}", "batch_name": f"{program}-{grade}{section}",
                            "program": program, "grade": grade,
                            "mode": "Online" if section == "C" else "Offline"})
            bid += 1
batches = pd.DataFrame(batches)

# batch-subject-teacher mapping
bst = []
for b in batches.itertuples():
    for subj in PROGRAMS[b.program]:
        t = teachers[teachers.subject == subj].sample(1, random_state=int(rng.integers(1e9))).iloc[0]
        bst.append({"batch_id": b.batch_id, "subject": subj, "teacher_id": t.teacher_id})
batch_subject_teacher = pd.DataFrame(bst)

# ---------------------------------------------------------------- topics
topics, tpid = [], 1
for subj, lst in TOPICS.items():
    for name, diff in lst:
        topics.append({"topic_id": f"TP{tpid:02d}", "subject": subj,
                       "topic_name": name, "difficulty": diff})
        tpid += 1
topics = pd.DataFrame(topics)

# ---------------------------------------------------------------- students
batch_ids = rng.choice(batches.batch_id, N_STUDENTS, p=None)
ability = rng.normal(0, 1, N_STUDENTS)              # hidden academic ability
engagement = np.clip(rng.normal(0.8, 0.12, N_STUDENTS), 0.35, 0.99)  # hidden base engagement
join_offset = np.where(rng.random(N_STUDENTS) < 0.8, 0, rng.integers(7, 70, N_STUDENTS))
schools = rng.integers(0, len(SCHOOLS), N_STUDENTS)

genders = rng.choice(["M", "F"], N_STUDENTS, p=[0.55, 0.45])
students = pd.DataFrame({
    "student_id": [f"S{i:04d}" for i in range(1, N_STUDENTS + 1)],
    "student_name": [f"{rng.choice(FIRST_M if g == 'M' else FIRST_F)} {rng.choice(LAST)}" for g in genders],
    "gender": genders,
    "batch_id": batch_ids,
    "school_id": [SCHOOLS[s][0] for s in schools],
    "join_date": [START + pd.Timedelta(days=int(d)) for d in join_offset],
})
b_lookup = batches.set_index("batch_id")
online = students.batch_id.map(b_lookup["mode"]).eq("Online").values
engagement = np.where(online, engagement - 0.07, engagement)   # online slightly lower attendance
late = join_offset > 0
engagement = np.where(late, engagement - 0.04, engagement)

# engagement decays for a subset -> potential dropouts
decay = np.where(rng.random(N_STUDENTS) < 0.14, rng.uniform(0.004, 0.012, N_STUDENTS), 0.0)
students["status"] = "Active"
students["dropout_date"] = pd.NaT

schools_df = pd.DataFrame(SCHOOLS, columns=["school_id", "school_name", "city"])

# ---------------------------------------------------------------- calendar
days = pd.date_range(START, END, freq="D")
class_days = days[days.dayofweek < 6]        # Mon-Sat classes
test_days = days[days.dayofweek == 6]        # Sunday CBTs

# ---------------------------------------------------------------- attendance (+ dropout)
att_rows = []
dropout_date = [None] * N_STUDENTS
for i in range(N_STUDENTS):
    jd = students.join_date.iat[i]
    p0 = engagement[i]
    for k, d in enumerate(class_days):
        if d < jd:
            continue
        week = (d - jd).days / 7
        p = np.clip(p0 - decay[i] * week * 7 / 3, 0.05, 0.99)
        if decay[i] > 0 and p < 0.45 and dropout_date[i] is None and rng.random() < 0.08:
            dropout_date[i] = d
        if dropout_date[i] is not None:
            break
        status = "Present" if rng.random() < p else ("Late" if rng.random() < 0.15 else "Absent")
        att_rows.append((students.student_id.iat[i], d.date(), status))
attendance = pd.DataFrame(att_rows, columns=["student_id", "class_date", "status"])
students["dropout_date"] = pd.to_datetime(dropout_date)
students.loc[students.dropout_date.notna(), "status"] = "Dropped"

# attendance rate per student per week (used to drive scores)
attendance["week"] = pd.to_datetime(attendance.class_date).dt.to_period("W-SUN")
att_week = (attendance.assign(p=attendance.status.ne("Absent"))
            .groupby(["student_id", "week"]).p.mean())

# ---------------------------------------------------------------- tests & results
tests, results, test_id = [], [], 1
sid_idx = {s: i for i, s in enumerate(students.student_id)}
students_by_batch = students.groupby("batch_id").student_id.apply(list)
subj_cycle = {}
for w, td in enumerate(test_days):
    for b in batches.itertuples():
        subjects = PROGRAMS[b.program]
        subj = subjects[w % len(subjects)]
        subj_topics = topics[topics.subject == subj]
        # each test covers 2 topics, progressing through the syllabus
        idx = (w // len(subjects)) * 2 % len(subj_topics)
        tp = subj_topics.iloc[[idx, (idx + 1) % len(subj_topics)]]
        tcode = f"CBT{test_id:04d}"
        tests.append({"test_id": tcode, "batch_id": b.batch_id, "test_date": td.date(),
                      "subject": subj, "total_questions": 30, "max_marks": 120})
        teacher = batch_subject_teacher.query("batch_id == @b.batch_id and subject == @subj").teacher_id.iat[0]
        wk = pd.Period(td, freq="W-SUN")
        for s in students_by_batch.get(b.batch_id, []):
            i = sid_idx[s]
            if td < students.join_date.iat[i]:
                continue
            dd = students.dropout_date.iat[i]
            if pd.notna(dd) and td >= dd:
                continue
            a = att_week.get((s, wk), np.nan)
            if np.isnan(a):
                a = engagement[i]
            if rng.random() > 0.35 + 0.65 * a:      # low attenders skip tests
                continue
            for t in tp.itertuples():
                n_q = 15
                attempted = int(np.clip(rng.normal(13 - 3 * (1 - a), 1.5), 5, n_q))
                logit = (0.35 + 0.9 * ability[i] + 1.6 * (a - 0.8) + teacher_effect[teacher]
                         - 0.45 * (t.difficulty - 2) + 0.012 * w + rng.normal(0, 0.35))
                acc = 1 / (1 + np.exp(-logit))
                correct = int(rng.binomial(attempted, acc))
                wrong = attempted - correct
                results.append({"test_id": tcode, "student_id": s, "topic_id": t.topic_id,
                                "questions": n_q, "attempted": attempted, "correct": correct,
                                "wrong": wrong, "marks": 4 * correct - wrong,
                                "time_spent_min": round(float(np.clip(rng.normal(45 - 8 * ability[i], 8), 15, 60)), 1)})
        test_id += 1
tests = pd.DataFrame(tests)
test_results = pd.DataFrame(results)

# ---------------------------------------------------------------- homework
hw_rows, hw_id = [], 1
homework_assign = []
for w, td in enumerate(test_days):
    assigned = td - pd.Timedelta(days=6)
    due = td - pd.Timedelta(days=2)
    for b in batches.itertuples():
        for subj in PROGRAMS[b.program]:
            hid = f"HW{hw_id:05d}"
            homework_assign.append({"homework_id": hid, "batch_id": b.batch_id, "subject": subj,
                                    "assigned_date": assigned.date(), "due_date": due.date(), "max_score": 20})
            hw_id += 1
            for s in students_by_batch.get(b.batch_id, []):
                i = sid_idx[s]
                if assigned < students.join_date.iat[i]:
                    continue
                dd = students.dropout_date.iat[i]
                if pd.notna(dd) and assigned >= dd:
                    continue
                p_sub = np.clip(engagement[i] - decay[i] * w * 2 + 0.05 * ability[i], 0.05, 0.98)
                if rng.random() < p_sub:
                    late_days = int(rng.choice([0, 0, 0, 0, 1, 2, 3]))
                    score = int(np.clip(rng.normal(13 + 3 * ability[i], 2.5), 0, 20))
                    hw_rows.append({"homework_id": hid, "student_id": s,
                                    "submitted_date": (due + pd.Timedelta(days=late_days)).date(),
                                    "score": score})
homework = pd.DataFrame(homework_assign)
homework_submissions = pd.DataFrame(hw_rows)

# ---------------------------------------------------------------- add a few data-quality issues (to clean)
dq = test_results.sample(25, random_state=SEED).copy()
test_results = pd.concat([test_results, dq], ignore_index=True)            # 25 duplicate rows
nan_idx = test_results.sample(40, random_state=SEED + 1).index
test_results.loc[nan_idx, "time_spent_min"] = np.nan                       # missing time values
students.loc[students.sample(12, random_state=SEED).index, "gender"] = students.gender.str.lower()  # 'm'/'f'

# ---------------------------------------------------------------- save
attendance = attendance.drop(columns="week")
files = {"schools": schools_df, "teachers": teachers, "batches": batches,
         "batch_subject_teacher": batch_subject_teacher, "topics": topics,
         "students": students, "attendance": attendance, "tests": tests,
         "test_results": test_results, "homework": homework,
         "homework_submissions": homework_submissions}
for name, df in files.items():
    df.to_csv(OUT / f"{name}.csv", index=False)
    print(f"{name:24s} {len(df):>8,d} rows")
