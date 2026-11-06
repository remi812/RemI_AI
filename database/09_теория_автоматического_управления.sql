-- Учебное наполнение ТАУ; предварительное содержание для проверки преподавателем.
-- Выполнять после файлов 01 и 03. Повторный запуск не добавляет дубликаты.
BEGIN;

INSERT INTO remi_project.topics (discipline_id, name)
SELECT d.discipline_id, v.name
FROM remi_project.disciplines d
CROSS JOIN (VALUES ('Сигналы и элементы системы'), ('Структурные схемы'), ('Переходные процессы и устойчивость')) AS v(name)
WHERE d.name = 'Теория автоматического управления'
ON CONFLICT (discipline_id, name) DO NOTHING;

INSERT INTO remi_project.competencies (topic_id, name, description)
SELECT t.topic_id, v.name, v.description
FROM (VALUES
 ('Сигналы и элементы системы', 'Определять объект управления', 'Находить объект, на который действует управление.'),
 ('Сигналы и элементы системы', 'Различать задание и выход', 'Различать требуемое и измеренное значение.'),
 ('Сигналы и элементы системы', 'Вычислять ошибку управления', 'Вычислять разность задания и измеренного выхода.'),
 ('Сигналы и элементы системы', 'Определять роль датчика', 'Понимать, что датчик измеряет величину.'),
 ('Обратная связь', 'Различать разомкнутую и замкнутую системы', 'Определять наличие обратной связи.'),
 ('Обратная связь', 'Понимать отрицательную обратную связь', 'Распознавать вычитание измеренного выхода из задания.'),
 ('Структурные схемы', 'Определять передаточную функцию последовательных звеньев', 'Перемножать функции последовательных звеньев.'),
 ('Переходные процессы и устойчивость', 'Понимать переходный процесс', 'Распознавать изменение выхода после изменения входа.'),
 ('Переходные процессы и устойчивость', 'Оценивать устойчивость простого звена', 'Оценивать затухание решения уравнения первого порядка.'),
 ('Переходные процессы и устойчивость', 'Определять постоянную времени звена', 'Находить постоянную времени звена вида K/(Ts+1).')
) AS v(topic, name, description)
JOIN remi_project.topics t ON t.name = v.topic
JOIN remi_project.disciplines d ON d.discipline_id = t.discipline_id AND d.name = 'Теория автоматического управления'
ON CONFLICT (topic_id, name) DO NOTHING;

-- Предварительный граф: приоритизация и полнота требуют экспертизы.
INSERT INTO remi_project.prerequisites (competency_id, prerequisite_id)
SELECT child.competency_id, parent.competency_id
FROM (VALUES
 ('Определять объект управления', 'Распознавать систему управления'),
 ('Различать задание и выход', 'Определять объект управления'),
 ('Вычислять ошибку управления', 'Различать задание и выход'),
 ('Определять роль датчика', 'Определять объект управления'),
 ('Различать разомкнутую и замкнутую системы', 'Объяснять обратную связь'),
 ('Понимать отрицательную обратную связь', 'Вычислять ошибку управления'),
 ('Понимать отрицательную обратную связь', 'Различать разомкнутую и замкнутую системы'),
 ('Определять передаточную функцию последовательных звеньев', 'Читать передаточную функцию'),
 ('Понимать переходный процесс', 'Распознавать систему управления'),
 ('Оценивать устойчивость простого звена', 'Понимать переходный процесс'),
 ('Определять постоянную времени звена', 'Читать передаточную функцию')
) AS v(child_name, parent_name)
JOIN remi_project.competencies child ON child.name = v.child_name
JOIN remi_project.topics ct ON ct.topic_id = child.topic_id
JOIN remi_project.disciplines cd ON cd.discipline_id = ct.discipline_id AND cd.name = 'Теория автоматического управления'
JOIN remi_project.competencies parent ON parent.name = v.parent_name
JOIN remi_project.topics pt ON pt.topic_id = parent.topic_id
JOIN remi_project.disciplines pd ON pd.discipline_id = pt.discipline_id AND pd.name = 'Теория автоматического управления'
ON CONFLICT DO NOTHING;

