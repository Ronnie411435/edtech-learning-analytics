-- =====================================================================
-- EdTech Learning Analytics  |  01_schema.sql
-- Relational schema for a coaching-institute learning platform.
-- Written for MySQL 8.0+ (also runs on SQLite via scripts/build_database.py)
-- =====================================================================

-- CREATE DATABASE IF NOT EXISTS edtech_analytics;
-- USE edtech_analytics;

DROP TABLE IF EXISTS homework_submissions;
DROP TABLE IF EXISTS homework;
DROP TABLE IF EXISTS test_results;
DROP TABLE IF EXISTS tests;
DROP TABLE IF EXISTS attendance;
DROP TABLE IF EXISTS students;
DROP TABLE IF EXISTS topics;
DROP TABLE IF EXISTS batch_subject_teacher;
DROP TABLE IF EXISTS batches;
DROP TABLE IF EXISTS teachers;
DROP TABLE IF EXISTS schools;

CREATE TABLE schools (
    school_id     VARCHAR(10)  PRIMARY KEY,
    school_name   VARCHAR(100) NOT NULL,
    city          VARCHAR(50)  NOT NULL
);

CREATE TABLE teachers (
    teacher_id        VARCHAR(10)  PRIMARY KEY,
    teacher_name      VARCHAR(100) NOT NULL,
    subject           VARCHAR(30)  NOT NULL,
    experience_years  INT
);

CREATE TABLE batches (
    batch_id    VARCHAR(10) PRIMARY KEY,
    batch_name  VARCHAR(30) NOT NULL,
    program     VARCHAR(20) NOT NULL,          -- JEE / NEET / Foundation
    grade       INT         NOT NULL,
    mode        VARCHAR(10) NOT NULL           -- Online / Offline
);

CREATE TABLE batch_subject_teacher (
    batch_id    VARCHAR(10) NOT NULL,
    subject     VARCHAR(30) NOT NULL,
    teacher_id  VARCHAR(10) NOT NULL,
    PRIMARY KEY (batch_id, subject),
    FOREIGN KEY (batch_id)   REFERENCES batches(batch_id),
    FOREIGN KEY (teacher_id) REFERENCES teachers(teacher_id)
);

CREATE TABLE topics (
    topic_id    VARCHAR(10)  PRIMARY KEY,
    subject     VARCHAR(30)  NOT NULL,
    topic_name  VARCHAR(100) NOT NULL,
    difficulty  INT          NOT NULL          -- 1 = easy, 3 = hard
);

CREATE TABLE students (
    student_id    VARCHAR(10)  PRIMARY KEY,
    student_name  VARCHAR(100) NOT NULL,
    gender        VARCHAR(1),
    batch_id      VARCHAR(10)  NOT NULL,
    school_id     VARCHAR(10)  NOT NULL,
    join_date     DATE         NOT NULL,
    status        VARCHAR(10)  NOT NULL,       -- Active / Dropped
    dropout_date  DATE,
    FOREIGN KEY (batch_id)  REFERENCES batches(batch_id),
    FOREIGN KEY (school_id) REFERENCES schools(school_id)
);

CREATE TABLE attendance (
    student_id  VARCHAR(10) NOT NULL,
    class_date  DATE        NOT NULL,
    status      VARCHAR(10) NOT NULL,          -- Present / Late / Absent
    PRIMARY KEY (student_id, class_date),
    FOREIGN KEY (student_id) REFERENCES students(student_id)
);

CREATE TABLE tests (
    test_id          VARCHAR(10) PRIMARY KEY,
    batch_id         VARCHAR(10) NOT NULL,
    test_date        DATE        NOT NULL,
    subject          VARCHAR(30) NOT NULL,
    total_questions  INT         NOT NULL,
    max_marks        INT         NOT NULL,
    FOREIGN KEY (batch_id) REFERENCES batches(batch_id)
);

-- one row per student, per test, per topic (CBT: +4 correct, -1 wrong)
CREATE TABLE test_results (
    test_id         VARCHAR(10)  NOT NULL,
    student_id      VARCHAR(10)  NOT NULL,
    topic_id        VARCHAR(10)  NOT NULL,
    questions       INT          NOT NULL,
    attempted       INT          NOT NULL,
    correct         INT          NOT NULL,
    wrong           INT          NOT NULL,
    marks           INT          NOT NULL,
    time_spent_min  DECIMAL(5,1),
    PRIMARY KEY (test_id, student_id, topic_id),
    FOREIGN KEY (test_id)    REFERENCES tests(test_id),
    FOREIGN KEY (student_id) REFERENCES students(student_id),
    FOREIGN KEY (topic_id)   REFERENCES topics(topic_id)
);

CREATE TABLE homework (
    homework_id    VARCHAR(10) PRIMARY KEY,
    batch_id       VARCHAR(10) NOT NULL,
    subject        VARCHAR(30) NOT NULL,
    assigned_date  DATE        NOT NULL,
    due_date       DATE        NOT NULL,
    max_score      INT         NOT NULL,
    FOREIGN KEY (batch_id) REFERENCES batches(batch_id)
);

CREATE TABLE homework_submissions (
    homework_id     VARCHAR(10) NOT NULL,
    student_id      VARCHAR(10) NOT NULL,
    submitted_date  DATE        NOT NULL,
    score           INT         NOT NULL,
    PRIMARY KEY (homework_id, student_id),
    FOREIGN KEY (homework_id) REFERENCES homework(homework_id),
    FOREIGN KEY (student_id)  REFERENCES students(student_id)
);

-- Indexes for the most common filters / joins
CREATE INDEX idx_students_batch   ON students(batch_id);
CREATE INDEX idx_attendance_date  ON attendance(class_date);
CREATE INDEX idx_results_student  ON test_results(student_id);
CREATE INDEX idx_results_topic    ON test_results(topic_id);
CREATE INDEX idx_tests_batch_date ON tests(batch_id, test_date);
CREATE INDEX idx_hwsub_student    ON homework_submissions(student_id);
