-- Учебная аттестация: только синтетические сессии demo-150-v1.
-- Прогноз третьего ответа после первых двух. Метки смоделированы и не
-- представляют проверенные знания учащихся.
-- Выполнять в базе RemI_AI. Не затрагивает исходные таблицы.
CREATE VIEW remi_project.attestation_next_answer_v1 AS
WITH ordered_answers AS (
    SELECT ss.student_number, ds.session_id, d.name AS discipline,
           a.is_correct, a.grading_method, q.answer_type,
           ROW_NUMBER() OVER (
               PARTITION BY ds.session_id ORDER BY a.answered_at, a.answer_id
           ) AS answer_order
    FROM remi_project.synthetic_students AS ss
    JOIN remi_project.diagnostic_sessions AS ds
      ON ds.student_id = ss.student_id
     AND ds.stop_reason = 'Синтетический набор demo-150-v1; результаты смоделированы.'
    JOIN remi_project.competencies AS c ON c.competency_id = ds.target_competency_id
    JOIN remi_project.topics AS t ON t.topic_id = c.topic_id
    JOIN remi_project.disciplines AS d ON d.discipline_id = t.discipline_id
    JOIN remi_project.student_answers AS a ON a.session_id = ds.session_id
    JOIN remi_project.questions AS q ON q.question_id = a.question_id
    WHERE ss.dataset_name = 'demo-150-v1'
), summary AS (
    SELECT student_number, session_id, discipline,
           COUNT(*) FILTER (WHERE answer_order <= 2) AS previous_answers,
           COUNT(is_correct) FILTER (WHERE answer_order <= 2) AS previous_scored,
           COUNT(*) FILTER (WHERE answer_order <= 2 AND is_correct IS TRUE) AS previous_correct,
           MAX(answer_type) FILTER (WHERE answer_order = 3) AS next_question_type,
           BOOL_OR(is_correct) FILTER (WHERE answer_order = 3) AS next_correct,
           MAX(grading_method) FILTER (WHERE answer_order = 3) AS next_grading_method,
           COUNT(*) FILTER (WHERE answer_order = 3) AS next_answer_count
    FROM ordered_answers
    WHERE answer_order <= 3
    GROUP BY student_number, session_id, discipline
)
SELECT student_number, session_id, discipline, previous_answers,
       previous_scored, previous_correct, next_question_type,
       next_correct, next_grading_method
FROM summary
WHERE previous_answers = 2 AND next_answer_count = 1;

-- После создания можно выполнить запрос ниже и сохранить результат в CSV.
SELECT * FROM remi_project.attestation_next_answer_v1 ORDER BY student_number;
