-- =====================================================================
-- 05_stored_procedures_mysql.sql  |  MySQL 8.0+ only
-- Parameterised reports that faculty / admins can run on demand.
-- (SQLite has no stored procedures; the Python notebook runs the same
--  logic with parameterised queries.)
-- =====================================================================

DELIMITER //

-- ---------------------------------------------------------------------
-- 1) Ranked result sheet for one test
--    CALL sp_test_leaderboard('CBT0001');
-- ---------------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_test_leaderboard //
CREATE PROCEDURE sp_test_leaderboard(IN p_test_id VARCHAR(10))
BEGIN
    SELECT sc.test_id, sc.test_date, b.batch_name, sc.subject,
           s.student_id, s.student_name, sc.marks, sc.max_marks, sc.score_pct, sc.accuracy_pct,
           DENSE_RANK()   OVER (ORDER BY sc.marks DESC)          AS test_rank,
           ROUND(100 * PERCENT_RANK() OVER (ORDER BY sc.marks), 1) AS percentile
    FROM v_student_test_scores sc
    JOIN students s ON s.student_id = sc.student_id
    JOIN batches  b ON b.batch_id  = sc.batch_id
    WHERE sc.test_id = p_test_id
    ORDER BY test_rank, s.student_name;
END //

-- ---------------------------------------------------------------------
-- 2) Full report card for one student: KPIs + topic-wise strengths/weaknesses
--    CALL sp_student_report('S0001');
-- ---------------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_student_report //
CREATE PROCEDURE sp_student_report(IN p_student_id VARCHAR(10))
BEGIN
    -- result set 1: summary KPIs
    SELECT * FROM v_student_summary WHERE student_id = p_student_id;

    -- result set 2: topic-wise accuracy vs the batch average
    SELECT tp.subject, tp.topic_name,
           ROUND(100 * SUM(r.correct) / SUM(r.attempted), 1) AS student_accuracy_pct,
           ba.batch_accuracy_pct,
           ROUND(100 * SUM(r.correct) / SUM(r.attempted) - ba.batch_accuracy_pct, 1) AS gap_vs_batch
    FROM test_results r
    JOIN topics tp ON tp.topic_id = r.topic_id
    JOIN (
        SELECT r2.topic_id, ROUND(100 * SUM(r2.correct) / SUM(r2.attempted), 1) AS batch_accuracy_pct
        FROM test_results r2
        JOIN students s2 ON s2.student_id = r2.student_id
        WHERE s2.batch_id = (SELECT batch_id FROM students WHERE student_id = p_student_id)
        GROUP BY r2.topic_id
    ) ba ON ba.topic_id = r.topic_id
    WHERE r.student_id = p_student_id
    GROUP BY tp.subject, tp.topic_name, ba.batch_accuracy_pct
    ORDER BY gap_vs_batch;
END //

-- ---------------------------------------------------------------------
-- 3) Weekly early-warning list with adjustable thresholds
--    CALL sp_at_risk_students(65, 50);   -- attendance %, homework %
-- ---------------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_at_risk_students //
CREATE PROCEDURE sp_at_risk_students(IN p_min_attendance DECIMAL(5,1),
                                     IN p_min_homework   DECIMAL(5,1))
BEGIN
    DECLARE v_since DATE;

    SELECT MIN(test_date) INTO v_since
    FROM (SELECT DISTINCT test_date FROM tests ORDER BY test_date DESC LIMIT 4) d;

    SELECT s.student_id, s.student_name, s.batch_name, s.program,
           ra.recent_attendance_pct, s.hw_submission_pct, s.avg_score_pct
    FROM v_student_summary s
    JOIN (
        SELECT student_id,
               ROUND(100 * SUM(status <> 'Absent') / COUNT(*), 1) AS recent_attendance_pct
        FROM attendance
        WHERE class_date >= v_since
        GROUP BY student_id
    ) ra ON ra.student_id = s.student_id
    WHERE s.status = 'Active'
      AND (ra.recent_attendance_pct < p_min_attendance OR s.hw_submission_pct < p_min_homework)
    ORDER BY ra.recent_attendance_pct;
END //

DELIMITER ;
