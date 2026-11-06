-- На странице указано, что запись на курс завершена. Сохраняем источник
-- для истории, но исключаем из рекомендованных до повторной проверки.
BEGIN;
UPDATE remi_project.learning_resources
SET access_type = 'запись закрыта',
    review_status = 'rejected',
    description = 'Запись закрыта; не рекомендовать до повторной проверки. По данным страницы первые две недели видеолекций доступны, остальные материалы платные.',
    link_checked_at = CURRENT_TIMESTAMP
WHERE url = 'https://openedu.ru/course/msu/MATHAN/'
  AND review_status = 'pending';
COMMIT;
