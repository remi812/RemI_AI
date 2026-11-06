-- Отдельный исследовательский раздел: данные OULAD, CC BY 4.0.
-- Запуски семи обезличенных модулей.
SELECT module_code, COUNT(*) AS course_runs,
       MIN(duration_days) AS min_duration_days,
       MAX(duration_days) AS max_duration_days
FROM oulad_research.course_runs
GROUP BY module_code
ORDER BY module_code;

-- Контрольные работы по типам и курсам.
SELECT module_code, assessment_type, COUNT(*) AS assessments
FROM oulad_research.assessments
GROUP BY module_code, assessment_type
ORDER BY module_code, assessment_type;

-- Итоги всех записей о прохождении; один студент мог быть записан более одного раза.
SELECT outcome, enrollment_count
FROM oulad_research.final_outcomes
ORDER BY enrollment_count DESC;

-- Ретроспективный анализ первых 28 дней: итог стал известен только после курса.
-- Выборка: зарегистрированные к дню 0 и без записи о прекращении до конца дня 27.
SELECT outcome, enrollments, median_clicks, mean_clicks,
       median_active_days, no_logged_activity
FROM oulad_research.week4_outcomes
ORDER BY median_clicks DESC;
