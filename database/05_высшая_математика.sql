-- Учебное наполнение высшей математики. Связи и вопросы ожидают проверки экспертом.
-- Повторный запуск не добавляет те же записи повторно.
BEGIN;

INSERT INTO remi_project.topics (discipline_id, name)
SELECT d.discipline_id, v.name
FROM remi_project.disciplines d
CROSS JOIN (VALUES ('Алгебра'), ('Пределы'), ('Применение производных')) AS v(name)
WHERE d.name = 'Высшая математика'
ON CONFLICT (discipline_id, name) DO NOTHING;

INSERT INTO remi_project.competencies (topic_id, name, description)
SELECT t.topic_id, v.name, v.description
FROM (VALUES
    ('Алгебра', 'Решать линейное уравнение', 'Находить неизвестное в простом линейном уравнении.'),
    ('Алгебра', 'Выполнять действия с дробями', 'Складывать простые обыкновенные дроби.'),
    ('Функции', 'Находить область определения функции', 'Определять допустимые значения аргумента.'),
    ('Пределы', 'Вычислять предел подстановкой', 'Находить предел непрерывной функции прямой подстановкой.'),
    ('Пределы', 'Понимать смысл предела', 'Понимать значение, к которому стремится функция.'),
    ('Производные', 'Вычислять производную многочлена', 'Применять правило степени и суммы.'),
    ('Применение производных', 'Определять скорость изменения', 'Находить скорость изменения по производной.'),
    ('Интегралы', 'Находить первообразную', 'Находить первообразную простой степенной функции.'),
    ('Интегралы', 'Вычислять определённый интеграл', 'Применять формулу Ньютона — Лейбница к простому примеру.')
) AS v(topic, name, description)
JOIN remi_project.topics t ON t.name = v.topic
JOIN remi_project.disciplines d ON d.discipline_id = t.discipline_id AND d.name = 'Высшая математика'
ON CONFLICT (topic_id, name) DO NOTHING;

-- Предложенные учебные зависимости; предметную корректность проверяет преподаватель.
INSERT INTO remi_project.prerequisites (competency_id, prerequisite_id)
SELECT child.competency_id, parent.competency_id
FROM (VALUES
    ('Вычислять значение функции', 'Решать линейное уравнение'),
    ('Находить область определения функции', 'Вычислять значение функции'),
    ('Понимать смысл предела', 'Вычислять значение функции'),
    ('Вычислять предел подстановкой', 'Понимать смысл предела'),
    ('Находить производную', 'Вычислять предел подстановкой'),
    ('Вычислять производную многочлена', 'Находить производную'),
    ('Определять скорость изменения', 'Вычислять производную многочлена'),
    ('Находить первообразную', 'Вычислять производную многочлена'),
    ('Вычислять определённый интеграл', 'Находить первообразную'),
    ('Вычислять определённый интеграл', 'Выполнять действия с дробями')
) AS v(child_name, parent_name)
JOIN remi_project.competencies child ON child.name = v.child_name
JOIN remi_project.topics ct ON ct.topic_id = child.topic_id
JOIN remi_project.disciplines cd ON cd.discipline_id = ct.discipline_id AND cd.name = 'Высшая математика'
JOIN remi_project.competencies parent ON parent.name = v.parent_name
JOIN remi_project.topics pt ON pt.topic_id = parent.topic_id
JOIN remi_project.disciplines pd ON pd.discipline_id = pt.discipline_id AND pd.name = 'Высшая математика'
ON CONFLICT DO NOTHING;

INSERT INTO remi_project.questions (competency_id, question_text, answer_type, expected_answer, explanation, validation_status, difficulty, source, evaluation_rules, numeric_tolerance)
SELECT c.competency_id, v.question_text, v.answer_type, v.expected_answer, v.explanation, 'pending', 1, 'manual', v.evaluation_rules, v.numeric_tolerance
FROM (VALUES
    ('Решать линейное уравнение', 'Решите уравнение 2x + 3 = 11. Чему равен x?', 'numeric', '4', '2x = 8, поэтому x = 4.', NULL, 0::numeric),
    ('Выполнять действия с дробями', 'Чему равна сумма 1/2 + 1/4? Укажите ответ десятичной дробью.', 'numeric', '0.75', '1/2 = 2/4, поэтому сумма равна 3/4.', NULL, 0::numeric),
    ('Находить область определения функции', 'Какое значение x недопустимо для функции f(x) = 1/(x − 2)?', 'numeric', '2', 'Знаменатель не может быть равен нулю.', NULL, 0::numeric),
    ('Понимать смысл предела', 'К чему стремится f(x) = x + 1, когда x стремится к 2?', 'choice', '3', 'При значениях x около 2 функция близка к 3.', NULL, NULL),
    ('Вычислять предел подстановкой', 'Найдите предел функции f(x) = 2x + 1 при x, стремящемся к 3.', 'numeric', '7', 'Для линейной функции можно подставить x = 3.', NULL, 0::numeric),
    ('Вычислять производную многочлена', 'Чему равна производная f(x) = 3x² + 2x в точке x = 1?', 'numeric', '8', 'f′(x) = 6x + 2, поэтому f′(1) = 8.', NULL, 0::numeric),
    ('Определять скорость изменения', 'Положение задано формулой s(t) = t². Чему равна скорость при t = 2?', 'numeric', '4', 'Скорость v(t) = s′(t) = 2t, поэтому v(2) = 4.', NULL, 0::numeric),
    ('Находить первообразную', 'Какая функция является первообразной для f(x) = 2x?', 'choice', 'x²', 'Производная x² равна 2x.', NULL, NULL),
    ('Вычислять определённый интеграл', 'Вычислите интеграл ∫ от 0 до 2 функции 2x dx.', 'numeric', '4', 'Первообразная x²; значение на границах равно 4 − 0.', NULL, 0::numeric)
) AS v(competency, question_text, answer_type, expected_answer, explanation, evaluation_rules, numeric_tolerance)
JOIN remi_project.competencies c ON c.name = v.competency
JOIN remi_project.topics t ON t.topic_id = c.topic_id
JOIN remi_project.disciplines d ON d.discipline_id = t.discipline_id AND d.name = 'Высшая математика'
WHERE NOT EXISTS (SELECT 1 FROM remi_project.questions q WHERE q.competency_id = c.competency_id AND q.question_text = v.question_text);

