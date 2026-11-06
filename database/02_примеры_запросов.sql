-- 1. Дисциплины и их темы.
SELECT d.name AS discipline, t.name AS topic
FROM remi_project.disciplines d
LEFT JOIN remi_project.topics t ON t.discipline_id = d.discipline_id
ORDER BY d.discipline_id, t.topic_id;

-- 2. Знания, необходимые перед выбранной компетенцией.
SELECT c.name AS competency, p.name AS prerequisite
FROM remi_project.prerequisites edge
JOIN remi_project.competencies c ON c.competency_id = edge.competency_id
JOIN remi_project.competencies p ON p.competency_id = edge.prerequisite_id
ORDER BY c.name, p.name;

-- 3. Ответы студентов и результаты.
SELECT s.display_name, q.question_text, a.answer_text, a.is_correct
FROM remi_project.student_answers a
JOIN remi_project.diagnostic_sessions ds ON ds.session_id = a.session_id
JOIN remi_project.students s ON s.student_id = ds.student_id
JOIN remi_project.questions q ON q.question_id = a.question_id
ORDER BY s.student_id, a.answered_at;

-- 4. Число ответов и правильных ответов в каждой диагностике.
SELECT ds.session_id, s.display_name, COUNT(a.answer_id) AS answer_count,
       COUNT(a.answer_id) FILTER (WHERE a.is_correct = TRUE) AS correct_count
FROM remi_project.diagnostic_sessions ds
JOIN remi_project.students s ON s.student_id = ds.student_id
LEFT JOIN remi_project.student_answers a ON a.session_id = ds.session_id
GROUP BY ds.session_id, s.display_name
ORDER BY ds.session_id;

-- 5. Материалы по компетенциям.
SELECT c.name AS competency, r.title AS resource
FROM remi_project.competencies c
JOIN remi_project.competency_resources cr ON cr.competency_id = c.competency_id
JOIN remi_project.learning_resources r ON r.resource_id = cr.resource_id
ORDER BY c.name;
