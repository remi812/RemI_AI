-- Учебное наполнение Python. Выполнить после 01 и 03 в базе RemI_AI.
-- Проверка идёт в одной транзакции; повторный запуск не дублирует записи.
BEGIN;

INSERT INTO remi_project.topics (discipline_id, name)
SELECT d.discipline_id, v.name
FROM remi_project.disciplines d
CROSS JOIN (VALUES ('Типы данных'), ('Функции Python'), ('Списки Python')) AS v(name)
WHERE d.name = 'Основы программирования'
ON CONFLICT (discipline_id, name) DO NOTHING;

INSERT INTO remi_project.competencies (topic_id, name, description)
SELECT t.topic_id, v.name, v.description
FROM (VALUES
 ('Типы данных', 'Различать типы данных Python', 'Различать целое число, дробное число, строку и логическое значение.'),
 ('Типы данных', 'Преобразовывать типы Python', 'Преобразовывать строку с целым числом в int.'),
 ('Условия', 'Вычислять логическое условие Python', 'Определять результат простого сравнения.'),
 ('Циклы', 'Определять число повторений цикла', 'Определять число повторений for с range.'),
 ('Функции Python', 'Вызывать функцию Python', 'Определять результат вызова простой функции.'),
 ('Функции Python', 'Понимать return', 'Понимать возврат результата из функции.'),
 ('Списки Python', 'Получать элемент списка', 'Использовать индексы списка, начиная с нуля.'),
 ('Списки Python', 'Определять длину списка', 'Использовать len для списка.'),
 ('Списки Python', 'Добавлять элемент в список', 'Использовать append для добавления элемента.')
) AS v(topic, name, description)
JOIN remi_project.topics t ON t.name = v.topic
JOIN remi_project.disciplines d ON d.discipline_id = t.discipline_id AND d.name = 'Основы программирования'
ON CONFLICT (topic_id, name) DO NOTHING;

-- Связи предварительных знаний являются учебной гипотезой.
INSERT INTO remi_project.prerequisites (competency_id, prerequisite_id)
SELECT child.competency_id, parent.competency_id
FROM (VALUES
 ('Различать типы данных Python', 'Использовать переменные'),
 ('Преобразовывать типы Python', 'Различать типы данных Python'),
 ('Вычислять логическое условие Python', 'Различать типы данных Python'),
 ('Использовать условие', 'Вычислять логическое условие Python'),
 ('Определять число повторений цикла', 'Понимать цикл'),
 ('Вызывать функцию Python', 'Использовать переменные'),
 ('Понимать return', 'Вызывать функцию Python'),
 ('Получать элемент списка', 'Различать типы данных Python'),
 ('Определять длину списка', 'Получать элемент списка'),
 ('Добавлять элемент в список', 'Получать элемент списка')
) AS v(child_name, parent_name)
JOIN remi_project.competencies child ON child.name = v.child_name
JOIN remi_project.topics ct ON ct.topic_id = child.topic_id
JOIN remi_project.disciplines cd ON cd.discipline_id = ct.discipline_id AND cd.name = 'Основы программирования'
JOIN remi_project.competencies parent ON parent.name = v.parent_name
JOIN remi_project.topics pt ON pt.topic_id = parent.topic_id
JOIN remi_project.disciplines pd ON pd.discipline_id = pt.discipline_id AND pd.name = 'Основы программирования'
ON CONFLICT DO NOTHING;

INSERT INTO remi_project.questions (competency_id, question_text, answer_type, expected_answer, explanation, validation_status, difficulty, source, evaluation_rules, numeric_tolerance)
SELECT c.competency_id, v.question_text, v.answer_type, v.expected_answer, v.explanation, 'pending', 1, 'manual', NULL, v.tolerance
FROM (VALUES
 ('Различать типы данных Python', 'Какой тип данных у значения 3.5 в Python?', 'choice', 'float', 'Число с десятичной точкой имеет тип float.', NULL::numeric),
 ('Преобразовывать типы Python', 'Какое число получится после int("12")?', 'numeric', '12', 'int преобразует строку с целым числом в целое число.', 0::numeric),
 ('Вычислять логическое условие Python', 'Каков результат выражения 5 > 3 в Python?', 'choice', 'True', 'Пять больше трёх, поэтому результат True.', NULL::numeric),
 ('Определять число повторений цикла', 'Сколько раз выполнится тело цикла for i in range(3)?', 'numeric', '3', 'range(3) содержит 0, 1 и 2.', 0::numeric),
 ('Вызывать функцию Python', 'Чему равно значение len("кот")?', 'numeric', '3', 'В строке «кот» три символа.', 0::numeric),
 ('Понимать return', 'Что возвращает функция, определённая как def f(): return 7, при вызове f()?', 'numeric', '7', 'Оператор return возвращает значение 7.', 0::numeric),
 ('Получать элемент списка', 'Чему равно значение [10, 20, 30][1] в Python?', 'numeric', '20', 'Индекс 1 обозначает второй элемент списка.', 0::numeric),
 ('Определять длину списка', 'Чему равно значение len([4, 5, 6])?', 'numeric', '3', 'В списке три элемента.', 0::numeric),
 ('Добавлять элемент в список', 'После a = [1, 2]; a.append(3) сколько элементов в списке a?', 'numeric', '3', 'append добавляет один элемент; список содержит 1, 2 и 3.', 0::numeric)
) AS v(competency, question_text, answer_type, expected_answer, explanation, tolerance)
JOIN remi_project.competencies c ON c.name = v.competency
JOIN remi_project.topics t ON t.topic_id = c.topic_id
JOIN remi_project.disciplines d ON d.discipline_id = t.discipline_id AND d.name = 'Основы программирования'
WHERE NOT EXISTS (SELECT 1 FROM remi_project.questions q WHERE q.competency_id = c.competency_id AND q.question_text = v.question_text);

