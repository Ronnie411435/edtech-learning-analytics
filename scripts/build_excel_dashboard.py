"""
Build an interactive Excel dashboard (dashboard/EdTech_Dashboard.xlsx).
KPIs and band tables are live Excel formulas (COUNTIFS / AVERAGEIFS) driven by
a Program / Mode filter, so the dashboard updates when the filter changes.

Run:  python scripts/build_excel_dashboard.py
"""
from pathlib import Path
import sqlite3
import pandas as pd
from openpyxl import Workbook
from openpyxl.chart import BarChart, LineChart, Reference
from openpyxl.chart.label import DataLabelList
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.worksheet.table import Table, TableStyleInfo

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "dashboard" / "EdTech_Dashboard.xlsx"
con = sqlite3.connect(ROOT / "data" / "edtech.db")
sql = (ROOT / "sql" / "04_analysis_queries.sql").read_text()
def query_n(n):
    import re
    return pd.read_sql(re.search(rf"-- Q{n}:.*?(?=\n-- Q\d+:|\Z)", sql, re.S).group(0), con)

summary = pd.read_sql("SELECT * FROM v_student_summary", con)
topics = pd.read_sql("SELECT subject, topic_name, difficulty, students_tested, accuracy_pct "
                     "FROM v_topic_performance ORDER BY accuracy_pct", con)
trend = query_n(6).pivot(index="test_date", columns="program", values="moving_avg_4wk").reset_index()
at_risk = query_n(9)
teachers = query_n(7)

F = "Arial"
NAVY, BLUE, LIGHT, GREY = "0D366B", "2A78D6", "EAF2FC", "52514E"
h1 = Font(name=F, size=18, bold=True, color=NAVY)
h2 = Font(name=F, size=12, bold=True, color=NAVY)
body = Font(name=F, size=10)
muted = Font(name=F, size=9, italic=True, color=GREY)
hdr_font = Font(name=F, size=10, bold=True, color="FFFFFF")
hdr_fill = PatternFill("solid", fgColor=NAVY)
tile_fill = PatternFill("solid", fgColor=LIGHT)
input_fill = PatternFill("solid", fgColor="FFF2CC")
thin = Side(style="thin", color="D9D9D9")

wb = Workbook()

# ------------------------------------------------------------------ data sheets
def write_table(ws, df, name, pct_cols=()):
    ws.append(list(df.columns))
    for row in df.itertuples(index=False):
        ws.append([None if (isinstance(v, float) and pd.isna(v)) else v for v in row])
    ref = f"A1:{get_column_letter(df.shape[1])}{len(df) + 1}"
    t = Table(displayName=name, ref=ref)
    t.tableStyleInfo = TableStyleInfo(name="TableStyleMedium2", showRowStripes=True)
    ws.add_table(t)
    for c in ws[1]:
        c.font = Font(name=F, bold=True, color="FFFFFF")
    for row in ws.iter_rows(min_row=2):
        for c in row:
            c.font = body
    for i, col in enumerate(df.columns, 1):
        ws.column_dimensions[get_column_letter(i)].width = max(11, min(30, len(col) + 3))
    ws.freeze_panes = "A2"

ws_dash = wb.active
ws_dash.title = "Dashboard"
ws_data = wb.create_sheet("Student_Data")
write_table(ws_data, summary, "StudentData")
ws_top = wb.create_sheet("Topics")
write_table(ws_top, topics, "TopicPerf")
ws_tr = wb.create_sheet("Weekly_Trend")
write_table(ws_tr, trend[["test_date", "JEE", "NEET", "Foundation"]], "WeeklyTrend")
ws_te = wb.create_sheet("Teachers")
write_table(ws_te, teachers, "TeacherPerf")
ws_risk = wb.create_sheet("At_Risk_Students")
write_table(ws_risk, at_risk, "AtRisk")

# column letters in Student_Data
col = {c: get_column_letter(i + 1) for i, c in enumerate(summary.columns)}
N = len(summary) + 1
def rng(c):
    return f"Student_Data!${col[c]}$2:${col[c]}${N}"

# ------------------------------------------------------------------ dashboard
d = ws_dash
d.sheet_view.showGridLines = False
d.page_setup.orientation = "landscape"; d.page_setup.fitToWidth = 1; d.page_setup.fitToHeight = 0
d.sheet_properties.pageSetUpPr.fitToPage = True
for c, w in zip("ABCDEFGHIJKLMN", [2, 22, 14, 3, 22, 14, 3, 22, 14, 3, 22, 14, 3, 3]):
    d.column_dimensions[c].width = w

d["B2"] = "EdTech Learning Analytics Dashboard"; d["B2"].font = h1
d["B3"] = "Coaching-institute CBT, attendance & homework data | Jul–Dec 2025 | synthetic data"; d["B3"].font = muted

