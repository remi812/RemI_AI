"""Repeat the AI content review against exact seeded snapshots on a disposable database."""
import os

from app.adaptive import grade
from app.pilot_content import questions_for, SECTIONS
from app.pilot_db import open_database
from pilot_acceptance import checked, profile, run_quiz


# Independently solved in editorial order (three initial, three follow-up).
# Choice answers use their text or the zero-based option position prefixed with #.
SOLUTIONS = {
    "Находить область определения функции": ("4","#0","3","-4","#1","7"),
    "Выполнять действия с дробями": ("0.875","0.5","1.5","0.7","0.5","0.5"),
    "Решать уравнения с дробными коэффициентами": ("8","12","6","12","10","6"),
    "Определять скорость изменения": ("7","s′(t)","10","-2","0.5","2"),
    "Вычислять простой интеграл": ("2x + C","x + C","3","4","#2","4"),
    "Находить первообразную": ("x³","5x","7","13","F + 7","26"),
    "Вычислять определённый интеграл": ("8","8","-2","7","0","7"),
    "Распознавать дифференциальное уравнение": ("y′+y=x","1","2","dx/dt=−2x","2","1"),
    "Преобразовывать типы Python": ("15","4","str","5","-8","#1"),
    "Вызывать функцию Python": ("8","f(3)","5","7","ping()","9"),
    "Понимать return": ("8","return","None","5","#0","5"),
    "Получать элемент списка": ("4","3","8","16","11","#2"),
    "Определять длину списка": ("3","0","2","4","1","5"),
    "Добавлять элемент в список": ("8","append","2","7","a.append(4)","None"),
    "Обновлять список и проверять результат": ("2","1","10","4","1","5"),
    "Определять роль датчика": ("#1","#0","#2","#1","#0","#2"),
    "Читать передаточную функцию": ("3","Y(s)/U(s)","6","2","3","-3"),
    "Определять передаточную функцию последовательных звеньев": ("10","#1","3","-8","1.5","3"),
    "Понимать переходный процесс": ("Переходный процесс","Единичную ступеньку","2","#1","Ступенька","1"),
    "Оценивать устойчивость простого звена": ("Затухает","−3","0","#1","Да","Нет"),
    "Определять постоянную времени звена": ("2","5","3","4","0.5","4"),
    "Описывать отклик звена первого порядка": ("0.5","#0","3","5","#1","3"),
    "Решать линейное уравнение": ("4", "7", "3", "4", "5", "-4"),
    "Вычислять значение функции": ("5", "9", "-5", "5", "5", "5"),
    "Понимать смысл предела": ("3", "2", "7", "5", "6", "Сохраняет предел 9"),
    "Вычислять предел подстановкой": ("7", "5", "6", "5", "11", "2"),
    "Находить производную": ("2x", "5", "3", "3x²", "7", "12"),
    "Вычислять производную многочлена": ("2x + 3", "6x", "8", "4x + 5", "3x²", "4"),
    "Использовать переменные": ("4", "3", "3", "6", "6", "4"),
    "Различать типы данных Python": ("float", "str", "bool", "float", "str", "float"),
    "Вычислять логическое условие Python": ("True", "False", "False", "True", "False", "False"),
    "Использовать условие": ("да", "2", "6", "a", "5", "3"),
    "Понимать цикл": ("Повторять действия", "2", "for", "Цикл", "4", "7"),
    "Определять число повторений цикла": ("3", "1", "3", "4", "0", "4"),
    "Распознавать математическую модель": ("Чтобы исследовать объект", "6", "s = v · t",
                                         "Упрощённо описывает объект", "6", "60n"),
    "Распознавать систему управления": ("#1", "#0", "#1", "Регулятор", "#0", "#1"),
    "Объяснять обратную связь": ("Измеренные обороты", "#0", "#1", "#2", "#1", "#1"),
    "Определять объект управления": ("Помещение", "Двигатель", "Печь", "Бак с водой", "Судно", "Двигатель"),
    "Различать задание и выход": ("Задание", "Выход", "73 °C", "Задание", "Выход", "240"),
    "Вычислять ошибку управления": ("-3", "5", "3", "-6", "0,3", "-1"),
    "Различать разомкнутую и замкнутую системы": ("Разомкнутый", "Замкнутый", "замкнутый",
                                                "#1", "разомкнутый", "По разомкнутому контуру"),
    "Понимать отрицательную обратную связь": ("уменьшается", "e = r − y", "-4",
                                            "Увеличить нагрев", "Минус", "Уменьшится"),
}


