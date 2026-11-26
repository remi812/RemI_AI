"""Catalogue entry points and the skills assessed at the start of each route."""
MATH = "Высшая математика"
PYTHON = "Основы программирования"
TAU = "Теория автоматического управления"
MODELING = "Моделирование систем"

# The goal is first. Other entries are key skills with separate diagnostic evidence.
TOPICS = {
    "functions": (MATH, "Функции", ["Находить область определения функции", "Вычислять значение функции"]),
    "algebra": (MATH, "Алгебра", ["Решать уравнения с дробными коэффициентами", "Выполнять действия с дробями"]),
    "limits": (MATH, "Пределы", ["Вычислять предел подстановкой", "Понимать смысл предела"]),
    "derivatives": (MATH, "Производные", ["Вычислять производную многочлена", "Находить производную"]),
    "rates": (MATH, "Применение производных", ["Определять скорость изменения"]),
    "integrals": (MATH, "Интегралы", ["Вычислять определённый интеграл", "Находить первообразную"]),
    "differential-equations": (MATH, "Введение в дифференциальные уравнения", ["Распознавать дифференциальное уравнение"]),
    "programming": (PYTHON, "Циклы", ["Определять число повторений цикла", "Понимать цикл"]),
    "programming-variables": (PYTHON, "Переменные", ["Использовать переменные"]),
    "programming-types": (PYTHON, "Типы данных", ["Преобразовывать типы Python", "Различать типы данных Python"]),
    "programming-conditions": (PYTHON, "Условия", ["Использовать условие"]),
    "programming-functions": (PYTHON, "Функции Python", ["Понимать return", "Вызывать функцию Python"]),
    "programming-lists": (PYTHON, "Списки Python", ["Обновлять список и проверять результат", "Добавлять элемент в список"]),
    "control": (TAU, "Обратная связь", ["Понимать отрицательную обратную связь", "Вычислять ошибку управления", "Различать разомкнутую и замкнутую системы"]),
    "control-system": (TAU, "Понятие системы управления", ["Распознавать систему управления"]),
    "control-signals": (TAU, "Сигналы и элементы системы", ["Вычислять ошибку управления", "Определять роль датчика"]),
    "control-transfer": (TAU, "Передаточные функции", ["Читать передаточную функцию"]),
    "control-blocks": (TAU, "Структурные схемы", ["Определять передаточную функцию последовательных звеньев"]),
    "control-transients": (TAU, "Переходные процессы и устойчивость", ["Описывать отклик звена первого порядка", "Оценивать устойчивость простого звена"]),
    "modeling": (MODELING, "Математические модели", ["Распознавать математическую модель"]),
}

PILOTS = {slug: {"discipline": discipline, "topic": topic, "goal": skills[0]}
          for slug, (discipline, topic, skills) in TOPICS.items()}
KEY_SKILLS = {slug: skills for slug, (_, _, skills) in TOPICS.items() if slug != "modeling"}
# Keep the established order of the two branching probes for the feedback route.
KEY_SKILLS["control"] = KEY_SKILLS["control"][1:] + KEY_SKILLS["control"][:1]
