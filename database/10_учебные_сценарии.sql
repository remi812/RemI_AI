-- Два вымышленных сценария: оценки и маршруты составлены вручную.
-- Вопросы ожидают проверки и не предназначены для реальной диагностики.
-- Выполнять после файлов 01, 03, 05 и 09. Повторный запуск не дублирует данные.
BEGIN;

INSERT INTO remi_project.students (display_name, email)
VALUES ('Учебный сценарий А', 'scenario.a@example.invalid'),
       ('Учебный сценарий Б', 'scenario.b@example.invalid')
ON CONFLICT (email) DO NOTHING;

INSERT INTO remi_project.questions (competency_id, question_text, answer_type, expected_answer, explanation, validation_status, difficulty, source, numeric_tolerance)
SELECT c.competency_id, v.question_text, v.answer_type, v.expected_answer, v.explanation, 'pending', 1, 'manual', v.tolerance
FROM (VALUES
 ('Высшая математика', 'Вычислять значение функции', 'Для функции f(x) = 2x + 1 найдите f(3).', 'numeric', '7', '2 × 3 + 1 = 7.', 0::numeric),
 ('Теория автоматического управления', 'Объяснять обратную связь', 'В системе отопления куда передаётся измеренная датчиком температура для сравнения с заданием?', 'choice', 'В регулятор', 'Регулятор использует измеренное значение для сравнения с заданием.', NULL::numeric),
 ('Теория автоматического управления', 'Объяснять обратную связь', 'Для чего в замкнутой системе используется информация об измеренном выходе?', 'choice', 'Для сравнения с заданием', 'Измеренный выход позволяет учитывать отклонение от заданного значения.', NULL::numeric)
) AS v(discipline, competency, question_text, answer_type, expected_answer, explanation, tolerance)
JOIN remi_project.competencies c ON c.name = v.competency
JOIN remi_project.topics t ON t.topic_id = c.topic_id
JOIN remi_project.disciplines d ON d.discipline_id = t.discipline_id AND d.name = v.discipline
WHERE NOT EXISTS (SELECT 1 FROM remi_project.questions q WHERE q.competency_id = c.competency_id AND q.question_text = v.question_text);

INSERT INTO remi_project.question_options (question_id, option_text)
SELECT q.question_id, v.option_text
FROM (VALUES
 ('В системе отопления куда передаётся измеренная датчиком температура для сравнения с заданием?', 'В регулятор'),
 ('В системе отопления куда передаётся измеренная датчиком температура для сравнения с заданием?', 'Непосредственно в нагреватель без сравнения'),
 ('Для чего в замкнутой системе используется информация об измеренном выходе?', 'Для сравнения с заданием'),
 ('Для чего в замкнутой системе используется информация об измеренном выходе?', 'Только для хранения без влияния на управление')
) AS v(question_text, option_text)
JOIN remi_project.questions q ON q.question_text = v.question_text
ON CONFLICT (question_id, option_text) DO NOTHING;

INSERT INTO remi_project.question_versions (question_id, version_number, competency_id, answer_type, question_text, expected_answer, explanation, numeric_tolerance, options_snapshot)
SELECT q.question_id, 1, q.competency_id, q.answer_type, q.question_text, q.expected_answer, q.explanation, q.numeric_tolerance,
       (SELECT jsonb_agg(o.option_text ORDER BY o.option_id) FROM remi_project.question_options o WHERE o.question_id = q.question_id)
FROM remi_project.questions q
WHERE q.question_text IN (
 'Для функции f(x) = 2x + 1 найдите f(3).',
 'В системе отопления куда передаётся измеренная датчиком температура для сравнения с заданием?',
 'Для чего в замкнутой системе используется информация об измеренном выходе?'
)
AND NOT EXISTS (SELECT 1 FROM remi_project.question_versions v WHERE v.question_id = q.question_id);

