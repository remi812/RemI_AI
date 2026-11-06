-- Оба набора вымышленных студентов и их учебной активности.
SELECT ss.dataset_name, COUNT(DISTINCT ss.student_id) AS students,
       COUNT(DISTINCT ds.session_id) AS sessions,
       COUNT(DISTINCT a.answer_id) AS answers,
       COUNT(DISTINCT lr.route_id) AS routes
FROM remi_project.synthetic_students ss
JOIN remi_project.diagnostic_sessions ds
  ON ds.student_id = ss.student_id
 AND ds.stop_reason = 'Синтетический набор ' || ss.dataset_name || '; результаты смоделированы.'
JOIN remi_project.student_answers a ON a.session_id = ds.session_id
JOIN remi_project.learning_routes lr
  ON lr.session_id = ds.session_id AND lr.algorithm_version = 'synthetic-' || ss.dataset_name
WHERE ss.dataset_name IN ('demo-150-v1', 'demo-150-v2')
GROUP BY ss.dataset_name ORDER BY ss.dataset_name;

-- Выборка студентов второго набора и учебных целей.
SELECT s.display_name, d.name AS discipline, c.name AS goal
FROM remi_project.synthetic_students ss
JOIN remi_project.students s ON s.student_id = ss.student_id
JOIN remi_project.diagnostic_sessions ds ON ds.student_id = s.student_id
 AND ds.stop_reason = 'Синтетический набор demo-150-v2; результаты смоделированы.'
JOIN remi_project.competencies c ON c.competency_id = ds.target_competency_id
JOIN remi_project.topics t ON t.topic_id = c.topic_id
JOIN remi_project.disciplines d ON d.discipline_id = t.discipline_id
WHERE ss.dataset_name = 'demo-150-v2'
ORDER BY ss.student_number LIMIT 20;

-- Сколько вымышленных студентов выбрали каждую дисциплину во втором наборе.
SELECT d.name AS discipline, COUNT(*) AS students
FROM remi_project.synthetic_students ss
JOIN remi_project.diagnostic_sessions ds ON ds.student_id = ss.student_id
 AND ds.stop_reason = 'Синтетический набор demo-150-v2; результаты смоделированы.'
JOIN remi_project.competencies c ON c.competency_id = ds.target_competency_id
JOIN remi_project.topics t ON t.topic_id = c.topic_id
JOIN remi_project.disciplines d ON d.discipline_id = t.discipline_id
WHERE ss.dataset_name = 'demo-150-v2'
GROUP BY d.name ORDER BY d.name;
