-- Примеры запросов к расширенной схеме RemI AI.

-- 1. История оценок: освоение и уверенность отображаются отдельно.
SELECT s.display_name, c.name AS competency, e.knowledge_status,
       e.mastery_score, e.evidence_confidence, e.explanation, e.estimated_at
FROM remi_project.mastery_estimates e
JOIN remi_project.students s ON s.student_id = e.student_id
JOIN remi_project.competencies c ON c.competency_id = e.competency_id
ORDER BY s.display_name, e.estimated_at DESC;

-- 2. Основания оценки: ответы, связанные с ней.
SELECT e.estimate_id, c.name AS competency, a.answer_text, a.is_correct
FROM remi_project.mastery_estimates e
JOIN remi_project.competencies c ON c.competency_id = e.competency_id
JOIN remi_project.estimate_evidence ev ON ev.estimate_id = e.estimate_id
JOIN remi_project.student_answers a ON a.answer_id = ev.answer_id
ORDER BY e.estimate_id, a.answer_id;

-- 3. Шаги маршрута и связанные учебные материалы.
SELECT s.display_name, r.route_id, rs.position, c.name AS competency,
       rs.status, rs.explanation, lr.title AS resource, lr.review_status
FROM remi_project.learning_routes r
JOIN remi_project.students s ON s.student_id = r.student_id
JOIN remi_project.route_steps rs ON rs.route_id = r.route_id
JOIN remi_project.competencies c ON c.competency_id = rs.competency_id
LEFT JOIN remi_project.route_step_resources rr ON rr.route_step_id = rs.route_step_id
LEFT JOIN remi_project.learning_resources lr ON lr.resource_id = rr.resource_id
ORDER BY r.route_id, rs.position;

-- 4. Вопросы, которым требуется проверка.
SELECT question_id, question_text, answer_type, validation_status
FROM remi_project.questions
WHERE validation_status = 'pending'
ORDER BY question_id;