INSERT INTO remi_project.question_options (question_id, option_text)
SELECT q.question_id, v.option_text
FROM (VALUES
 ('Какой тип данных у значения 3.5 в Python?', 'int'),
 ('Какой тип данных у значения 3.5 в Python?', 'float'),
 ('Какой тип данных у значения 3.5 в Python?', 'str'),
 ('Каков результат выражения 5 > 3 в Python?', 'True'),
 ('Каков результат выражения 5 > 3 в Python?', 'False')
) AS v(question_text, option_text)
JOIN remi_project.questions q ON q.question_text = v.question_text
ON CONFLICT (question_id, option_text) DO NOTHING;

INSERT INTO remi_project.question_versions (question_id, version_number, competency_id, answer_type, question_text, expected_answer, explanation, evaluation_rules, numeric_tolerance, options_snapshot)
SELECT q.question_id, 1, q.competency_id, q.answer_type, q.question_text, q.expected_answer, q.explanation, q.evaluation_rules, q.numeric_tolerance,
       (SELECT jsonb_agg(o.option_text ORDER BY o.option_id) FROM remi_project.question_options o WHERE o.question_id = q.question_id)
FROM remi_project.questions q
JOIN remi_project.competencies c ON c.competency_id = q.competency_id
JOIN remi_project.topics t ON t.topic_id = c.topic_id
JOIN remi_project.disciplines d ON d.discipline_id = t.discipline_id AND d.name = 'Основы программирования'
WHERE NOT EXISTS (SELECT 1 FROM remi_project.question_versions v WHERE v.question_id = q.question_id);

-- На странице курса указаны бесплатное обучение и возможность начать сразу;
-- фактическое зачисление и экспертная модерация не проверены.
INSERT INTO remi_project.learning_resources (title, resource_type, url, description, provider, language, access_type, review_status, link_checked_at)
SELECT v.title, 'курс', v.url, v.description, 'Stepik', 'русский', 'уточнить', 'pending', CURRENT_TIMESTAMP
FROM (VALUES
 ('Поколение Python: курс для начинающих', 'https://stepik.org/course/58852/promo', 'Типы данных, условия и циклы. На странице указано: бесплатно, учиться можно сразу.'),
 ('Программирование Python для начинающих', 'https://stepik.org/course/212681/promo', 'Типы данных, условия, циклы, списки и функции. На странице указано: бесплатно, учиться можно сразу.'),
 ('Python для начинающих', 'https://stepik.org/course/237923/promo', 'Типы данных, условия, циклы, списки и функции. На странице указано: бесплатно, учиться можно сразу.')
) AS v(title, url, description)
WHERE NOT EXISTS (SELECT 1 FROM remi_project.learning_resources r WHERE r.url = v.url);

INSERT INTO remi_project.competency_resources (competency_id, resource_id)
SELECT c.competency_id, r.resource_id
FROM (VALUES
 ('Использовать переменные', 'https://stepik.org/course/58852/promo'),
 ('Различать типы данных Python', 'https://stepik.org/course/58852/promo'),
 ('Использовать условие', 'https://stepik.org/course/58852/promo'),
 ('Понимать цикл', 'https://stepik.org/course/58852/promo'),
 ('Преобразовывать типы Python', 'https://stepik.org/course/212681/promo'),
 ('Вызывать функцию Python', 'https://stepik.org/course/212681/promo'),
 ('Понимать return', 'https://stepik.org/course/212681/promo'),
 ('Получать элемент списка', 'https://stepik.org/course/237923/promo'),
 ('Определять длину списка', 'https://stepik.org/course/237923/promo'),
 ('Добавлять элемент в список', 'https://stepik.org/course/237923/promo')
) AS v(competency, url)
JOIN remi_project.competencies c ON c.name = v.competency
JOIN remi_project.topics t ON t.topic_id = c.topic_id
JOIN remi_project.disciplines d ON d.discipline_id = t.discipline_id AND d.name = 'Основы программирования'
JOIN remi_project.learning_resources r ON r.url = v.url
ON CONFLICT (competency_id, resource_id) DO NOTHING;

COMMIT;
