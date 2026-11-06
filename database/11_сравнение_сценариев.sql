-- Сравнение вымышленных маршрутов для двух студентов.
SELECT s.display_name, rs.position, d.name AS discipline, c.name AS competency,
       rs.explanation, e.knowledge_status
FROM remi_project.learning_routes lr
JOIN remi_project.students s ON s.student_id = lr.student_id
JOIN remi_project.route_steps rs ON rs.route_id = lr.route_id
JOIN remi_project.competencies c ON c.competency_id = rs.competency_id
JOIN remi_project.topics t ON t.topic_id = c.topic_id
JOIN remi_project.disciplines d ON d.discipline_id = t.discipline_id
LEFT JOIN remi_project.mastery_estimates e ON e.estimate_id = rs.estimate_id
WHERE lr.algorithm_version = 'manual-demo-10'
ORDER BY s.display_name, rs.position;

-- Ответы, послужившие учебными примерами для предварительной оценки.
SELECT s.display_name, c.name AS competency, q.question_text, a.answer_text,
       a.is_correct, e.knowledge_status, e.explanation
FROM remi_project.mastery_estimates e
JOIN remi_project.students s ON s.student_id = e.student_id
JOIN remi_project.competencies c ON c.competency_id = e.competency_id
JOIN remi_project.estimate_evidence ev ON ev.estimate_id = e.estimate_id
JOIN remi_project.student_answers a ON a.answer_id = ev.answer_id
JOIN remi_project.questions q ON q.question_id = a.question_id
WHERE e.algorithm_version = 'manual-demo-10'
ORDER BY s.display_name, a.answer_id;