def verify_content(db):
    snapshots = db.execute("""SELECT c.name, v.*, q.pilot_phase FROM question_versions v
        JOIN questions q USING(question_id) JOIN competencies c ON c.competency_id=v.competency_id
        WHERE q.pilot_phase IS NOT NULL""").fetchall()
    versions = {(q["name"], q["pilot_phase"], q["question_text"]): q for q in snapshots}
    assert len(versions) == len(snapshots) == 6 * len(SOLUTIONS)
    expected_answers = {}
    for name, answers in SOLUTIONS.items():
        for phase, solutions in (("initial", answers[:3]), ("retake", answers[3:])):
            rows = questions_for(name, phase)
            assert len(rows) == len(solutions) == 3
            for (_, prompt, _, _), solution in zip(rows, solutions):
                q = versions[name, phase, prompt]
                options = q["options_snapshot"] or []
                value = options[int(solution[1:])] if solution.startswith("#") else solution
                assert grade(q, value), (name, prompt)
                assert len(options) == len(set(options))
                for wrong in [x for x in options if x != value] or ["98765"]:
                    assert not grade(q, wrong), (prompt, wrong)
                expected_answers[q["question_version_id"]] = value
    expected = {(title, url, skill) for sections in SECTIONS.values()
                for _, title, url, _, skills in sections for skill in skills}
    actual = db.execute("""SELECT r.title, r.url, c.name FROM course_sections s
        JOIN learning_resources r USING(resource_id) JOIN competency_resources cr USING(resource_id)
        JOIN competencies c USING(competency_id) WHERE r.review_status='approved'
        AND r.language='русский' AND r.access_type='открытая страница'""").fetchall()
    assert {(r["title"], r["url"], r["name"]) for r in actual} == expected
    assert {skill for _, _, skill in expected} == SOLUTIONS.keys()
    print(len(expected_answers), "версий и", len({title for title, _, _ in expected}), "разделов проверено")
    return expected_answers


def mixed_retake(slug, answers, tested):
    client, _ = profile("Проверка смешанной пары")
    run_quiz(client, slug, set())
    root = f"/api/learn/{slug}"
    for node in checked(client.get(root + "/preview"))["nodes"]:
        skill, name = node["competency_id"], node["name"]
        if name in tested:
            continue
        quiz = checked(client.post(root + "/start", json={"skill": skill}))
        seen = set()
        for correct in (False, True, True):
            question = quiz["question"]
            version = question["question_version_id"]
            assert version not in seen
            seen.add(version)
            value = answers[version]
            if not correct:
                value = next((o for o in question["options_snapshot"] or [] if o != value), "98765")
            quiz = checked(client.post(f"/api/learn/sessions/{quiz['session_id']}/answer",
                                       json={"version": version, "value": value}))
            assert quiz["correct"] == correct
        assert quiz["done"] and quiz["reason"] == "sufficient"
        progress = checked(client.get(root + "/progress"))
        assert progress["results"][str(skill)]["knowledge_status"] == "mastered"
        assert checked(client.get(f"{root}/skills/{skill}/materials"))["items"]
        tested.add(name)


if __name__ == "__main__":
    if not os.environ.get("PGDATABASE", "").endswith("_demo"):
        raise SystemExit("Нужна отдельная база *_demo")
    with open_database() as db:
        solutions = verify_content(db)
    tested = set()
    for route in SECTIONS:
        mixed_retake(route, solutions, tested)
    assert tested == SOLUTIONS.keys()
    print(f"При 1 из 2 все {len(tested)} навыков выдали третье задание и приняли результат 2 из 3.")
