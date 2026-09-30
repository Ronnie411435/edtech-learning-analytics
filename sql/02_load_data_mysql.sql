-- =====================================================================
-- 02_load_data_mysql.sql  |  Load the CLEANED CSVs into MySQL
-- Run from the repo root:  mysql --local-infile=1 -u root -p edtech_analytics < sql/02_load_data_mysql.sql
-- (SET GLOBAL local_infile = 1; may be required once.)
-- Loads data/clean/*.csv produced by the notebook / scripts/build_database.py
-- =====================================================================
LOAD DATA LOCAL INFILE 'data/clean/schools.csv'   INTO TABLE schools   FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' IGNORE 1 LINES;
LOAD DATA LOCAL INFILE 'data/clean/teachers.csv'  INTO TABLE teachers  FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' IGNORE 1 LINES;
LOAD DATA LOCAL INFILE 'data/clean/batches.csv'   INTO TABLE batches   FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' IGNORE 1 LINES;
LOAD DATA LOCAL INFILE 'data/clean/batch_subject_teacher.csv' INTO TABLE batch_subject_teacher FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' IGNORE 1 LINES;
LOAD DATA LOCAL INFILE 'data/clean/topics.csv'    INTO TABLE topics    FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' IGNORE 1 LINES;

LOAD DATA LOCAL INFILE 'data/clean/students.csv'  INTO TABLE students  FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' IGNORE 1 LINES
  (student_id, student_name, gender, batch_id, school_id, join_date, status, @dropout)
  SET dropout_date = NULLIF(@dropout, '');

LOAD DATA LOCAL INFILE 'data/clean/attendance.csv' INTO TABLE attendance FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' IGNORE 1 LINES;
LOAD DATA LOCAL INFILE 'data/clean/tests.csv'      INTO TABLE tests      FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' IGNORE 1 LINES;

LOAD DATA LOCAL INFILE 'data/clean/test_results.csv' INTO TABLE test_results FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' IGNORE 1 LINES
  (test_id, student_id, topic_id, questions, attempted, correct, wrong, marks, @tsm)
  SET time_spent_min = NULLIF(@tsm, '');

LOAD DATA LOCAL INFILE 'data/clean/homework.csv'             INTO TABLE homework             FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' IGNORE 1 LINES;
LOAD DATA LOCAL INFILE 'data/clean/homework_submissions.csv' INTO TABLE homework_submissions FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' IGNORE 1 LINES;
