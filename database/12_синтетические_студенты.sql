-- 150 вымышленных пользователей и учебные действия для запросов и демонстраций.
-- Это не данные реального сайта и не результаты проверенной диагностики.
-- Создаёт отдельный реестр участников набора, чтобы их можно было однозначно отличить.
-- Запускать после 01, 03, 05, 08 и 09 в RemI_AI. Повторный запуск не дублирует записи.
BEGIN;

CREATE TABLE IF NOT EXISTS remi_project.synthetic_students (
    student_id INTEGER PRIMARY KEY REFERENCES remi_project.students(student_id),
    dataset_name VARCHAR(50) NOT NULL,
    student_number INTEGER NOT NULL CHECK (student_number > 0),
    UNIQUE (dataset_name, student_number)
);

-- Не присваивать существующие аккаунты набору, если их адреса заняты вне реестра.
DO $preflight$
BEGIN
    IF EXISTS (
        SELECT 1 FROM generate_series(1, 150) n
        JOIN remi_project.students s ON s.email = 'remi-demo-' || lpad(n::text, 3, '0') || '@example.invalid'
        LEFT JOIN remi_project.synthetic_students ss ON ss.student_id = s.student_id
            AND ss.dataset_name = 'demo-150-v1' AND ss.student_number = n
        WHERE ss.student_id IS NULL
    ) THEN
        RAISE EXCEPTION 'Один из учебных адресов уже занят вне набора demo-150-v1';
    END IF;
    IF (SELECT count(*) FROM remi_project.competencies c JOIN remi_project.topics t USING(topic_id)
        JOIN remi_project.disciplines d USING(discipline_id)
        WHERE (d.name, c.name) IN (
          ('Высшая математика', 'Вычислять значение функции'),
          ('Основы программирования', 'Использовать условие'),
          ('Теория автоматического управления', 'Объяснять обратную связь')
        )) <> 3 THEN
        RAISE EXCEPTION 'Отсутствует одна из целевых компетенций для набора';
    END IF;
END;
$preflight$;

WITH inserted AS (
    INSERT INTO remi_project.students (display_name, email)
    SELECT 'Демо-студент ' || lpad(n::text, 3, '0'),
           'remi-demo-' || lpad(n::text, 3, '0') || '@example.invalid'
    FROM generate_series(1, 150) n
    WHERE NOT EXISTS (SELECT 1 FROM remi_project.synthetic_students ss WHERE ss.dataset_name = 'demo-150-v1' AND ss.student_number = n)
    RETURNING student_id, email
)
INSERT INTO remi_project.synthetic_students (student_id, dataset_name, student_number)
SELECT student_id, 'demo-150-v1', substring(email FROM 'remi-demo-([0-9]{3})@')::integer FROM inserted;

-- У трёх групп разные цели: функция, условие Python или обратная связь.
INSERT INTO remi_project.diagnostic_sessions (student_id, target_competency_id, started_at, finished_at, status, stop_reason)
SELECT ss.student_id, c.competency_id,
       TIMESTAMP '2026-02-01 09:00' + ss.student_number * INTERVAL '1 hour',
       TIMESTAMP '2026-02-01 09:05' + ss.student_number * INTERVAL '1 hour',
       'completed', 'Синтетический набор demo-150-v1; результаты смоделированы.'
FROM remi_project.synthetic_students ss
JOIN remi_project.competencies c ON c.name = CASE ss.student_number % 3
    WHEN 1 THEN 'Вычислять значение функции'
    WHEN 2 THEN 'Использовать условие'
    ELSE 'Объяснять обратную связь' END
JOIN remi_project.topics t ON t.topic_id = c.topic_id
JOIN remi_project.disciplines d ON d.discipline_id = t.discipline_id AND d.name = CASE ss.student_number % 3
    WHEN 1 THEN 'Высшая математика'
    WHEN 2 THEN 'Основы программирования'
    ELSE 'Теория автоматического управления' END