INSERT INTO remi_project.diagnostic_sessions (student_id, target_competency_id, started_at, finished_at, status, stop_reason)
SELECT s.student_id, c.competency_id, TIMESTAMP '2026-02-01 10:00', TIMESTAMP '2026-02-01 10:05', 'completed', 'Учебный сценарий; результаты смоделированы вручную.'
FROM remi_project.students s
JOIN remi_project.competencies c ON c.name = 'Объяснять обратную связь'
JOIN remi_project.topics t ON t.topic_id = c.topic_id
JOIN remi_project.disciplines d ON d.discipline_id = t.discipline_id AND d.name = 'Теория автоматического управления'
WHERE s.email IN ('scenario.a@example.invalid', 'scenario.b@example.invalid')
AND NOT EXISTS (SELECT 1 FROM remi_project.diagnostic_sessions ds WHERE ds.student_id = s.student_id AND ds.stop_reason = 'Учебный сценарий; результаты смоделированы вручную.');

INSERT INTO remi_project.student_answers (session_id, question_id, question_version_id, answer_text, is_correct, grading_method, grading_details, answered_at)
SELECT ds.session_id, q.question_id, v.question_version_id, x.answer_text, FALSE, 'ungraded', 'Вымышленный пример; не является реальной оценкой.', TIMESTAMP '2026-02-01 10:02'
FROM (VALUES
 ('scenario.a@example.invalid', 'Чему равно f(2), если f(x) = 3x + 1?', '6'),
 ('scenario.a@example.invalid', 'Для функции f(x) = 2x + 1 найдите f(3).', '8'),
 ('scenario.b@example.invalid', 'В системе отопления куда передаётся измеренная датчиком температура для сравнения с заданием?', 'Непосредственно в нагреватель без сравнения'),
 ('scenario.b@example.invalid', 'Для чего в замкнутой системе используется информация об измеренном выходе?', 'Только для хранения без влияния на управление')
) AS x(email, question_text, answer_text)
JOIN remi_project.students s ON s.email = x.email
JOIN remi_project.diagnostic_sessions ds ON ds.student_id = s.student_id AND ds.stop_reason = 'Учебный сценарий; результаты смоделированы вручную.'
JOIN remi_project.questions q ON q.question_text = x.question_text
JOIN remi_project.question_versions v ON v.question_id = q.question_id AND v.version_number = 1
WHERE NOT EXISTS (SELECT 1 FROM remi_project.student_answers a WHERE a.session_id = ds.session_id AND a.question_id = q.question_id);

-- Без выдуманных числовых оценок и без вывода о подтверждённом пробеле.
INSERT INTO remi_project.mastery_estimates (student_id, competency_id, session_id, knowledge_status, explanation, algorithm_version)
SELECT s.student_id, c.competency_id, ds.session_id, 'needs_review', 'Учебный пример: ответы указывают на тему для уточнения; реальная диагностика не проводилась.', 'manual-demo-10'
FROM (VALUES
 ('scenario.a@example.invalid', 'Высшая математика', 'Вычислять значение функции'),
 ('scenario.b@example.invalid', 'Теория автоматического управления', 'Объяснять обратную связь')
) AS x(email, discipline, competency)
JOIN remi_project.students s ON s.email = x.email
JOIN remi_project.diagnostic_sessions ds ON ds.student_id = s.student_id AND ds.stop_reason = 'Учебный сценарий; результаты смоделированы вручную.'
JOIN remi_project.competencies c ON c.name = x.competency
JOIN remi_project.topics t ON t.topic_id = c.topic_id
JOIN remi_project.disciplines d ON d.discipline_id = t.discipline_id AND d.name = x.discipline
WHERE NOT EXISTS (SELECT 1 FROM remi_project.mastery_estimates e WHERE e.session_id = ds.session_id AND e.competency_id = c.competency_id AND e.algorithm_version = 'manual-demo-10');

INSERT INTO remi_project.estimate_evidence (estimate_id, answer_id)
SELECT e.estimate_id, a.answer_id
FROM remi_project.mastery_estimates e
JOIN remi_project.student_answers a ON a.session_id = e.session_id
JOIN remi_project.questions q ON q.question_id = a.question_id AND q.competency_id = e.competency_id
WHERE e.algorithm_version = 'manual-demo-10'
ON CONFLICT DO NOTHING;

