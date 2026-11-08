-- Представление уже создано в базе RemI_AI.
CREATE VIEW attestation_demo_3000.diagnostic_features AS
SELECT ss.student_number AS session_id,
 SUM(CASE WHEN a.stage='initial' AND a.topic='equations' THEN 1 ELSE 0 END) AS initial_equations_count,
 SUM(CASE WHEN a.stage='initial' AND a.topic='equations' AND a.correct=1 THEN 1 ELSE 0 END) AS initial_equations_correct,
 SUM(CASE WHEN a.stage='initial' AND a.topic='derivatives' THEN 1 ELSE 0 END) AS initial_derivatives_count,
 SUM(CASE WHEN a.stage='initial' AND a.topic='derivatives' AND a.correct=1 THEN 1 ELSE 0 END) AS initial_derivatives_correct,
 SUM(CASE WHEN a.stage='followup' AND a.topic='derivatives' THEN 1 ELSE 0 END) AS followup_count,
 SUM(CASE WHEN a.stage='followup' AND a.topic='derivatives' AND a.correct=1 THEN 1 ELSE 0 END) AS followup_correct,
 CASE WHEN SUM(CASE WHEN a.stage='followup' AND a.topic='derivatives' THEN 1 ELSE 0 END)=3 THEN
   CASE WHEN SUM(CASE WHEN a.stage='followup' AND a.topic='derivatives' AND a.correct=1 THEN 1 ELSE 0 END)<=1 THEN 1 ELSE 0 END ELSE NULL END AS needs_review
FROM remi_project.synthetic_students ss
JOIN remi_project.diagnostic_sessions ds ON ds.student_id=ss.student_id AND ds.stop_reason='Синтетическая учебная сессия attestation-3000-v1; оценки не подтверждены'
JOIN attestation_demo_3000.answers a ON a.session_id=ds.session_id
WHERE ss.dataset_name='attestation-3000-v1' GROUP BY ss.student_number;
