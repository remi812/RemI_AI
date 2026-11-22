"""Evaluate ranking independently of the skill links that protect the student-facing catalogue."""
import math
import re
from collections import Counter

import numpy as np

from app.encoder import MODEL_ID, encode
from app.pilot_db import open_database

# Labels refer to independently inspected section titles. Fixed before the first run.
SIGN = "1.2.3. Принцип обратной связи"
OPEN = "1.2.1. Принцип разомкнутого управления"
INTRO = "Введение перед первой лекцией"
SUM = "Как найти производную? Правило суммы"
LIMIT = "Пределы функций. Примеры решений"
FOR = "Цикл for. Функция range"
IF = "Условия. Операторы сравнения"
INPUT = "Ввод и вывод данных"
LABELS = [
    ("Как узнать знак рассогласования, если фактическая температура выше требуемой?", {SIGN}),
    ("Что подаётся на вход регулятора при вычитании показаний датчика из уставки?", {SIGN}),
    ("Как отличить нагрев по расписанию от термостата?", {OPEN,INTRO}),
    ("Полив включается на пять минут. Замкнут ли такой контур по влажности?", {OPEN,INTRO}),
    ("Как дифференцировать несколько слагаемых с постоянными коэффициентами?", {SUM}),
    ("Найти наклон касательной к графику полинома в точке", {SUM}),
    ("К чему приближается частное при стремлении аргумента к заданному числу?", {LIMIT}),
    ("Как вычислять пределы функций подстановкой?", {LIMIT}),
    ("Сколько проходов сделает for по диапазону с шагом три?", {FOR}),
    ("Правая граница range включается при переборе?", {FOR}),
    ("Как выполнить одну команду при истинном сравнении и другую в противном случае?", {IF}),
    ("Как превратить строку из input в целое число?", {INPUT}),
]


def words(text):
    return Counter(re.findall(r"[а-яёa-z0-9]+",text.casefold()))


def evaluate():
    with open_database() as db:
        rows = db.execute("""SELECT r.title,r.description,s.encoder,s.vector FROM learning_resources r
            JOIN course_sections s USING(resource_id) JOIN learning_resources parent ON parent.resource_id=s.course_id
            WHERE r.review_status='approved' AND parent.review_status<>'rejected'
            AND r.language='русский' AND r.access_type='открытая страница' ORDER BY r.resource_id""").fetchall()
    assert rows and all(r["encoder"]==MODEL_ID and r["vector"] for r in rows),"Сначала индексируйте допущенные разделы."
    titles = [r["title"] for r in rows]
    docs = [words(r["title"]+" "+r["description"]) for r in rows]
    vectors = np.asarray([r["vector"] for r in rows])
    scores = {"MiniLM":[],"TF-IDF":[]}
    for query,labels in LABELS:
        assert labels <= set(titles),labels
        bag = words(query)
        def weights(b):
            return {t:n*(1+math.log((1+len(docs))/(1+sum(t in d for d in docs)))) for t,n in b.items()}
        query_weights = weights(bag)
        def lexical(doc):
            doc_weights = weights(doc)
            norm = math.sqrt(sum(v*v for v in query_weights.values())*sum(v*v for v in doc_weights.values()))
            return sum(v*doc_weights.get(t,0) for t,v in query_weights.items())/norm if norm else 0
        for name,sim in [("MiniLM",vectors@encode(query)),("TF-IDF",[lexical(d) for d in docs])]:
            ranked = np.argsort(-np.array(sim),kind="stable")
            rank = next(i for i,idx in enumerate(ranked,1) if titles[idx] in labels)
            scores[name].append(rank)
            if rank!=1: print(name,query,"→",titles[ranked[0]],"| ранг",rank)
    print(len(rows),"разделов,",len(LABELS),"запросов")
    for name,ranks in scores.items():
        print(name,"Hit@1",sum(r==1 for r in ranks),"/",len(ranks),"MRR",round(np.mean([1/r for r in ranks]),3))


if __name__=="__main__":
    evaluate()

