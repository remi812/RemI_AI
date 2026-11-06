-- Домашнее задание 14. RemI AI: аналитика ответов.
-- Один факт = один отправленный ответ на одно задание.
BEGIN;

CREATE SCHEMA hw14_star;
CREATE TABLE hw14_star.dim_date (
    date_key INTEGER PRIMARY KEY,
    calendar_date DATE NOT NULL UNIQUE,
    day_number SMALLINT NOT NULL CHECK (day_number BETWEEN 1 AND 31),
    month_number SMALLINT NOT NULL CHECK (month_number BETWEEN 1 AND 12),
    quarter_number SMALLINT NOT NULL CHECK (quarter_number BETWEEN 1 AND 4),
    year_number SMALLINT NOT NULL
);
CREATE TABLE hw14_star.dim_student (
    student_key BIGSERIAL PRIMARY KEY,
    source_student_token TEXT NOT NULL UNIQUE
);
CREATE TABLE hw14_star.dim_question (
    question_key BIGSERIAL PRIMARY KEY,
    source_question_id TEXT NOT NULL,
    version_number INTEGER NOT NULL CHECK (version_number > 0),
    question_text TEXT NOT NULL,
    question_type_code VARCHAR(20) NOT NULL CHECK (question_type_code IN ('choice', 'numeric', 'short_text')),
    question_type_name TEXT NOT NULL,
    UNIQUE (source_question_id, version_number)
);
CREATE TABLE hw14_star.dim_competency (
    competency_key BIGSERIAL PRIMARY KEY,
    source_competency_id TEXT NOT NULL UNIQUE,
    competency_name TEXT NOT NULL,
    source_discipline_id TEXT NOT NULL,
    discipline_name TEXT NOT NULL
);
CREATE TABLE hw14_star.fact_answer (
    answer_key BIGSERIAL PRIMARY KEY,
    source_answer_id TEXT NOT NULL UNIQUE,
    date_key INTEGER NOT NULL REFERENCES hw14_star.dim_date(date_key),
    student_key BIGINT NOT NULL REFERENCES hw14_star.dim_student(student_key),
    question_key BIGINT NOT NULL REFERENCES hw14_star.dim_question(question_key),
    competency_key BIGINT NOT NULL REFERENCES hw14_star.dim_competency(competency_key),
    answer_count SMALLINT NOT NULL DEFAULT 1 CHECK (answer_count = 1),
    normalized_score NUMERIC(6,5) CHECK (normalized_score BETWEEN 0 AND 1)
);

CREATE SCHEMA hw14_snow;
CREATE TABLE hw14_snow.dim_question_type (
    question_type_key BIGSERIAL PRIMARY KEY,
    type_code VARCHAR(20) NOT NULL UNIQUE
        CHECK (type_code IN ('choice', 'numeric', 'short_text')),
    type_name TEXT NOT NULL
);
CREATE TABLE hw14_snow.dim_discipline (
    discipline_key BIGSERIAL PRIMARY KEY,
    source_discipline_id TEXT NOT NULL UNIQUE,
    discipline_name TEXT NOT NULL
);
CREATE TABLE hw14_snow.dim_date (
    date_key INTEGER PRIMARY KEY,
    calendar_date DATE NOT NULL UNIQUE,
    day_number SMALLINT NOT NULL CHECK (day_number BETWEEN 1 AND 31),
    month_number SMALLINT NOT NULL CHECK (month_number BETWEEN 1 AND 12),
    quarter_number SMALLINT NOT NULL CHECK (quarter_number BETWEEN 1 AND 4),
    year_number SMALLINT NOT NULL
);
CREATE TABLE hw14_snow.dim_student (
    student_key BIGSERIAL PRIMARY KEY,
    source_student_token TEXT NOT NULL UNIQUE
);
CREATE TABLE hw14_snow.dim_question (
    question_key BIGSERIAL PRIMARY KEY,
    source_question_id TEXT NOT NULL,
    version_number INTEGER NOT NULL CHECK (version_number > 0),
    question_text TEXT NOT NULL,
    question_type_key BIGINT NOT NULL REFERENCES hw14_snow.dim_question_type(question_type_key),
    UNIQUE (source_question_id, version_number)
);
CREATE TABLE hw14_snow.dim_competency (
    competency_key BIGSERIAL PRIMARY KEY,
    source_competency_id TEXT NOT NULL UNIQUE,
    competency_name TEXT NOT NULL,
    discipline_key BIGINT NOT NULL REFERENCES hw14_snow.dim_discipline(discipline_key)
);
CREATE TABLE hw14_snow.fact_answer (
    answer_key BIGSERIAL PRIMARY KEY,
    source_answer_id TEXT NOT NULL UNIQUE,
    date_key INTEGER NOT NULL REFERENCES hw14_snow.dim_date(date_key),
    student_key BIGINT NOT NULL REFERENCES hw14_snow.dim_student(student_key),
    question_key BIGINT NOT NULL REFERENCES hw14_snow.dim_question(question_key),
    competency_key BIGINT NOT NULL REFERENCES hw14_snow.dim_competency(competency_key),
    answer_count SMALLINT NOT NULL DEFAULT 1 CHECK (answer_count = 1),
    normalized_score NUMERIC(6,5) CHECK (normalized_score BETWEEN 0 AND 1)
);

COMMIT;