INSERT INTO remi_project.questions (competency_id, question_text, answer_type, expected_answer, explanation, validation_status, difficulty, source, numeric_tolerance)
SELECT c.competency_id, v.question_text, v.answer_type, v.expected_answer, v.explanation, 'pending', 1, 'manual', v.tolerance
FROM (VALUES
 ('Определять объект управления', 'В системе поддержания температуры что является объектом управления?', 'choice', 'Помещение', 'Температура помещения является регулируемой величиной.', NULL::numeric),
 ('Различать задание и выход', 'Как называют требуемое значение температуры, которое пользователь задаёт системе?', 'choice', 'Задание', 'Задание задаёт желаемое значение регулируемой величины.', NULL::numeric),
 ('Вычислять ошибку управления', 'Задание r = 10, измеренный выход y = 8. Найдите ошибку e = r − y.', 'numeric', '2', 'Разность составляет 10 − 8 = 2.', 0::numeric),
 ('Определять роль датчика', 'Что делает датчик температуры в системе отопления?', 'choice', 'Измеряет температуру', 'Датчик предоставляет измеренное значение температуры.', NULL::numeric),
 ('Различать разомкнутую и замкнутую системы', 'Какая система использует измерение выхода для формирования управления?', 'choice', 'Замкнутая', 'В замкнутой системе выход передаётся в контур обратной связи.', NULL::numeric),
 ('Понимать отрицательную обратную связь', 'Как формируется ошибка при единичной отрицательной обратной связи?', 'choice', 'Задание минус измеренный выход', 'При принятом обозначении e = r − y.', NULL::numeric),
 ('Определять передаточную функцию последовательных звеньев', 'Два звена с передаточными функциями 2 и 3 соединены последовательно. Чему равна общая передаточная функция?', 'numeric', '6', 'Для последовательного соединения передаточные функции перемножаются: 2 × 3 = 6.', 0::numeric),
 ('Понимать переходный процесс', 'Как называется изменение выхода системы после изменения входного воздействия?', 'choice', 'Переходный процесс', 'Переходный процесс описывает изменение состояния или выхода во времени после воздействия.', NULL::numeric),
 ('Оценивать устойчивость простого звена', 'Решение уравнения x′ = −2x при любом конечном начальном x стремится к какому числу при росте времени?', 'numeric', '0', 'x(t) = x(0) e^(−2t), поэтому решение стремится к нулю.', 0::numeric),
 ('Определять постоянную времени звена', 'Чему равна постоянная времени T звена W(s) = 4/(3s+1)?', 'numeric', '3', 'В форме K/(Ts+1) коэффициент при s равен T.', 0::numeric)
) AS v(competency, question_text, answer_type, expected_answer, explanation, tolerance)
JOIN remi_project.competencies c ON c.name = v.competency
JOIN remi_project.topics t ON t.topic_id = c.topic_id
JOIN remi_project.disciplines d ON d.discipline_id = t.discipline_id AND d.name = 'Теория автоматического управления'
WHERE NOT EXISTS (SELECT 1 FROM remi_project.questions q WHERE q.competency_id = c.competency_id AND q.question_text = v.question_text);

INSERT INTO remi_project.question_options (question_id, option_text)
SELECT q.question_id, v.option_text
FROM (VALUES
 ('В системе поддержания температуры что является объектом управления?', 'Помещение'),
 ('В системе поддержания температуры что является объектом управления?', 'Учебник'),
 ('Как называют требуемое значение температуры, которое пользователь задаёт системе?', 'Задание'),
 ('Как называют требуемое значение температуры, которое пользователь задаёт системе?', 'Измеренный выход'),
 ('Что делает датчик температуры в системе отопления?', 'Измеряет температуру'),
 ('Что делает датчик температуры в системе отопления?', 'Вычисляет интеграл'),
 ('Какая система использует измерение выхода для формирования управления?', 'Замкнутая'),
 ('Какая система использует измерение выхода для формирования управления?', 'Разомкнутая без обратной связи'),
 ('Как формируется ошибка при единичной отрицательной обратной связи?', 'Задание минус измеренный выход'),
 ('Как формируется ошибка при единичной отрицательной обратной связи?', 'Задание плюс измеренный выход'),
 ('Как называется изменение выхода системы после изменения входного воздействия?', 'Переходный процесс'),
 ('Как называется изменение выхода системы после изменения входного воздействия?', 'Пароль пользователя')
) AS v(question_text, option_text)
JOIN remi_project.questions q ON q.question_text = v.question_text
ON CONFLICT (question_id, option_text) DO NOTHING;

