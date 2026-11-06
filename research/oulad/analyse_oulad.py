"""Сводная проверка официального архива OULAD без выгрузки персональных строк."""
import csv
import io
import json
import os
import sys
import zipfile
from collections import Counter

archive_path = os.path.join(os.path.dirname(__file__), 'oulad.zip')
result = {'source': 'https://doi.org/10.24432/C5KK69', 'files': {}}

with zipfile.ZipFile(archive_path) as archive:
    def rows(name):
        with archive.open(name) as binary:
            yield from csv.DictReader(io.TextIOWrapper(binary, encoding='utf-8-sig', newline=''))

    courses = list(rows('courses.csv'))
    result['files']['courses.csv'] = {'rows': len(courses), 'modules': len({x['code_module'] for x in courses}),
                                      'presentations': len({(x['code_module'], x['code_presentation']) for x in courses})}
    course_keys = {(x['code_module'], x['code_presentation']) for x in courses}
    info = list(rows('studentInfo.csv'))
    enrollment_keys = {(x['code_module'], x['code_presentation'], x['id_student']) for x in info}
    result['files']['studentInfo.csv'] = {
        'rows': len(info), 'unique_student_ids': len({x['id_student'] for x in info}),
        'unique_enrollments': len(enrollment_keys),
        'results': dict(sorted(Counter(x['final_result'] for x in info).items())),
        'missing_total': sum(any(v == '' or v == '?' for v in x.values()) for x in info),
        'unmatched_courses': sum((x['code_module'], x['code_presentation']) not in course_keys for x in info)}
    registrations = list(rows('studentRegistration.csv'))
    result['files']['studentRegistration.csv'] = {
        'rows': len(registrations),
        'missing_registration_date': sum(x['date_registration'] in ('', '?') for x in registrations),
        'missing_unregistration_date': sum(x['date_unregistration'] in ('', '?') for x in registrations),
        'unmatched_enrollments': sum((x['code_module'], x['code_presentation'], x['id_student']) not in enrollment_keys for x in registrations)}
    assessments = list(rows('assessments.csv'))
    assess_by_id = {x['id_assessment']: x for x in assessments}
    result['files']['assessments.csv'] = {'rows': len(assessments), 'types': dict(sorted(Counter(x['assessment_type'] for x in assessments).items())),
        'missing_date': sum(x['date'] in ('', '?') for x in assessments), 'unique_ids': len(assess_by_id)}
    scores = list(rows('studentAssessment.csv'))
    grades = [float(x['score']) for x in scores if x['score'] not in ('', '?')]
    result['files']['studentAssessment.csv'] = {
        'rows': len(scores), 'missing_score': len(scores) - len(grades),
        'mean_score_nonmissing': round(sum(grades) / len(grades), 2),
        'unmatched_assessments': sum(x['id_assessment'] not in assess_by_id for x in scores),
        'unmatched_enrollments': sum((assess_by_id[x['id_assessment']]['code_module'], assess_by_id[x['id_assessment']]['code_presentation'], x['id_student']) not in enrollment_keys for x in scores if x['id_assessment'] in assess_by_id),
        'banked': sum(x['is_banked'] == '1' for x in scores)}
    materials = list(rows('vle.csv'))
    material_ids = {x['id_site'] for x in materials}
    result['files']['vle.csv'] = {'rows': len(materials), 'activity_types': dict(sorted(Counter(x['activity_type'] for x in materials).items())),
        'missing_week_from': sum(x['week_from'] in ('', '?') for x in materials),
        'missing_week_to': sum(x['week_to'] in ('', '?') for x in materials)}
    activity_count = clicks = before_start = missing_student = missing_material = 0
    for x in rows('studentVle.csv'):
        activity_count += 1
        clicks += int(x['sum_click'])
        before_start += int(x['date']) < 0
        missing_student += (x['code_module'], x['code_presentation'], x['id_student']) not in enrollment_keys
        missing_material += x['id_site'] not in material_ids
    result['files']['studentVle.csv'] = {'rows': activity_count, 'total_clicks': clicks, 'rows_before_start': before_start,
        'unmatched_enrollments': missing_student, 'unmatched_material_ids': missing_material}

print(json.dumps(result, ensure_ascii=False, indent=2))
