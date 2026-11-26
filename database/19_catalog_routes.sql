BEGIN;
SET LOCAL search_path = remi_project, pg_catalog;
CREATE TABLE IF NOT EXISTS catalog_migrations (
    version integer PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now()
);
INSERT INTO competencies(topic_id, name, description)
SELECT t.topic_id, v.skill, v.description FROM (VALUES
 ('Высшая математика','Алгебра','Решать уравнения с дробными коэффициентами','Привести дроби к общему знаменателю и найти неизвестное.'),
 ('Основы программирования','Списки Python','Обновлять список и проверять результат','Добавить элемент и определить новую длину или значение элемента.'),
 ('Теория автоматического управления','Переходные процессы и устойчивость','Описывать отклик звена первого порядка','Связать полюс, постоянную времени и поведение выхода после ступеньки.')
) AS v(discipline,topic,skill,description)
JOIN disciplines d ON d.name=v.discipline JOIN topics t ON t.discipline_id=d.discipline_id AND t.name=v.topic
ON CONFLICT(topic_id,name) DO NOTHING;
INSERT INTO prerequisites(competency_id,prerequisite_id)
SELECT c.competency_id,p.competency_id FROM (VALUES
 ('Решать уравнения с дробными коэффициентами','Решать линейное уравнение'),
 ('Решать уравнения с дробными коэффициентами','Выполнять действия с дробями'),
 ('Обновлять список и проверять результат','Определять длину списка'),
 ('Обновлять список и проверять результат','Добавлять элемент в список'),
 ('Описывать отклик звена первого порядка','Определять постоянную времени звена'),
 ('Описывать отклик звена первого порядка','Оценивать устойчивость простого звена'),
 ('Различать задание и выход','Определять роль датчика'),
 ('Вычислять определённый интеграл','Вычислять простой интеграл')
) AS v(skill,parent)
JOIN competencies c ON c.name=v.skill JOIN competencies p ON p.name=v.parent
ON CONFLICT DO NOTHING;
INSERT INTO catalog_migrations(version) VALUES (19) ON CONFLICT DO NOTHING;
COMMIT;