INSERT INTO remi_project.question_options (question_id, option_text)
SELECT q.question_id, v.option_text
FROM (VALUES
    ('К чему стремится f(x) = x + 1, когда x стремится к 2?', '2'),
    ('К чему стремится f(x) = x + 1, когда x стремится к 2?', '3'),
    ('К чему стремится f(x) = x + 1, когда x стремится к 2?', '4'),
    ('Какая функция является первообразной для f(x) = 2x?', 'x²'),
    ('Какая функция является первообразной для f(x) = 2x?', '2'),
    ('Какая функция является первообразной для f(x) = 2x?', 'x³')
) AS v(question_text, option_text)
JOIN remi_project.questions q ON q.question_text = v.question_text
ON CONFLICT (question_id, option_text) DO NOTHING;

-- Сохраняем первый снимок только для новых вопросов после добавления вариантов.
INSERT INTO remi_project.question_versions (question_id, version_number, competency_id, answer_type, question_text, expected_answer, explanation, evaluation_rules, numeric_tolerance, options_snapshot)
SELECT q.question_id, 1, q.competency_id, q.answer_type, q.question_text, q.expected_answer, q.explanation, q.evaluation_rules, q.numeric_tolerance,
       (SELECT jsonb_agg(o.option_text ORDER BY o.option_id) FROM remi_project.question_options o WHERE o.question_id = q.question_id)
FROM remi_project.questions q
JOIN remi_project.competencies c ON c.competency_id = q.competency_id
JOIN remi_project.topics t ON t.topic_id = c.topic_id
JOIN remi_project.disciplines d ON d.discipline_id = t.discipline_id AND d.name = 'Высшая математика'
WHERE NOT EXISTS (SELECT 1 FROM remi_project.question_versions v WHERE v.question_id = q.question_id);

-- Ссылки проверены как существующие источники, но предметная модерация ещё не пройдена.
INSERT INTO remi_project.learning_resources (title, resource_type, url, description, provider, language, access_type, review_status, link_checked_at)
SELECT v.title, v.resource_type, v.url, v.description, v.provider, 'английский', 'открытый', 'pending', CURRENT_TIMESTAMP
FROM (VALUES
    ('OpenStax: Functions and Graphs', 'учебник', 'https://openstax.org/books/calculus-volume-1/pages/1-introduction', 'Функции и их свойства.', 'OpenStax'),
    ('OpenStax: The Derivative as a Function', 'учебник', 'https://openstax.org/books/calculus-volume-1/pages/3-2-the-derivative-as-a-function', 'Понятие производной.', 'OpenStax'),
    ('OpenStax: Differentiation Rules', 'учебник', 'https://openstax.org/books/calculus-volume-1/pages/3-3-differentiation-rules', 'Правила дифференцирования.', 'OpenStax'),
    ('OpenStax: Antiderivatives', 'учебник', 'https://openstax.org/books/calculus-volume-1/pages/4-10-antiderivatives', 'Первообразные.', 'OpenStax'),
    ('MIT OpenCourseWare: Single Variable Calculus', 'курс', 'https://ocw.mit.edu/courses/18-01sc-single-variable-calculus-fall-2010/', 'Курс по дифференцированию и интегрированию.', 'MIT OpenCourseWare')
) AS v(title, resource_type, url, description, provider)
WHERE NOT EXISTS (SELECT 1 FROM remi_project.learning_resources r WHERE r.url = v.url);

INSERT INTO remi_project.competency_resources (competency_id, resource_id)
SELECT c.competency_id, r.resource_id
FROM (VALUES
    ('Вычислять значение функции', 'https://openstax.org/books/calculus-volume-1/pages/1-introduction'),
    ('Находить область определения функции', 'https://openstax.org/books/calculus-volume-1/pages/1-introduction'),
    ('Находить производную', 'https://openstax.org/books/calculus-volume-1/pages/3-2-the-derivative-as-a-function'),
    ('Вычислять производную многочлена', 'https://openstax.org/books/calculus-volume-1/pages/3-3-differentiation-rules'),
    ('Находить первообразную', 'https://openstax.org/books/calculus-volume-1/pages/4-10-antiderivatives'),
    ('Вычислять определённый интеграл', 'https://ocw.mit.edu/courses/18-01sc-single-variable-calculus-fall-2010/')
) AS v(competency, url)
JOIN remi_project.competencies c ON c.name = v.competency
JOIN remi_project.topics t ON t.topic_id = c.topic_id
JOIN remi_project.disciplines d ON d.discipline_id = t.discipline_id AND d.name = 'Высшая математика'
JOIN remi_project.learning_resources r ON r.url = v.url
ON CONFLICT (competency_id, resource_id) DO NOTHING;

COMMIT;
