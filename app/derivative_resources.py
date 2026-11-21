"""Дополнительные источники пилота. Проверка страницы не заменяет экспертизу."""

CHECKED_ON = '2026-11-15'
_FUNCTIONS = ('Понятие функции и предела — лекция 2',
              'https://teach-in.ru/lecture/09_10_Bikov', 'МГУ / Teach-in')
_DERIVATIVE = ('Производная — лекция 7',
               'https://teach-in.ru/lecture/10_15_Bikov', 'МГУ / Teach-in')
_DIFF_PRACTICE = ('Как найти производную? Примеры решений',
                  'https://mathprofi.ru/kak_naiti_proizvodnuju.html', 'MathProfi')
_LIMITS = ('Пределы функций: примеры решений',
           'https://mathprofi.ru/predely_primery_reshenii.html', 'MathProfi')
_EQUATIONS = ('Линейное уравнение с одной переменной',
              'https://interneturok.ru/h/biblioteka/algebra/7-klass/lineynoe-uravnenie-s-odnoy-peremennoy/1',
              'InternetUrok')

CURATED = {
    'Решать линейное уравнение': [_EQUATIONS],
    'Вычислять значение функции': [_FUNCTIONS],
    'Понимать смысл предела': [_FUNCTIONS],
    'Вычислять предел подстановкой': [_LIMITS],
    'Находить производную': [_DERIVATIVE, _DIFF_PRACTICE],
    'Вычислять производную многочлена': [_DIFF_PRACTICE],
}

# Проверено описание курса: бесплатно доступна первая неделя, полный доступ платный.
RESOURCE_NOTES = {
    'https://openedu.ru/course/urfu/CALC/?session=fall_2026':
        'Бесплатно доступна первая неделя; полный доступ платный. Условия могут измениться.',
    'https://stepik.org/course/716/promo':
        'Название курса найдено; полное содержание и запись не проверены.',
    'https://stepik.org/course/229762/promo':
        'Название курса найдено; полное содержание и запись не проверены.',
}


def add_curated(nodes, resources):
    combined = []
    for node in nodes:
        for title, url, provider in CURATED.get(node['name'], []):
            combined.append({'competency_id': node['competency_id'], 'title': title, 'url': url,
                             'provider': provider, 'review_status': 'pending',
                             'check_note': f'Страница и тема проверены {CHECKED_ON}; экспертная проверка не проведена.'})
    seen = {(item['competency_id'], item['url']) for item in combined}
    for item in resources:
        key = item['competency_id'], item['url']
        if key not in seen:
            combined.append({**item, 'check_note': RESOURCE_NOTES.get(item['url'], '')})
            seen.add(key)
    return combined
