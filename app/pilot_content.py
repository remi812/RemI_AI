"""Authored pilot bank. Every imported version and section starts pending."""
from app.derivatives import QUESTIONS, RETAKE_QUESTIONS

ERROR = "Вычислять ошибку управления"
LOOP = "Различать разомкнутую и замкнутую системы"
FEEDBACK = "Понимать отрицательную обратную связь"
DERIV = "Вычислять производную многочлена"
PYTHON = "Определять число повторений цикла"
KEY_SKILLS = {"control": [ERROR, LOOP, FEEDBACK], "derivatives": [DERIV, "Находить производную"],
              "programming": [PYTHON, "Понимать цикл"],
              "programming-variables": ["Использовать переменные"],
              "programming-types": ["Различать типы данных Python"],
              "programming-conditions": ["Использовать условие"],
              "control-system": ["Распознавать систему управления"],
              "control-signals": [ERROR]}

# Within each phase, the first task opens the skill, the second is a simpler probe,
# the third is an application. A mixed pair can use the remaining probe.
def numeric(text, answer):
    return ("numeric", text, str(answer), None)


def choice(text, *options, answer):
    return ("choice", text, options[answer], list(options))


def short(text, *allowed):
    return ("short_text", text, "|".join(allowed), None)


SPECIAL = {
    ERROR: {
        "initial": [numeric("Уставка 18 °C, датчик показывает 21 °C. Найди ошибку в градусах при единичной отрицательной обратной связи.", -3),
                    numeric("Используй e = r − y. Чему равно e при r = 9 и y = 4?", 5),
                    numeric("При задании −2 °C измерено −5 °C. Чему равна ошибка e = r − y?", 3)],
        "retake": [numeric("Нужны 40 оборотов в минуту, измерено 46. Найди e = r − y в об/мин.", -6),
                   numeric("Целевой уровень 1,5 м, измеренный 1,2 м. Чему равна ошибка в метрах?", 0.3),
                   numeric("Выход вырос с 4 до 7 при уставке 6. Чему теперь равна ошибка e = r − y?", -1)]},
    LOOP: {
        "initial": [choice("Термометр только записывает температуру. Нагреватель включается по таймеру. Каков контур регулирования температуры?", "Замкнутый", "Разомкнутый", answer=1),
                    choice("Регулятор меняет мощность по измеренной температуре комнаты. Каков контур?", "Замкнутый", "Разомкнутый", answer=0),
                    short("Насос управляется по уровню воды в баке. Назови контур одним словом (разомкнутый или замкнутый).", "замкнутый")],
        "retake": [choice("Привод получает команду по расписанию. Какие изменения замкнут контур по скорости?", "Запись скорости в журнал", "Коррекция команды по измеренной скорости", "Увеличение частоты команд", answer=1),
                   short("Орошение длится ровно 5 минут независимо от влажности. Назови контур по влажности одним словом (замкнутый или разомкнутый).", "разомкнутый"),
                   choice("Прибор показывает давление оператору. Автоматика меняет клапан только по времени. Как работает автоматика по давлению?", "По разомкнутому контуру", "По замкнутому контуру", answer=0)]},
}

EXTRA = {
    FEEDBACK: numeric("Задание постоянно. Выход увеличился на 4. На сколько со знаком изменилось e = r − y?", -4),
    "Различать задание и выход": choice("Оператор установил 80 °C, измерено 73 °C. Какой сигнал является выходом?", "80 °C", "73 °C", answer=1),
    "Объяснять обратную связь": choice("Какое действие использует обратную связь?", "Запуск по расписанию", "Изменение мощности по измеренной скорости", answer=1),
    DERIV: numeric("Найди значение производной x³ − 4x в точке 2.", 8),
    "Находить производную": numeric("Каков наклон графика y = 3x + 7?", 3),
    PYTHON: numeric("Сколько значений перебирает for n in range(2, 9, 3)?", 3),
    "Понимать цикл": short("Какое ключевое слово начинает цикл перебора элементов в Python? Введи одно слово.", "for"),
}


def questions_for(name, phase):
    if name in SPECIAL:
        return SPECIAL[name][phase]
    source = QUESTIONS if phase == "initial" else RETAKE_QUESTIONS
    rows = [("choice", text, options[index], options) for text, options, index in source.get(name, [])]
    if phase == "initial" and name in EXTRA:
        rows.append(EXTRA[name])
    return rows


TOE = ("Курс лекций по ТАУ", "https://www.toehelp.ru/theory/tau/contents.html")
TEX = ("Теория автоматического управления: конспект лекций", "https://www.texnic.ru/tools/lekcii/tau_kl/tau0.htm")
MATH = ("MathProfi", "https://mathprofi.ru/lekcii_po_vysshei_matematike.html")
TUTOR = ("Интерактивный учебник языка Python", "https://pythontutor.ru/")
TAU1 = "https://www.toehelp.ru/theory/tau/lecture01.htm"
SECTIONS = {
    "control": [
        (TOE, "1.2.3. Принцип обратной связи", TAU1,
         "Сравнивающее устройство вычитает измеренный выход из задания. По рисунку 8 можно проследить знак отклонения и действие регулятора.",
         [ERROR, FEEDBACK, "Различать задание и выход", "Объяснять обратную связь"]),
        (TOE, "1.2.1. Принцип разомкнутого управления", TAU1,
         "Схема печи показывает, как программа задаёт нагрев без коррекции по измеренной температуре. Сопоставьте с рисунком 7 в подразделе 1.2.3.",
         [LOOP, "Распознавать систему управления", "Определять объект управления"]),
        (TEX, "Введение перед первой лекцией", TEX[1],
         "Сравните регулирование температуры с поливом по таймеру. Проследите, влияет ли результат измерения на управляющее действие.",
         [LOOP, "Объяснять обратную связь"])],
    "derivatives": [
        (MATH, "Как найти производную? Правило суммы", "https://mathprofi.ru/kak_naiti_proizvodnuju.html",
         "Разберите по слагаемым производную многочлена и вынесите постоянный множитель за знак производной.", [DERIV,"Находить производную"]),
        (MATH, "Пределы функций. Примеры решений", "https://mathprofi.ru/predely_primery_reshenii.html",
         "Проверьте подстановку аргумента и вычисление предела функции в точке.", ["Понимать смысл предела","Вычислять предел подстановкой"])],
    "programming": [
        (TUTOR, "Цикл for. Функция range", "https://pythontutor.ru/lessons/for_loop/",
         "Определите границы диапазона, шаг и число итераций цикла.", [PYTHON,"Понимать цикл"]),
        (TUTOR, "Условия. Операторы сравнения", "https://pythontutor.ru/lessons/ifelse/",
         "Проследите ветвление if и else, значение логического выражения и выбор команды.", ["Вычислять логическое условие Python","Использовать условие"]),
        (TUTOR, "Ввод и вывод данных", "https://pythontutor.ru/lessons/inout_and_arithmetic_operations/",
         "Проверьте присваивание переменной, строковый ввод и перевод значения в число.", ["Использовать переменные","Различать типы данных Python"])],
}

