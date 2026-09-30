-- =====================================================================
-- 04_analysis_queries.sql  |  Business questions answered with SQL
-- Portable SQL (MySQL 8.0+ and SQLite 3.25+): CTEs, window functions,
-- CASE, joins, views. Each query starts with a "-- Q<n>:" header.
-- =====================================================================

-- Q1: Platform KPI overview - how healthy is the institute overall?
SELECT
    COUNT(*)                                                           AS total_students,
    SUM(CASE WHEN status = 'Active'  THEN 1 ELSE 0 END)                AS active_students,
    ROUND(100.0 * SUM(CASE WHEN status = 'Dropped' THEN 1 ELSE 0 END) / COUNT(*), 1) AS dropout_rate_pct,
    ROUND(AVG(attendance_pct), 1)                                      AS avg_attendance_pct,
    ROUND(AVG(hw_submission_pct), 1)                                   AS avg_hw_submission_pct,
    ROUND(AVG(avg_score_pct), 1)                                       AS avg_test_score_pct,
    ROUND(AVG(avg_accuracy_pct), 1)                                    AS avg_accuracy_pct
FROM v_student_summary;

-- Q2: Which topics are students weakest in? (10 lowest-accuracy topics)
SELECT subject, topic_name, difficulty, students_tested, accuracy_pct, attempt_rate_pct
FROM v_topic_performance
ORDER BY accuracy_pct
LIMIT 10;

-- Q3: Does attendance drive test scores? Average score by attendance band
SELECT
    CASE
        WHEN attendance_pct >= 90 THEN '1) 90%+'
        WHEN attendance_pct >= 75 THEN '2) 75-90%'
        WHEN attendance_pct >= 60 THEN '3) 60-75%'
        ELSE                           '4) Below 60%'
    END                               AS attendance_band,
    COUNT(*)                          AS students,
    ROUND(AVG(avg_score_pct), 1)      AS avg_score_pct,
    ROUND(AVG(avg_accuracy_pct), 1)   AS avg_accuracy_pct,
    ROUND(100.0 * SUM(CASE WHEN status = 'Dropped' THEN 1 ELSE 0 END) / COUNT(*), 1) AS dropout_rate_pct
FROM v_student_summary
WHERE tests_taken > 0
GROUP BY 1
ORDER BY 1;

-- Q4: Does homework completion matter? Average score by homework band
SELECT
    CASE
        WHEN hw_submission_pct >= 80 THEN '1) 80%+'
        WHEN hw_submission_pct >= 60 THEN '2) 60-80%'
        WHEN hw_submission_pct >= 40 THEN '3) 40-60%'
        ELSE                              '4) Below 40%'
    END                           AS homework_band,
    COUNT(*)                      AS students,
    ROUND(AVG(avg_score_pct), 1)  AS avg_score_pct
FROM v_student_summary
WHERE tests_taken > 0
GROUP BY 1
ORDER BY 1;

-- Q5: Leaderboard - top 3 students in each batch's most recent test
WITH latest_test AS (
    SELECT batch_id, MAX(test_date) AS test_date
    FROM tests
    GROUP BY batch_id
),
ranked AS (
    SELECT sc.batch_id, sc.test_id, sc.subject, sc.student_id, sc.marks, sc.score_pct,
           DENSE_RANK() OVER (PARTITION BY sc.test_id ORDER BY sc.marks DESC) AS test_rank
    FROM v_student_test_scores sc
    JOIN latest_test lt ON lt.batch_id = sc.batch_id AND lt.test_date = sc.test_date
)
SELECT b.batch_name, r.subject, r.test_rank, s.student_name, r.marks, r.score_pct
FROM ranked r
JOIN students s ON s.student_id = r.student_id
JOIN batches  b ON b.batch_id  = r.batch_id
WHERE r.test_rank <= 3
ORDER BY b.batch_name, r.test_rank, s.student_name;

