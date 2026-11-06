-- Домашнее задание 13. Выполнить в базе RemI_AI (проверить фактическое имя).
-- Четыре независимых учебных варианта, а не единая производственная схема.
BEGIN;

-- 1. Single Table Inheritance: одна таблица для двух типов.
CREATE SCHEMA hw13_sti;
CREATE TABLE hw13_sti.question (
    question_id BIGSERIAL PRIMARY KEY,
    prompt TEXT NOT NULL,
    answer_type VARCHAR(20) NOT NULL CHECK (answer_type IN ('numeric', 'short_text')),
    expected_number NUMERIC,
    tolerance NUMERIC,
    evaluation_rubric TEXT,
    CHECK (
        (answer_type = 'numeric'
            AND expected_number IS NOT NULL
            AND tolerance IS NOT NULL AND tolerance >= 0
            AND evaluation_rubric IS NULL)
        OR
        (answer_type = 'short_text'
            AND evaluation_rubric IS NOT NULL
            AND expected_number IS NULL AND tolerance IS NULL)
    )
);

-- 2. Class Table Inheritance: общая таблица и две таблицы подтипов.
-- В задании название Common Table Inheritance; используем модель лекции.
CREATE SCHEMA hw13_class;
CREATE TABLE hw13_class.question (
    question_id BIGSERIAL PRIMARY KEY,
    prompt TEXT NOT NULL
);
CREATE TABLE hw13_class.numeric_question (
    question_id BIGINT PRIMARY KEY REFERENCES hw13_class.question(question_id),
    expected_number NUMERIC NOT NULL,
    tolerance NUMERIC NOT NULL CHECK (tolerance >= 0)
);
CREATE TABLE hw13_class.short_text_question (
    question_id BIGINT PRIMARY KEY REFERENCES hw13_class.question(question_id),
    evaluation_rubric TEXT NOT NULL
);
-- Приложение должно создавать ровно один подтип для каждой родительской записи.
-- Только PK/FK не запрещают одновременное наличие двух подтипов или их отсутствие.

-- 3. Concrete Table Inheritance: две самостоятельные таблицы.
CREATE SCHEMA hw13_concrete;
CREATE TABLE hw13_concrete.numeric_question (
    question_id BIGSERIAL PRIMARY KEY,
    prompt TEXT NOT NULL,
    expected_number NUMERIC NOT NULL,
    tolerance NUMERIC NOT NULL CHECK (tolerance >= 0)
);
CREATE TABLE hw13_concrete.short_text_question (
    question_id BIGSERIAL PRIMARY KEY,
    prompt TEXT NOT NULL,
    evaluation_rubric TEXT NOT NULL
);
-- Идентификаторы уникальны внутри каждой таблицы, но могут совпадать между типами.

-- 4. Entity Attribute Value: постоянные поля и расширяемые характеристики.
CREATE SCHEMA hw13_eav;
CREATE TABLE hw13_eav.question (
    question_id BIGSERIAL PRIMARY KEY,
    prompt TEXT NOT NULL,
    answer_type VARCHAR(20) NOT NULL CHECK (answer_type IN ('numeric', 'short_text'))
);
CREATE TABLE hw13_eav.attribute (
    attribute_name VARCHAR(50) PRIMARY KEY,
    description TEXT NOT NULL
);
CREATE TABLE hw13_eav.question_value (
    question_id BIGINT NOT NULL REFERENCES hw13_eav.question(question_id),
    attribute_name VARCHAR(50) NOT NULL REFERENCES hw13_eav.attribute(attribute_name),
    attribute_value TEXT NOT NULL,
    PRIMARY KEY (question_id, attribute_name)
);
-- Для numeric: атрибуты expected_number и tolerance; для short_text: evaluation_rubric.
-- Их определения и значения добавляются записями в attribute и question_value.
-- Проверку допустимых атрибутов, обязательности и числовых типов выполняет приложение.
COMMIT;
