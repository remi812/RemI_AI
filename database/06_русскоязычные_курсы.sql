-- Русскоязычные источники по математике. Применяется после 05_высшая_математика.sql.
-- Ссылки проверены; доступность записи, стоимость и качество требуют перепроверки.
BEGIN;

INSERT INTO remi_project.learning_resources (title, resource_type, url, description, provider, language, access_type, review_status, link_checked_at)
SELECT v.title, 'курс', v.url, v.description, v.provider, 'русский', 'уточнить', 'pending', CURRENT_TIMESTAMP
FROM (VALUES
  ('Высшая математика: математический анализ с нуля', 'https://stepik.org/course/229762/promo', 'Начальный курс: пределы, производные, интегралы.', 'Stepik'),
  ('Математический анализ (часть 1)', 'https://stepik.org/course/716/promo', 'Последовательности, пределы и непрерывность.', 'Stepik'),
  ('Математический анализ: интегрирование и функции многих переменных', 'https://openedu.ru/course/msu/MATHAN/', 'Курс МГУ: неопределённый и определённый интегралы, функции многих переменных.', 'Открытое образование / МГУ'),
  ('Математический анализ', 'https://openedu.ru/course/urfu/CALC/?session=fall_2026', 'Курс УрФУ: функции, пределы, производные и интегралы.', 'Открытое образование / УрФУ')
) AS v(title, url, description, provider)
WHERE NOT EXISTS (SELECT 1 FROM remi_project.learning_resources r WHERE r.url = v.url);

INSERT INTO remi_project.competency_resources (competency_id, resource_id)
SELECT c.competency_id, r.resource_id
FROM (VALUES
  ('Вычислять значение функции', 'https://openedu.ru/course/urfu/CALC/?session=fall_2026'),
  ('Понимать смысл предела', 'https://stepik.org/course/716/promo'),
  ('Вычислять предел подстановкой', 'https://stepik.org/course/229762/promo'),
  ('Находить производную', 'https://stepik.org/course/229762/promo'),
  ('Вычислять производную многочлена', 'https://openedu.ru/course/urfu/CALC/?session=fall_2026'),
  ('Находить первообразную', 'https://openedu.ru/course/msu/MATHAN/'),
  ('Вычислять определённый интеграл', 'https://openedu.ru/course/msu/MATHAN/')
) AS v(competency, url)
JOIN remi_project.competencies c ON c.name = v.competency
JOIN remi_project.topics t ON t.topic_id = c.topic_id
JOIN remi_project.disciplines d ON d.discipline_id = t.discipline_id AND d.name = 'Высшая математика'
JOIN remi_project.learning_resources r ON r.url = v.url
ON CONFLICT (competency_id, resource_id) DO NOTHING;

COMMIT;
