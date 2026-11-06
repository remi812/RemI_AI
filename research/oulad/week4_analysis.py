"""Описательное сравнение активности OULAD к концу 28-го дня.

Единица наблюдения — студент в конкретном запуске курса. Итог известен только
после курса и используется исключительно для ретроспективной группировки.
"""
import csv
import io
import json
import os
import statistics
import zipfile
from collections import Counter, defaultdict

BASE = os.path.dirname(__file__)
with zipfile.ZipFile(os.path.join(BASE, 'oulad.zip')) as archive:
    def rows(name):
        with archive.open(name) as binary:
            yield from csv.DictReader(io.TextIOWrapper(binary, encoding='utf-8-sig', newline=''))

    def key(row):
        return (row['code_module'], row['code_presentation'], row['id_student'])

    outcomes = {key(x): x['final_result'] for x in rows('studentInfo.csv')}
    eligible = set()
    exclusions = Counter()
    for row in rows('studentRegistration.csv'):
        start, stop = row['date_registration'], row['date_unregistration']
        if start in ('', '?'):
            exclusions['registration_unknown'] += 1
        elif int(start) > 0:
            exclusions['registered_after_day_zero'] += 1
        elif stop not in ('', '?') and int(stop) <= 27:
            exclusions['withdrawal_on_or_before_day_27'] += 1
        else:
            eligible.add(key(row))

    clicks = defaultdict(int)
    active_days = defaultdict(set)
    activity_rows = 0
    for row in rows('studentVle.csv'):
        date = int(row['date'])
        if 0 <= date <= 27:
            k = key(row)
            if k in eligible:
                clicks[k] += int(row['sum_click'])
                active_days[k].add(date)
                activity_rows += 1

    by_result = defaultdict(list)
    for k in eligible:
        by_result[outcomes[k]].append((clicks.get(k, 0), len(active_days.get(k, ())), k in active_days))

    summary = {}
    for outcome, values in sorted(by_result.items()):
        counts = [v[0] for v in values]
        days = [v[1] for v in values]
        summary[outcome] = {
            'enrollments': len(values),
            'no_logged_activity_in_window': sum(not v[2] for v in values),
            'median_clicks': statistics.median(counts),
            'mean_clicks': round(statistics.mean(counts), 2),
            'median_active_days': statistics.median(days),
        }
    output = {
        'window': 'day 0 through day 27 inclusive',
        'unit': 'student, module, presentation',
        'eligible_rule': 'registration day <= 0 and no recorded withdrawal on days <= 27',
        'eligible_enrollments': len(eligible),
        'exclusions': dict(exclusions),
        'activity_rows_in_window_for_eligible': activity_rows,
        'groups_by_eventual_final_result': summary,
        'limitations': 'Descriptive retrospective grouping; absence of logs is not proof of no learning; final outcome is not an available early feature.'
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))
