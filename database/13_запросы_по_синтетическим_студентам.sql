-- Только вымышленные студенты набора demo-150-v1.
SELECT s.student_id, s.display_name, s.email
FROM remi_project.synthetic_students ss
JOIN remi_project.students s USING (student_id)
WHERE ss.dataset_name = 'demo-150-v1'
ORDER BY ss.student_number
LIMIT 20;

-- Сколько студентов выбрало каждую дисциплину.
SELECT d.name AS discipline, COUNT(DISTINCT ss.student_id) AS students
FROM remi_project.synthetic_students ss
JOIN remi_project.diagnostic_sessions ds ON ds.student_id = ss.student_id
    AND ds.stop_reason = 'Синтетический набор demo-150-v1; результаты смоделированы.'
JOIN remi_project.competencies c ON c.competency_id = ds.target_competency_id
JOIN remi_project.topics t ON t.topic_id = c.topic_id
JOIN remi_project.disciplines d ON d.discipline_id = t.discipline_id
WHERE ss.dataset_name = 'demo-150-v1'
GROUP BY d.name ORDER BY d.name;

-- Учебные ответы одного студента: не считать эти данные настоящей диагностикой.
SELECT s.display_name, q.question_text, a.answer_text, a.is_correct
FROM remi_project.synthetic_students ss
JOIN remi_project.students s USING (student_id)
JOIN remi_project.diagnostic_sessions ds ON ds.student_id = s.student_id
    AND ds.stop_reason = 'Синтетический набор demo-150-v1; результаты смоделированы.'
JOIN remi_project.student_answers a USING (session_id)
JOIN remi_project.questions q USING (question_id)
WHERE ss.dataset_name = 'demo-150-v1' AND ss.student_number = 1
ORDER BY a.answered_at, a.answer_id;