-- Q6: Weekly score trend per program with a 4-week moving average
WITH weekly AS (
    SELECT b.program, sc.test_date, ROUND(AVG(sc.score_pct), 2) AS avg_score_pct
    FROM v_student_test_scores sc
    JOIN batches b ON b.batch_id = sc.batch_id
    GROUP BY b.program, sc.test_date
)
SELECT program, test_date, avg_score_pct,
       ROUND(AVG(avg_score_pct) OVER (PARTITION BY program ORDER BY test_date
                                      ROWS BETWEEN 3 PRECEDING AND CURRENT ROW), 2) AS moving_avg_4wk
FROM weekly
ORDER BY program, test_date;

-- Q7: Teacher effectiveness - accuracy by teacher, ranked within subject
WITH teacher_perf AS (
    SELECT bst.teacher_id, t.subject,
           COUNT(DISTINCT r.student_id)                          AS students_taught,
           ROUND(100.0 * SUM(r.correct) / SUM(r.attempted), 2)   AS accuracy_pct
    FROM test_results r
    JOIN tests t                   ON t.test_id = r.test_id
    JOIN batch_subject_teacher bst ON bst.batch_id = t.batch_id AND bst.subject = t.subject
    GROUP BY bst.teacher_id, t.subject
)
SELECT tp.subject, te.teacher_name, te.experience_years, tp.students_taught, tp.accuracy_pct,
       RANK() OVER (PARTITION BY tp.subject ORDER BY tp.accuracy_pct DESC) AS rank_in_subject
FROM teacher_perf tp
JOIN teachers te ON te.teacher_id = tp.teacher_id
ORDER BY tp.subject, rank_in_subject;

-- Q8: Online vs offline batches - engagement and results by mode and program
SELECT program, mode,
       COUNT(*)                                AS students,
       ROUND(AVG(attendance_pct), 1)           AS avg_attendance_pct,
       ROUND(AVG(hw_submission_pct), 1)        AS avg_hw_submission_pct,
       ROUND(AVG(avg_score_pct), 1)            AS avg_score_pct,
       ROUND(100.0 * SUM(CASE WHEN status = 'Dropped' THEN 1 ELSE 0 END) / COUNT(*), 1) AS dropout_rate_pct
FROM v_student_summary
GROUP BY program, mode
ORDER BY program, mode;

-- Q9: Early-warning list - ACTIVE students at risk of dropping out
--     Rule: attendance in the last 4 weeks < 65%  OR  homework submission < 50%
--           OR score in the last 4 tests fell 10+ points below their earlier average
WITH cutoff AS (
    SELECT MIN(test_date) AS since
    FROM (SELECT DISTINCT test_date FROM tests ORDER BY test_date DESC LIMIT 4) d
),
recent_att AS (
    SELECT a.student_id,
           ROUND(100.0 * SUM(CASE WHEN a.status <> 'Absent' THEN 1 ELSE 0 END) / COUNT(*), 1) AS recent_attendance_pct
    FROM attendance a, cutoff c
    WHERE a.class_date >= c.since
    GROUP BY a.student_id
),
test_seq AS (
    SELECT student_id, score_pct,
           ROW_NUMBER() OVER (PARTITION BY student_id ORDER BY test_date DESC) AS rn
    FROM v_student_test_scores
),
trend AS (
    SELECT student_id,
           AVG(CASE WHEN rn <= 4 THEN score_pct END) AS recent_score,
           AVG(CASE WHEN rn >  4 THEN score_pct END) AS earlier_score
    FROM test_seq
    GROUP BY student_id
)
SELECT s.student_id, s.student_name, s.batch_name,
       ra.recent_attendance_pct, s.hw_submission_pct,
       ROUND(tr.earlier_score, 1)                     AS earlier_score_pct,
       ROUND(tr.recent_score, 1)                      AS recent_score_pct,
       ROUND(tr.recent_score - tr.earlier_score, 1)   AS score_change,
       (CASE WHEN ra.recent_attendance_pct < 65 THEN 1 ELSE 0 END
      + CASE WHEN s.hw_submission_pct      < 50 THEN 1 ELSE 0 END
      + CASE WHEN tr.recent_score - tr.earlier_score <= -10 THEN 1 ELSE 0 END) AS risk_flags