INSERT INTO remi_project.learning_routes (student_id, session_id, target_competency_id, explanation, algorithm_version)
SELECT s.student_id, ds.session_id, ds.target_competency_id, 'Учебный маршрут составлен вручную для демонстрации, а не алгоритмом.', 'manual-demo-10'
FROM remi_project.students s
JOIN remi_project.diagnostic_sessions ds ON ds.student_id = s.student_id AND ds.stop_reason = 'Учебный сценарий; результаты смоделированы вручную.'
WHERE s.email IN ('scenario.a@example.invalid', 'scenario.b@example.invalid')
AND NOT EXISTS (SELECT 1 FROM remi_project.learning_routes lr WHERE lr.session_id = ds.session_id AND lr.algorithm_version = 'manual-demo-10');

INSERT INTO remi_project.route_steps (route_id, position, competency_id, estimate_id, status, explanation)
SELECT lr.route_id, x.position, c.competency_id, e.estimate_id, 'planned', x.explanation
FROM (VALUES
 ('scenario.a@example.invalid', 1, 'Высшая математика', 'Вычислять значение функции', 'Повторить подстановку аргумента в функцию.'),
 ('scenario.a@example.invalid', 2, 'Моделирование систем', 'Распознавать математическую модель', 'Рассмотреть, как формулы описывают систему.'),
 ('scenario.a@example.invalid', 3, 'Теория автоматического управления', 'Распознавать систему управления', 'Изучить назначение системы управления.'),
 ('scenario.a@example.invalid', 4, 'Теория автоматического управления', 'Объяснять обратную связь', 'Разобрать передачу измеренного выхода в систему управления.'),
 ('scenario.b@example.invalid', 1, 'Теория автоматического управления', 'Распознавать систему управления', 'Повторить основные элементы системы управления.'),
 ('scenario.b@example.invalid', 2, 'Теория автоматического управления', 'Объяснять обратную связь', 'Разобрать назначение обратной связи.')
) AS x(email, position, discipline, competency, explanation)
JOIN remi_project.students s ON s.email = x.email
JOIN remi_project.learning_routes lr ON lr.student_id = s.student_id AND lr.algorithm_version = 'manual-demo-10'
JOIN remi_project.competencies c ON c.name = x.competency
JOIN remi_project.topics t ON t.topic_id = c.topic_id
JOIN remi_project.disciplines d ON d.discipline_id = t.discipline_id AND d.name = x.discipline
LEFT JOIN remi_project.mastery_estimates e ON e.student_id = s.student_id AND e.competency_id = c.competency_id AND e.session_id = lr.session_id AND e.algorithm_version = 'manual-demo-10'
ON CONFLICT (route_id, position) DO NOTHING;

-- Ссылки помечены pending и показаны только как демонстрация структуры.
INSERT INTO remi_project.route_step_resources (route_step_id, resource_id, reason)
SELECT rs.route_step_id, r.resource_id, 'Учебный пример; материал ещё требует проверки преподавателем.'
FROM (VALUES
 ('scenario.a@example.invalid', 1, 'https://openedu.ru/course/urfu/CALC/?session=fall_2026'),
 ('scenario.a@example.invalid', 4, 'https://www.texnic.ru/tools/lekcii/tau_kl/tau0.htm'),
 ('scenario.b@example.invalid', 1, 'https://www.texnic.ru/tools/lekcii/tau_kl/tau0.htm'),
 ('scenario.b@example.invalid', 2, 'https://www.texnic.ru/tools/lekcii/tau_kl/tau0.htm')
) AS x(email, position, url)
JOIN remi_project.students s ON s.email = x.email
JOIN remi_project.learning_routes lr ON lr.student_id = s.student_id AND lr.algorithm_version = 'manual-demo-10'
JOIN remi_project.route_steps rs ON rs.route_id = lr.route_id AND rs.position = x.position
JOIN remi_project.learning_resources r ON r.url = x.url
ON CONFLICT DO NOTHING;

COMMIT;