WHERE ss.dataset_name = 'demo-150-v1'
AND NOT EXISTS (SELECT 1 FROM remi_project.diagnostic_sessions ds WHERE ds.student_id = ss.student_id AND ds.stop_reason = 'Синтетический набор demo-150-v1; результаты смоделированы.');

-- Три разных вопроса выбранной дисциплины; правильность здесь искусственно задана.
INSERT INTO remi_project.student_answers (session_id, question_id, question_version_id, answer_text, is_correct, grading_method, grading_details, answered_at)
SELECT ds.session_id, q.question_id, q.question_version_id,
       CASE WHEN (ss.student_number + q.question_id) % 4 <> 0 THEN q.expected_answer
            WHEN q.answer_type = 'numeric' THEN (q.expected_answer::numeric + 1)::text
            WHEN q.answer_type = 'choice' THEN COALESCE(q.wrong_option, 'Учебный неправильный ответ')
            ELSE 'Учебный неправильный ответ' END,
       (ss.student_number + q.question_id) % 4 <> 0,
       'ungraded', 'Синтетический ответ; задание и оценка не подтверждены.',
       ds.started_at + INTERVAL '1 minute' * q.question_order
FROM remi_project.synthetic_students ss
JOIN remi_project.diagnostic_sessions ds ON ds.student_id = ss.student_id AND ds.stop_reason = 'Синтетический набор demo-150-v1; результаты смоделированы.'
JOIN remi_project.competencies target ON target.competency_id = ds.target_competency_id
JOIN remi_project.topics target_topic ON target_topic.topic_id = target.topic_id
JOIN LATERAL (
    SELECT q0.question_id, q0.answer_type, q0.expected_answer, v.question_version_id,
           (SELECT min(o.option_text) FROM remi_project.question_options o WHERE o.question_id = q0.question_id AND o.option_text <> q0.expected_answer) AS wrong_option,
           row_number() OVER (ORDER BY (q0.competency_id = target.competency_id) DESC, q0.question_id) AS question_order
    FROM remi_project.questions q0
    JOIN remi_project.competencies c0 ON c0.competency_id = q0.competency_id
    JOIN remi_project.topics t0 ON t0.topic_id = c0.topic_id AND t0.discipline_id = target_topic.discipline_id
    JOIN remi_project.question_versions v ON v.question_id = q0.question_id AND v.version_number = 1
    ORDER BY (q0.competency_id = target.competency_id) DESC, q0.question_id
    LIMIT 3
) q ON TRUE
WHERE ss.dataset_name = 'demo-150-v1'
AND NOT EXISTS (SELECT 1 FROM remi_project.student_answers a WHERE a.session_id = ds.session_id AND a.question_id = q.question_id);

INSERT INTO remi_project.mastery_estimates (student_id, competency_id, session_id, knowledge_status, explanation, algorithm_version, estimated_at)
SELECT ss.student_id, ds.target_competency_id, ds.session_id, 'needs_review',
       'Синтетический пример; реального вывода о знаниях нет.', 'synthetic-demo-150-v1', ds.finished_at
FROM remi_project.synthetic_students ss
JOIN remi_project.diagnostic_sessions ds ON ds.student_id = ss.student_id AND ds.stop_reason = 'Синтетический набор demo-150-v1; результаты смоделированы.'
WHERE ss.dataset_name = 'demo-150-v1'
AND NOT EXISTS (SELECT 1 FROM remi_project.mastery_estimates e WHERE e.session_id = ds.session_id AND e.algorithm_version = 'synthetic-demo-150-v1');

INSERT INTO remi_project.estimate_evidence (estimate_id, answer_id)
SELECT e.estimate_id, a.answer_id
FROM remi_project.mastery_estimates e
JOIN remi_project.student_answers a ON a.session_id = e.session_id
JOIN remi_project.questions q ON q.question_id = a.question_id AND q.competency_id = e.competency_id
WHERE e.algorithm_version = 'synthetic-demo-150-v1'
ON CONFLICT DO NOTHING;