FROM v_student_summary s
LEFT JOIN recent_att ra ON ra.student_id = s.student_id
LEFT JOIN trend tr      ON tr.student_id = s.student_id
WHERE s.status = 'Active'
  AND (ra.recent_attendance_pct < 65
       OR s.hw_submission_pct < 50
       OR tr.recent_score - tr.earlier_score <= -10)
ORDER BY risk_flags DESC, ra.recent_attendance_pct;

-- Q10: What did students who dropped out look like, compared with active students?
SELECT status,
       COUNT(*)                          AS students,
       ROUND(AVG(attendance_pct), 1)     AS avg_attendance_pct,
       ROUND(AVG(hw_submission_pct), 1)  AS avg_hw_submission_pct,
       ROUND(AVG(avg_score_pct), 1)      AS avg_score_pct,
       ROUND(AVG(tests_taken), 1)        AS avg_tests_taken
FROM v_student_summary
GROUP BY status;

-- Q11: Attendance trend in the 8 weeks before a student dropped out
WITH weeks_before AS (
    SELECT a.student_id,
           CAST((JULIANDAY(s.dropout_date) - JULIANDAY(a.class_date)) / 7 AS INTEGER) + 1 AS weeks_before_dropout,
           -- SQLite syntax. MySQL equivalent: FLOOR(DATEDIFF(s.dropout_date, a.class_date) / 7) + 1
           CASE WHEN a.status <> 'Absent' THEN 1 ELSE 0 END AS attended
    FROM attendance a
    JOIN students s ON s.student_id = a.student_id
    WHERE s.status = 'Dropped'
)
SELECT weeks_before_dropout,
       COUNT(DISTINCT student_id)          AS students,
       ROUND(100.0 * AVG(attended), 1)     AS attendance_pct
FROM weeks_before
WHERE weeks_before_dropout BETWEEN 1 AND 8
GROUP BY weeks_before_dropout
ORDER BY weeks_before_dropout DESC;

-- Q12: Partner-school view - how do students from each school perform?
SELECT sc.school_name, sc.city,
       COUNT(*)                          AS students,
       ROUND(AVG(v.attendance_pct), 1)   AS avg_attendance_pct,
       ROUND(AVG(v.avg_score_pct), 1)    AS avg_score_pct,
       RANK() OVER (ORDER BY AVG(v.avg_score_pct) DESC) AS score_rank
FROM v_student_summary v
JOIN schools sc ON sc.school_id = v.school_id
GROUP BY sc.school_name, sc.city
ORDER BY score_rank;

-- Q13: Did scores improve over the term? First 5 vs last 5 tests per batch
WITH seq AS (
    SELECT batch_id, test_date, AVG(score_pct) AS avg_score,
           ROW_NUMBER() OVER (PARTITION BY batch_id ORDER BY test_date)      AS n_first,
           ROW_NUMBER() OVER (PARTITION BY batch_id ORDER BY test_date DESC) AS n_last
    FROM v_student_test_scores
    GROUP BY batch_id, test_date
)
SELECT b.batch_name,
       ROUND(AVG(CASE WHEN n_first <= 5 THEN avg_score END), 1) AS first_5_tests_pct,
       ROUND(AVG(CASE WHEN n_last  <= 5 THEN avg_score END), 1) AS last_5_tests_pct,
       ROUND(AVG(CASE WHEN n_last  <= 5 THEN avg_score END)
           - AVG(CASE WHEN n_first <= 5 THEN avg_score END), 1) AS improvement_pts
FROM seq
JOIN batches b ON b.batch_id = seq.batch_id
GROUP BY b.batch_name
ORDER BY improvement_pts DESC;
