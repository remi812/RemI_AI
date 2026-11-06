"""Создаёт SQL для отдельной исследовательской схемы без данных отдельных студентов."""
import csv
import io
import json
import os
import zipfile

base = os.path.dirname(__file__)

def literal(value):
    if value is None or value in ('', '?'):
        return 'NULL'
    return "'" + str(value).replace("'", "''") + "'"

with open(os.path.join(base, 'summary.json'), encoding='utf-8-sig') as f:
    summary = json.load(f)
with open(os.path.join(base, 'week4_summary.json'), encoding='utf-8-sig') as f:
    week4 = json.load(f)
with zipfile.ZipFile(os.path.join(base, 'oulad.zip')) as archive:
    def rows(name):
        with archive.open(name) as f:
            return list(csv.DictReader(io.TextIOWrapper(f, encoding='utf-8-sig', newline='')))
    courses, assessments = rows('courses.csv'), rows('assessments.csv')

lines = [
    '-- OULAD: отдельный раздел для исследований; никаких персональных строк.',
    '-- Источник: Kuzilek, Hlosta, Zdrahal (2015), https://doi.org/10.24432/C5KK69, CC BY 4.0.',
    '-- Выполнять один раз: наличие схемы остановит транзакцию без изменения данных.',
    'BEGIN;',
    'CREATE SCHEMA oulad_research;',
    'CREATE TABLE oulad_research.course_runs (module_code TEXT NOT NULL, presentation_code TEXT NOT NULL, duration_days INTEGER NOT NULL, PRIMARY KEY(module_code, presentation_code));',
    'CREATE TABLE oulad_research.assessments (assessment_id INTEGER PRIMARY KEY, module_code TEXT NOT NULL, presentation_code TEXT NOT NULL, assessment_type TEXT NOT NULL, due_day INTEGER, weight NUMERIC NOT NULL, FOREIGN KEY(module_code, presentation_code) REFERENCES oulad_research.course_runs(module_code, presentation_code));',
    'CREATE TABLE oulad_research.source_table_counts (source_file TEXT PRIMARY KEY, row_count BIGINT NOT NULL);',
    'CREATE TABLE oulad_research.final_outcomes (outcome TEXT PRIMARY KEY, enrollment_count INTEGER NOT NULL);',
    'CREATE TABLE oulad_research.week4_outcomes (outcome TEXT PRIMARY KEY, enrollments INTEGER NOT NULL, no_logged_activity INTEGER NOT NULL, median_clicks NUMERIC NOT NULL, mean_clicks NUMERIC NOT NULL, median_active_days NUMERIC NOT NULL, FOREIGN KEY(outcome) REFERENCES oulad_research.final_outcomes(outcome));',
    "COMMENT ON SCHEMA oulad_research IS 'OULAD, doi:10.24432/C5KK69, CC BY 4.0; отдельные учебные исследования, данные не являются студентами RemI AI.';",
    "COMMENT ON TABLE oulad_research.week4_outcomes IS 'Описательный срез дней 0–27 среди зарегистрированных к дню 0 и не отчислившихся до конца окна; группы по известному после курса результату; связь не доказывает причину.';",
    'INSERT INTO oulad_research.course_runs (module_code, presentation_code, duration_days) VALUES\n' + ',\n'.join('(%s, %s, %d)' % (literal(x['code_module']), literal(x['code_presentation']), int(x['module_presentation_length'])) for x in courses) + ';',
    'INSERT INTO oulad_research.assessments (assessment_id, module_code, presentation_code, assessment_type, due_day, weight) VALUES\n' + ',\n'.join('(%d, %s, %s, %s, %s, %s)' % (int(x['id_assessment']), literal(x['code_module']), literal(x['code_presentation']), literal(x['assessment_type']), 'NULL' if x['date'] in ('', '?') else str(int(float(x['date']))), str(float(x['weight']))) for x in assessments) + ';',
    'INSERT INTO oulad_research.source_table_counts (source_file, row_count) VALUES\n' + ',\n'.join('(%s, %d)' % (literal(k), v['rows']) for k, v in summary['files'].items()) + ';',
    'INSERT INTO oulad_research.final_outcomes (outcome, enrollment_count) VALUES\n' + ',\n'.join('(%s, %d)' % (literal(k), v) for k, v in summary['files']['studentInfo.csv']['results'].items()) + ';',
    'INSERT INTO oulad_research.week4_outcomes (outcome, enrollments, no_logged_activity, median_clicks, mean_clicks, median_active_days) VALUES\n' + ',\n'.join('(%s, %d, %d, %s, %s, %s)' % (literal(k), v['enrollments'], v['no_logged_activity_in_window'], v['median_clicks'], v['mean_clicks'], v['median_active_days']) for k, v in week4['groups_by_eventual_final_result'].items()) + ';',
    'COMMIT;\n',
]
output = os.path.join(base, 'oulad_research.sql')
with open(output, 'w', encoding='utf-8', newline='\n') as f:
    f.write('\n\n'.join(lines))
print('Создан исследовательский SQL: 22 запуска курсов, 206 контрольных работ и сводные показатели.')