INSERT INTO remi_project.question_versions (question_id, version_number, competency_id, answer_type, question_text, expected_answer, explanation, evaluation_rules, numeric_tolerance, options_snapshot)
SELECT q.question_id, 1, q.competency_id, q.answer_type, q.question_text, q.expected_answer, q.explanation, q.evaluation_rules, q.numeric_tolerance,
       (SELECT jsonb_agg(o.option_text ORDER BY o.option_id) FROM remi_project.question_options o WHERE o.question_id = q.question_id)
FROM remi_project.questions q
JOIN remi_project.competencies c ON c.competency_id = q.competency_id
JOIN remi_project.topics t ON t.topic_id = c.topic_id
JOIN remi_project.disciplines d ON d.discipline_id = t.discipline_id AND d.name = 'Теория автоматического управления'
WHERE NOT EXISTS (SELECT 1 FROM remi_project.question_versions v WHERE v.question_id = q.question_id);

-- Ссылки проверены как существующие страницы; запись и качество требуют проверки.
INSERT INTO remi_project.learning_resources (title, resource_type, url, description, provider, language, access_type, review_status, link_checked_at)
SELECT v.title, v.resource_type, v.url, v.description, v.provider, 'русский', v.access_type, 'pending', CURRENT_TIMESTAMP
FROM (VALUES
 ('Основы теории автоматического управления', 'курс', 'https://stepik.org/course/115666/promo', 'Страница курса на Stepik; фактические условия и возможность записи нужно проверить.', 'Stepik', 'уточнить'),
 ('Основы создания математических моделей в SimInTech', 'курс', 'https://stepik.org/course/89909/promo', 'Курс моделирования с использованием SimInTech; на странице указано, что обучение бесплатное и можно начать сразу.', 'Stepik', 'уточнить'),
 ('Теория автоматического управления: конспект лекций', 'конспект', 'https://www.texnic.ru/tools/lekcii/tau_kl/tau0.htm', 'Введение, обратная связь, передаточные функции и устойчивость; содержание требует проверки экспертом.', 'Texnic.ru', 'открытая страница')
) AS v(title, resource_type, url, description, provider, access_type)
WHERE NOT EXISTS (SELECT 1 FROM remi_project.learning_resources r WHERE r.url = v.url);

INSERT INTO remi_project.competency_resources (competency_id, resource_id)
SELECT c.competency_id, r.resource_id
FROM (VALUES
 ('Распознавать систему управления', 'https://www.texnic.ru/tools/lekcii/tau_kl/tau0.htm'),
 ('Распознавать систему управления', 'https://stepik.org/course/115666/promo'),
 ('Объяснять обратную связь', 'https://www.texnic.ru/tools/lekcii/tau_kl/tau0.htm'),
 ('Читать передаточную функцию', 'https://www.texnic.ru/tools/lekcii/tau_kl/tau0.htm'),
 ('Понимать переходный процесс', 'https://www.texnic.ru/tools/lekcii/tau_kl/tau0.htm'),
 ('Оценивать устойчивость простого звена', 'https://www.texnic.ru/tools/lekcii/tau_kl/tau0.htm')
) AS v(competency, url)
JOIN remi_project.competencies c ON c.name = v.competency
JOIN remi_project.topics t ON t.topic_id = c.topic_id
JOIN remi_project.disciplines d ON d.discipline_id = t.discipline_id AND d.name = 'Теория автоматического управления'
JOIN remi_project.learning_resources r ON r.url = v.url
ON CONFLICT (competency_id, resource_id) DO NOTHING;

COMMIT;
