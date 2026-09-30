# Power BI Dashboard – Build Guide

This guide rebuilds the Excel dashboard as an interactive Power BI report (about 1–2 hours).
When it's done, save it as `dashboard/EdTech_Dashboard.pbix`, take a screenshot as
`images/powerbi_dashboard.png`, and add the screenshot to the main README.

## 1. Load the data
**Home → Get Data → Text/CSV** and load these files from `data/clean/`:
`students`, `batches`, `schools`, `teachers`, `topics`, `tests`, `test_results`,
`attendance`, `homework`, `homework_submissions`, `batch_subject_teacher`.

In **Power Query**:
- Set `join_date`, `dropout_date`, `class_date`, `test_date`, `assigned_date`, `due_date`, `submitted_date` to **Date**.
- In `attendance`, add a custom column: `Attended = if [status] = "Absent" then 0 else 1`.

## 2. Model (star schema)
Create these relationships (Model view, one-to-many, single direction):

| From (many) | To (one) |
|---|---|
| students[batch_id] | batches[batch_id] |
| students[school_id] | schools[school_id] |
| attendance[student_id] | students[student_id] |
| test_results[student_id] | students[student_id] |
| test_results[test_id] | tests[test_id] |
| test_results[topic_id] | topics[topic_id] |
| homework_submissions[student_id] | students[student_id] |
| homework_submissions[homework_id] | homework[homework_id] |

Add a **Date** table: `Date = CALENDAR(DATE(2025,7,1), DATE(2025,12,31))`, mark it as a date table,
and relate `Date[Date]` → `attendance[class_date]` and `Date[Date]` → `tests[test_date]`.

## 3. DAX measures
Create a table called `_Measures` to hold these measures:

```DAX
Total Students = DISTINCTCOUNT ( students[student_id] )

Dropped Students = CALCULATE ( [Total Students], students[status] = "Dropped" )

Dropout Rate % = DIVIDE ( [Dropped Students], [Total Students] )

Attendance % = DIVIDE ( SUM ( attendance[Attended] ), COUNTROWS ( attendance ) )

Accuracy % = DIVIDE ( SUM ( test_results[correct] ), SUM ( test_results[attempted] ) )

CBT Score % = DIVIDE ( SUM ( test_results[marks] ), SUM ( test_results[questions] ) * 4 )

Homework Submitted = COUNTROWS ( homework_submissions )

Avg Homework Score = AVERAGE ( homework_submissions[score] )

Score Rank in Test =
RANKX ( ALLSELECTED ( students[student_name] ), [CBT Score %], , DESC, DENSE )
```

> `CBT Score %` = total marks ÷ maximum possible marks (questions × 4). This is a weighted version of the SQL view, which averages each test's score, so the numbers may differ slightly.

**Attendance band** (calculated column on `students`):
```DAX
Student Attendance % =
DIVIDE (
    CALCULATE ( SUM ( attendance[Attended] ) ),
    CALCULATE ( COUNTROWS ( attendance ) )
)

Attendance Band =
SWITCH ( TRUE (),
    students[Student Attendance %] >= 0.90, "90%+",
    students[Student Attendance %] >= 0.75, "75-90%",
    students[Student Attendance %] >= 0.60, "60-75%",
    "Below 60%" )
```

## 4. Report pages

**Page 1 – Overview**
- Cards: Total Students, Dropout Rate %, Attendance %, CBT Score %, Accuracy %
- Slicers: `batches[program]`, `batches[mode]`, `schools[school_name]`
- Clustered column: `Attendance Band` × `CBT Score %`
- Line chart: `tests[test_date]` × `CBT Score %`, legend = `batches[program]`

**Page 2 – Topics & Teachers**
- Bar chart: `topics[topic_name]` × `Accuracy %`, sorted ascending, colored by `topics[difficulty]`
- Matrix: `topics[subject]` → `topics[topic_name]` with Accuracy % (conditional formatting)
- Table: teacher name, subject, Accuracy %

**Page 3 – At-Risk Students**
- Table: student_name, batch, Attendance %, Homework Submitted, CBT Score %,
  filtered to `students[status] = "Active"` and `Attendance %` < 65%
- Use a drill-through from any batch to this page

## 5. Publish
Save the file, export page 1 as an image, and link it in the README. If you have
a Power BI account, **Publish to web** and add the link too.
