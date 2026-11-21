"""Подготовка каталога из пользовательской подборки и результатов ручной проверки."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
source = (ROOT / 'EduPath_AI_kursy_ru.txt').read_text(encoding='utf-8').splitlines()
categories = {
    '1. ВЫСШАЯ МАТЕМАТИКА': 'Высшая математика',
    '2. ОСНОВЫ ПРОГРАММИРОВАНИЯ': 'Основы программирования',
    '3. МОДЕЛИРОВАНИЕ СИСТЕМ': 'Моделирование систем',
    '4. ТЕОРИЯ АВТОМАТИЧЕСКОГО УПРАВЛЕНИЯ (ТАУ)': 'Теория автоматического управления',
    'ДОПОЛНИТЕЛЬНО: СМЕЖНЫЙ КУРС': 'Основы программирования',
}
partial = {'95', '229762', '716', '227868', '83142', '512', '212681', '194633'}
unavailable = {'52892', '234343'}
uncertain_hosts = ('math.volchenko.com', 'mipt.ipu.ru', 'zaochnik.ru/blog/matematika-dlya-chajnikov/proizvodnaya', 'zaochnik.ru/blog/matematika-dlya-chajnikov/integraly')
items = []
subject = None
for index, line in enumerate(source):
    line = line.strip()
    if line in categories:
        subject = categories[line]
    if not line.startswith('https://'):
        continue
    raw_title = source[index - 1].strip().replace('★ РЕКОМЕНДУЮ | ', '')
    title, _, provider = raw_title.rpartition(' — ')
    if not title:
        title, provider = raw_title, 'Другое'
    if 'Stepik' in provider:
        kind = 'интерактивный курс'
    elif 'МГУ' in provider:
        kind = 'видеолекции'
    elif 'лекций' in title.lower() or 'системы управления' in title.lower():
        kind = 'лекции'
    else:
        kind = 'справочник'
    found = re.search(r'stepik\.org/course/(\d+)', line)
    status = 'page_found'
    note = 'Страница и тематика просмотрены; условия доступа и качество требуют проверки.'
    if found and found.group(1) in partial:
        status, note = 'title_only', 'Подтверждено название страницы; содержимое и запись не проверены.'
    if (found and found.group(1) in unavailable) or any(host in line for host in uncertain_hosts):
        status, note = 'unconfirmed', 'Страница не открылась при проверке; возможна временная недоступность.'
    original_url = line
    if 'kpolyakov.nichost.ru' in line:
        line = 'https://www.kpolyakov.spb.ru/uni/lecs.htm'
        status, note = 'unconfirmed', 'Найден адрес на сайте автора; страница есть в поиске, но прямое открытие не подтвердилось.'
    if '89909' in line:
        note += ' Для практики нужна программа SimInTech.'
    if '194633' in line:
        note += ' Смежный курс по ИИ; не относится к обязательным.'
    items.append({
        'title': title, 'provider': provider, 'url': line, 'original_url': original_url,
        'discipline': subject, 'kind': kind, 'description': source[index + 1].strip(),
        'priority': '★' in source[index - 1], 'link_status': status,
        'link_note': note, 'checked_on': '2026-11-09',
    })
(ROOT / 'database' / 'course_catalog.json').write_text(json.dumps(items, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
payload = json.dumps(items, ensure_ascii=False).replace("'", "''")
sql = """-- Каталог четырёх направлений и пользовательская подборка. Транзакция сохраняет историю.
BEGIN;
ALTER TABLE remi_project.disciplines ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE;
DO $$
BEGIN
  IF (SELECT count(*) FROM remi_project.disciplines WHERE name IN
      ('Высшая математика', 'Дифференциальные уравнения', 'Основы программирования', 'Моделирование систем', 'Теория автоматического управления')) <> 5 THEN
    RAISE EXCEPTION 'Не найдены ожидаемые дисциплины';
  END IF;
  IF EXISTS (SELECT 1 FROM remi_project.topics old_topic
    JOIN remi_project.disciplines old_d ON old_d.discipline_id=old_topic.discipline_id AND old_d.name='Дифференциальные уравнения'
    JOIN remi_project.disciplines math ON math.name='Высшая математика'
    JOIN remi_project.topics existing ON existing.discipline_id=math.discipline_id AND existing.name=old_topic.name) THEN
    RAISE EXCEPTION 'Найдены одноимённые темы; требуется отдельное объединение';
  END IF;
END $$;
UPDATE remi_project.topics SET discipline_id=(SELECT discipline_id FROM remi_project.disciplines WHERE name='Высшая математика')
 WHERE discipline_id=(SELECT discipline_id FROM remi_project.disciplines WHERE name='Дифференциальные уравнения');
UPDATE remi_project.disciplines SET is_active=FALSE WHERE name='Дифференциальные уравнения';

CREATE TABLE IF NOT EXISTS remi_project.catalog_resources (
    resource_id INTEGER PRIMARY KEY REFERENCES remi_project.learning_resources(resource_id),
    discipline_id INTEGER NOT NULL REFERENCES remi_project.disciplines(discipline_id),
    original_url TEXT NOT NULL,
    priority BOOLEAN NOT NULL DEFAULT FALSE,
    link_status TEXT NOT NULL CHECK (link_status IN ('page_found','title_only','unconfirmed')),
    link_note TEXT NOT NULL,
    checked_on DATE,
    visible BOOLEAN NOT NULL DEFAULT TRUE
);
CREATE TEMP TABLE import_course_catalog ON COMMIT DROP AS
SELECT * FROM jsonb_to_recordset('__PAYLOAD__'::jsonb) AS x(
  title text, provider text, url text, original_url text, discipline text, kind text,
  description text, priority boolean, link_status text, link_note text, checked_on date);
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM import_course_catalog c LEFT JOIN remi_project.disciplines d ON d.name=c.discipline
             WHERE d.discipline_id IS NULL) THEN RAISE EXCEPTION 'Не найдена дисциплина для ресурса'; END IF;
END $$;
INSERT INTO remi_project.learning_resources(title, resource_type, url, description, provider, language, access_type, review_status, link_checked_at)
SELECT c.title, c.kind, c.url, c.description, c.provider, 'русский', 'уточнить', 'pending', c.checked_on
FROM import_course_catalog c WHERE NOT EXISTS (SELECT 1 FROM remi_project.learning_resources r WHERE r.url=c.url);
INSERT INTO remi_project.catalog_resources(resource_id, discipline_id, original_url, priority, link_status, link_note, checked_on)
SELECT r.resource_id, d.discipline_id, c.original_url, c.priority, c.link_status, c.link_note, c.checked_on
FROM import_course_catalog c
JOIN remi_project.disciplines d ON d.name=c.discipline
JOIN LATERAL (SELECT resource_id FROM remi_project.learning_resources WHERE url=c.url ORDER BY resource_id LIMIT 1) r ON TRUE
ON CONFLICT (resource_id) DO UPDATE SET discipline_id=EXCLUDED.discipline_id, original_url=EXCLUDED.original_url,
 priority=EXCLUDED.priority, link_status=EXCLUDED.link_status, link_note=EXCLUDED.link_note, checked_on=EXCLUDED.checked_on;
COMMIT;
""".replace('__PAYLOAD__', payload)
(ROOT / 'database' / '17_каталог_курсов.sql').write_text(sql, encoding='utf-8')
print(f'Подготовлено материалов: {len(items)}')