# filters
d["B5"] = "Program filter"; d["B5"].font = Font(name=F, bold=True)
d["C5"] = "All"; d["C5"].fill = input_fill; d["C5"].font = Font(name=F, bold=True, color="0000FF")
d["E5"] = "Mode filter"; d["E5"].font = Font(name=F, bold=True)
d["F5"] = "All"; d["F5"].fill = input_fill; d["F5"].font = Font(name=F, bold=True, color="0000FF")
d["H5"] = "← pick from the yellow drop-downs; every number below recalculates"; d["H5"].font = muted
dv1 = DataValidation(type="list", formula1='"All,JEE,NEET,Foundation"', allow_blank=False)
dv2 = DataValidation(type="list", formula1='"All,Online,Offline"', allow_blank=False)
d.add_data_validation(dv1); d.add_data_validation(dv2); dv1.add("C5"); dv2.add("F5")
# helper criteria (wildcard when All)
d["M5"] = '=IF($C$5="All","*",$C$5)'
d["N5"] = '=IF($F$5="All","*",$F$5)'
d.column_dimensions["M"].hidden = True; d.column_dimensions["N"].hidden = True
P, M = "Dashboard!$M$5", "Dashboard!$N$5"
crit = f'{rng("program")},{P},{rng("mode")},{M}'

# KPI tiles
tiles = [
    ("B", "Students", f"=COUNTIFS({crit})", "#,##0"),
    ("E", "Dropout rate", f'=IFERROR(COUNTIFS({crit},{rng("status")},"Dropped")/COUNTIFS({crit}),0)', "0.0%"),
    ("H", "Avg attendance", f'=IFERROR(AVERAGEIFS({rng("attendance_pct")},{crit})/100,0)', "0.0%"),
    ("K", "Avg CBT score", f'=IFERROR(AVERAGEIFS({rng("avg_score_pct")},{crit})/100,0)', "0.0%"),
]
for c, label, formula, fmt in tiles:
    c2 = get_column_letter(d[c + "1"].column + 1)
    for r in (7, 8):
        for cc in (c, c2):
            d[f"{cc}{r}"].fill = tile_fill
    d[f"{c}7"] = label; d[f"{c}7"].font = Font(name=F, size=10, color=GREY)
    d[f"{c}8"] = formula; d[f"{c}8"].font = Font(name=F, size=22, bold=True, color=NAVY)
    d[f"{c}8"].number_format = fmt
    d.row_dimensions[8].height = 34
d["B9"] = "Avg homework submission"; d["B9"].font = Font(name=F, size=10, color=GREY)
d["C9"] = f'=IFERROR(AVERAGEIFS({rng("hw_submission_pct")},{crit})/100,0)'; d["C9"].number_format = "0.0%"
d["C9"].font = Font(name=F, bold=True, color=NAVY)
d["E9"] = "Active students"; d["E9"].font = Font(name=F, size=10, color=GREY)
d["F9"] = f'=COUNTIFS({crit},{rng("status")},"Active")'; d["F9"].font = Font(name=F, bold=True, color=NAVY)

def band_table(top, title, first_col_label, metric, bands):
    d[f"B{top}"] = title; d[f"B{top}"].font = h2
    heads = [first_col_label, "Students", "Avg score %", "Dropout %"]
    cols = ["B", "C", "E", "F"]
    for cl, h in zip(cols, heads):
        cell = d[f"{cl}{top + 1}"]; cell.value = h; cell.font = hdr_font; cell.fill = hdr_fill
        cell.alignment = Alignment(horizontal="center")
    d[f"D{top + 1}"].fill = hdr_fill
    for j, (label, lo, hi) in enumerate(bands):
        r = top + 2 + j
        c = f'{crit},{rng(metric)},">={lo}",{rng(metric)},"<{hi}"'
        d[f"B{r}"] = label
        d[f"C{r}"] = f"=COUNTIFS({c})"
        d[f"E{r}"] = f'=IFERROR(AVERAGEIFS({rng("avg_score_pct")},{c}),0)'
        d[f"F{r}"] = f'=IFERROR(COUNTIFS({c},{rng("status")},"Dropped")/C{r},0)'
        d[f"E{r}"].number_format = "0.0"; d[f"F{r}"].number_format = "0.0%"
        for cl in cols + ["D"]:
            d[f"{cl}{r}"].font = body; d[f"{cl}{r}"].border = Border(bottom=thin)
    return top + 2, top + 1 + len(bands)

a0, a1 = band_table(11, "Score & dropout by attendance band", "Attendance", "attendance_pct",
                    [("Below 60%", 0, 60), ("60–75%", 60, 75), ("75–90%", 75, 90), ("90%+", 90, 101)])
h0, h1_ = band_table(19, "Score & dropout by homework band", "Homework submitted", "hw_submission_pct",
                     [("Below 40%", 0, 40), ("40–60%", 40, 60), ("60–80%", 60, 80), ("80%+", 80, 101)])
