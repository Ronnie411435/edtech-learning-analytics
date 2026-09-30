-- =====================================================================
-- 03_views.sql  |  Reusable reporting views (MySQL 8.0+ / SQLite)
-- =====================================================================

-- ---------------------------------------------------------------------
-- v_student_test_scores : one row per student per test
-- ---------------------------------------------------------------------
DROP VIEW IF EXISTS v_student_test_scores;
CREATE VIEW v_student_test_scores AS
SELECT
    t.test_id,
    t.test_date,
    t.batch_id,
    t.subject,
    r.student_id,
    SUM(r.marks)                                         AS marks,
    t.max_marks,
    ROUND(100.0 * SUM(r.marks) / t.max_marks, 2)         AS score_pct,
    ROUND(100.0 * SUM(r.correct) / SUM(r.attempted), 2)  AS accuracy_pct,
    SUM(r.attempted)                                     AS attempted,
    SUM(r.correct)                                       AS correct
FROM tests t
JOIN test_results r ON r.test_id = t.test_id
GROUP BY t.test_id, t.test_date, t.batch_id, t.subject, r.student_id, t.max_marks;

-- ---------------------------------------------------------------------
-- v_student_summary : one row per student with the key engagement KPIs
-- ---------------------------------------------------------------------
DROP VIEW IF EXISTS v_student_summary;
CREATE VIEW v_student_summary AS
WITH att AS (
    SELECT student_id,
           COUNT(*)                                                   AS classes_held,
           SUM(CASE WHEN status IN ('Present', 'Late') THEN 1 ELSE 0 END) AS classes_attended
    FROM attendance
    GROUP BY student_id
),
hw_assigned AS (
    SELECT s.student_id, COUNT(*) AS hw_assigned
    FROM students s
    JOIN homework h
      ON h.batch_id = s.batch_id
     AND h.assigned_date >= s.join_date
     AND (s.dropout_date IS NULL OR h.assigned_date < s.dropout_date)
    GROUP BY s.student_id
),
hw_done AS (
    SELECT student_id, COUNT(*) AS hw_submitted, AVG(score) AS avg_hw_score
    FROM homework_submissions
    GROUP BY student_id
),
scores AS (
    SELECT student_id, COUNT(*) AS tests_taken,
           AVG(score_pct) AS avg_score_pct, AVG(accuracy_pct) AS avg_accuracy_pct
    FROM v_student_test_scores
    GROUP BY student_id
)
SELECT
    s.student_id, s.student_name, s.gender, s.batch_id, b.batch_name, b.program, b.grade, b.mode,
    s.school_id, s.join_date, s.status, s.dropout_date,
    COALESCE(att.classes_held, 0)                                          AS classes_held,
    ROUND(100.0 * att.classes_attended / att.classes_held, 1)              AS attendance_pct,
    COALESCE(ha.hw_assigned, 0)                                            AS hw_assigned,
    COALESCE(hd.hw_submitted, 0)                                           AS hw_submitted,
    ROUND(100.0 * COALESCE(hd.hw_submitted, 0) / ha.hw_assigned, 1)        AS hw_submission_pct,
    ROUND(hd.avg_hw_score, 2)                                              AS avg_hw_score,
    COALESCE(sc.tests_taken, 0)                                            AS tests_taken,
    ROUND(sc.avg_score_pct, 2)                                             AS avg_score_pct,
    ROUND(sc.avg_accuracy_pct, 2)                                          AS avg_accuracy_pct
FROM students s
JOIN batches b          ON b.batch_id = s.batch_id
LEFT JOIN att           ON att.student_id = s.student_id
LEFT JOIN hw_assigned ha ON ha.student_id = s.student_id
LEFT JOIN hw_done hd    ON hd.student_id = s.student_id
LEFT JOIN scores sc     ON sc.student_id = s.student_id;

-- ---------------------------------------------------------------------
-- v_topic_performance : accuracy by topic (weak-topic analysis)
-- ---------------------------------------------------------------------
DROP VIEW IF EXISTS v_topic_performance;
CREATE VIEW v_topic_performance AS
SELECT
    tp.topic_id, tp.subject, tp.topic_name, tp.difficulty,
    COUNT(DISTINCT r.student_id)                          AS students_tested,
    SUM(r.attempted)                                      AS questions_attempted,
    ROUND(100.0 * SUM(r.correct)   / SUM(r.attempted), 2) AS accuracy_pct,
    ROUND(100.0 * SUM(r.attempted) / SUM(r.questions), 2) AS attempt_rate_pct
FROM topics tp
JOIN test_results r ON r.topic_id = tp.topic_id
GROUP BY tp.topic_id, tp.subject, tp.topic_name, tp.difficulty;