INSERT INTO remi_project.learning_routes (student_id, session_id, target_competency_id, status, explanation, algorithm_version, created_at)
SELECT ss.student_id, ds.session_id, ds.target_competency_id, 'active',
       'Учебный маршрут из одной предпосылки и цели; создан по шаблону, не диагностическим алгоритмом.',
       'synthetic-demo-150-v1', ds.finished_at
FROM remi_project.synthetic_students ss
JOIN remi_project.diagnostic_sessions ds ON ds.student_id = ss.student_id AND ds.stop_reason = 'Синтетический набор demo-150-v1; результаты смоделированы.'
WHERE ss.dataset_name = 'demo-150-v1'
AND NOT EXISTS (SELECT 1 FROM remi_project.learning_routes lr WHERE lr.session_id = ds.session_id AND lr.algorithm_version = 'synthetic-demo-150-v1');

INSERT INTO remi_project.route_steps (route_id, position, competency_id, estimate_id, status, explanation)
SELECT lr.route_id, 1, p.prerequisite_id, NULL, 'planned', 'Учебный пример предварительной компетенции; она не оценивалась.'
FROM remi_project.learning_routes lr
JOIN LATERAL (SELECT prerequisite_id FROM remi_project.prerequisites WHERE competency_id = lr.target_competency_id ORDER BY prerequisite_id LIMIT 1) p ON TRUE
WHERE lr.algorithm_version = 'synthetic-demo-150-v1'
ON CONFLICT (route_id, position) DO NOTHING;

INSERT INTO remi_project.route_steps (route_id, position, competency_id, estimate_id, status, explanation)
SELECT lr.route_id, 2, lr.target_competency_id, e.estimate_id, 'planned', 'Учебная цель; реальная диагностика не проводилась.'
FROM remi_project.learning_routes lr
JOIN remi_project.mastery_estimates e ON e.session_id = lr.session_id AND e.competency_id = lr.target_competency_id AND e.algorithm_version = 'synthetic-demo-150-v1'
WHERE lr.algorithm_version = 'synthetic-demo-150-v1'
ON CONFLICT (route_id, position) DO NOTHING;

-- Проверяем полноту набора до COMMIT: при ошибке вся транзакция отменяется.
DO $verify$
DECLARE n_students INTEGER; n_sessions INTEGER; n_answers INTEGER; n_routes INTEGER; n_steps INTEGER; n_evidence INTEGER;
BEGIN
    SELECT count(*) INTO n_students FROM remi_project.synthetic_students WHERE dataset_name = 'demo-150-v1';
    SELECT count(*) INTO n_sessions FROM remi_project.diagnostic_sessions WHERE stop_reason = 'Синтетический набор demo-150-v1; результаты смоделированы.';
    SELECT count(*) INTO n_answers FROM remi_project.student_answers a JOIN remi_project.diagnostic_sessions ds USING(session_id) WHERE ds.stop_reason = 'Синтетический набор demo-150-v1; результаты смоделированы.';
    SELECT count(*) INTO n_routes FROM remi_project.learning_routes WHERE algorithm_version = 'synthetic-demo-150-v1';
    SELECT count(*) INTO n_steps FROM remi_project.route_steps rs JOIN remi_project.learning_routes lr USING(route_id) WHERE lr.algorithm_version = 'synthetic-demo-150-v1';
    SELECT count(*) INTO n_evidence FROM remi_project.estimate_evidence ev JOIN remi_project.mastery_estimates e USING(estimate_id) WHERE e.algorithm_version = 'synthetic-demo-150-v1';
    IF n_students <> 150 OR n_sessions <> 150 OR n_answers <> 450 OR n_routes <> 150 OR n_steps <> 300 OR n_evidence < 150 THEN
        RAISE EXCEPTION 'Неполный синтетический набор: студенты %, сессии %, ответы %, маршруты %, шаги %, свидетельства %', n_students, n_sessions, n_answers, n_routes, n_steps, n_evidence;
    END IF;
END;
$verify$;

COMMIT;