d["B25"] = "Scores are averages of each student's CBT score (% of max marks, +4/−1 marking)."; d["B25"].font = muted

def bar(title, cats_ref, vals_ref, anchor, color=BLUE, w=15, h=7.5, horizontal=False, ytitle=None):
    ch = BarChart(); ch.type = "bar" if horizontal else "col"
    ch.title = title; ch.style = 2; ch.legend = None
    ch.add_data(vals_ref, titles_from_data=False); ch.set_categories(cats_ref)
    s = ch.series[0]; s.graphicalProperties.solidFill = color; s.graphicalProperties.line.noFill = True
    s.dLbls = DataLabelList(); s.dLbls.showVal = True
    for k in ('showSerName','showCatName','showLegendKey','showPercent'): setattr(s.dLbls, k, False)
    ch.gapWidth = 80; ch.width, ch.height = w, h
    ch.y_axis.majorGridlines = None
    if ytitle: ch.y_axis.title = ytitle
    ch.y_axis.delete = False; ch.x_axis.delete = False
    d.add_chart(ch, anchor)

bar("Avg CBT score by attendance band", Reference(d, min_col=2, min_row=a0, max_row=a1),
    Reference(d, min_col=5, min_row=a0, max_row=a1), "H11")
bar("Avg CBT score by homework band", Reference(d, min_col=2, min_row=h0, max_row=h1_),
    Reference(d, min_col=5, min_row=h0, max_row=h1_), "H27")

# topic chart (bottom 10)
ch = BarChart(); ch.type = "bar"; ch.title = "10 weakest topics – answer accuracy %"; ch.style = 2; ch.legend = None
ch.add_data(Reference(ws_top, min_col=5, min_row=2, max_row=11)); ch.set_categories(Reference(ws_top, min_col=2, min_row=2, max_row=11))
s = ch.series[0]; s.graphicalProperties.solidFill = NAVY; s.graphicalProperties.line.noFill = True
s.dLbls = DataLabelList(); s.dLbls.showVal = True
for k in ('showSerName','showCatName','showLegendKey','showPercent'): setattr(s.dLbls, k, False)
ch.y_axis.majorGridlines = None; ch.y_axis.scaling.min = 40; ch.x_axis.scaling.orientation = "maxMin"
ch.y_axis.delete = False; ch.x_axis.delete = False
ch.width, ch.height = 15, 9
d.add_chart(ch, "B27")

# trend chart
lc = LineChart(); lc.title = "Weekly CBT score by program (4-week moving avg, %)"; lc.style = 2
lc.add_data(Reference(ws_tr, min_col=2, max_col=4, min_row=1, max_row=len(trend) + 1), titles_from_data=True)
lc.set_categories(Reference(ws_tr, min_col=1, min_row=2, max_row=len(trend) + 1))
for s, c in zip(lc.series, [BLUE, "EB6834", "1BAF7A"]):
    s.graphicalProperties.line.solidFill = c; s.graphicalProperties.line.width = 22000; s.smooth = False
lc.y_axis.scaling.min = 30; lc.legend.position = "b"; lc.width, lc.height = 30, 8
lc.y_axis.delete = False; lc.x_axis.delete = False
d.add_chart(lc, "B46")

d["B63"] = "At-risk students (active, flagged by SQL rule Q9): see the At_Risk_Students sheet."; d["B63"].font = muted
d["B64"] = f'=COUNTA(AtRisk[student_id])&" students flagged; "&COUNTIF(AtRisk[risk_flags],">=2")&" with 2+ risk flags"'
d["B64"].font = Font(name=F, bold=True, color="C00000")

# ------------------------------------------------------------------ about sheet
ab = wb.create_sheet("About")
lines = [
    ("About this workbook", h1),
    ("Source: data/edtech.db built from synthetic data (scripts/generate_data.py, seed 42). All names are fictional.", body),
    ("Student_Data = SQL view v_student_summary (one row per student).", body),
    ("Topics = view v_topic_performance · Weekly_Trend = query Q6 · Teachers = Q7 · At_Risk_Students = Q9.", body),
    ("Dashboard KPIs use COUNTIFS / AVERAGEIFS on Student_Data, filtered by the yellow Program and Mode cells.", body),
    ("Percent columns in Student_Data are stored as 0–100 values (e.g. 78.4 = 78.4%).", body),
    ("Rebuild: python scripts/build_excel_dashboard.py", body),
]
for i, (t, f) in enumerate(lines, 1):
    ab.cell(row=i, column=1, value=t).font = f
ab.column_dimensions["A"].width = 110

OUT.parent.mkdir(exist_ok=True)
wb.save(OUT)
print(f"Saved {OUT.relative_to(ROOT)}")
