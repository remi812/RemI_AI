"""Transactional selection and scoring against reviewed snapshots in PostgreSQL."""
import os
import random
from app.availability import inventory
from collections import defaultdict, deque
from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, Depends, HTTPException
from psycopg.types.json import Jsonb
from pydantic import BaseModel, Field

from app.accounts import DB, owner
from app.encoder import recommend
from app.pilot_content import KEY_SKILLS

router = APIRouter(prefix="/api/learn")
LABELS = {"mastered":"Предварительно освоено","possible_gap":"Вероятный пробел",
          "not_assessed":"Не проверено","needs_review":"Требует уточнения"}


def graph(slug,db=None):
    from app.main import get_pilot_graph
    if slug not in KEY_SKILLS:
        raise HTTPException(404,"Адаптивный маршрут пока не подготовлен.")
    if db is not None:
        from app.catalog_routes import PILOTS
        from app.main import read_pilot_graph
        config = PILOTS[slug]
        nodes,edges,_ = read_pilot_graph(config,db,resources=False)
        if not nodes:
            raise HTTPException(503,"Карта пока недоступна.")
    else:
        config,nodes,edges,_ = get_pilot_graph(slug,catalog=True)
    return config,nodes,edges


def rules():
    return {k: max(low,min(high,int(os.getenv("REMI_"+k.upper(),default))))
            for k,default,low,high in [("votes",2,2,6),("depth",3,0,10),("limit",20,1,100)]}


def status(answers, votes):
    if not answers:
        return "not_assessed"
    good = sum(a["is_correct"] for a in answers)
    if good >= votes:
        return "mastered"
    return "possible_gap" if len(answers)-good >= votes else "needs_review"


def grade(q, value):
    value = value.strip()
    if not value:
        raise HTTPException(422,"Введите ответ.")
    if q["answer_type"]=="choice":
        if value not in q["options_snapshot"]:
            raise HTTPException(422,"Выберите один из предложенных вариантов.")
        return value==q["expected_answer"]
    if q["answer_type"]=="short_text":
        return value.casefold() in [x.strip().casefold() for x in q["expected_answer"].split("|")]
    try:
        number = Decimal(value.replace(",",".").replace("−","-"))
        if not number.is_finite() or abs(number.adjusted())>300:
            raise ValueError
        return abs(number-Decimal(q["expected_answer"])) <= (q["numeric_tolerance"] or 0)
    except (InvalidOperation,ValueError):
        raise HTTPException(422,"Введите конечное число, например −1,5.") from None


def lock_owner(db, uid):
    db.execute("SELECT student_id FROM students WHERE student_id=%s FOR UPDATE",(uid,))


def session(db, uid, sid):
    row = db.execute("""SELECT * FROM diagnostic_sessions WHERE student_id=%s AND session_id=%s
                        AND pilot_slug IS NOT NULL FOR UPDATE""",(uid,sid)).fetchone()
    if not row:
        raise HTTPException(404,"Проверка не найдена.")
    return row


def evidence(db,sid):
    by_skill = defaultdict(list)
    for a in db.execute("""SELECT a.answer_id,a.is_correct,v.competency_id FROM student_answers a
            JOIN question_versions v USING(question_version_id) WHERE session_id=%s ORDER BY answer_id""",(sid,)):
        by_skill[a["competency_id"]].append(a)
    return by_skill


def planned(s,nodes,edges,answers):
    ids = {n["name"]:n["competency_id"] for n in nodes}
    parents = defaultdict(list)
    for edge in edges:
        parents[edge["competency_id"]].append(edge["prerequisite_id"])
    cfg = s["pilot_rules"]
    ordered = []
    def visit(skill,depth):
        if skill not in ordered:
            ordered.append(skill)
        if depth < cfg["depth"] and status(answers[skill],cfg["votes"])=="possible_gap":
            for parent in sorted(parents[skill]):
                visit(parent,depth+1)
    if s["retake_skill"]:
        return [s["retake_skill"]]
    for key in KEY_SKILLS[s["pilot_slug"]]:
        visit(ids[key],0)
    return ordered


def finish(db,s,answers,skills,reason):
    sid,uid = s["session_id"],s["student_id"]
    db.execute("""UPDATE diagnostic_sessions SET status=%s,finished_at=clock_timestamp(),stop_reason=%s
                  WHERE session_id=%s""",("stopped" if reason=="student" else "completed",reason,sid))
    for skill in skills:
        rows = answers[skill]
        score = sum(a["is_correct"] for a in rows)/len(rows) if rows else None
        estimate = db.execute("""INSERT INTO mastery_estimates(student_id,competency_id,session_id,
            mastery_score,knowledge_status,algorithm_version,explanation) VALUES (%s,%s,%s,%s,%s,'adaptive-v1',%s)
            RETURNING estimate_id""",(uid,skill,sid,score,status(rows,s["pilot_rules"]["votes"]),reason)).fetchone()
        for row in rows:
            db.execute("INSERT INTO estimate_evidence VALUES (%s,%s)",(estimate["estimate_id"],row["answer_id"]))
    return {"session_id":sid,"done":True,"reason":reason}


def advance(db,s,stop=False):
    sid,uid = s["session_id"],s["student_id"]
    if s["status"]!="in_progress":
        return {"session_id":sid,"done":True,"reason":s["stop_reason"]}
    _,nodes,edges = graph(s["pilot_slug"],db)
    answers = evidence(db,sid)
    skills = planned(s,nodes,edges,answers)
    if stop:
        return finish(db,s,answers,skills,"student")
    db.execute("""UPDATE pilot_issues i SET withdrawn=true WHERE session_id=%s AND answer_id IS NULL
        AND NOT EXISTS (SELECT 1 FROM approved_pilot_questions q WHERE q.question_version_id=i.question_version_id)""",(sid,))
    q = db.execute("""SELECT q.* FROM pilot_issues i JOIN approved_pilot_questions q USING(question_version_id)
        WHERE session_id=%s AND answer_id IS NULL AND NOT withdrawn""",(sid,)).fetchone()
    if not q:
        count = db.execute("SELECT count(*) AS n FROM pilot_issues WHERE session_id=%s",(sid,)).fetchone()["n"]
        missing = False
        for skill in skills:
            rows = answers[skill]
            if status(rows,s["pilot_rules"]["votes"]) in ("mastered","possible_gap"):
                continue
            if count >= s["pilot_rules"]["limit"]:
                return finish(db,s,answers,skills,"limit")
            difficulty = 2 if not rows else (3 if rows[-1]["is_correct"] else 1)
            q = db.execute("""SELECT q.* FROM approved_pilot_questions q WHERE competency_id=%s
                AND pilot_phase=%s AND NOT EXISTS (SELECT 1 FROM pilot_issues i
                WHERE i.student_id=%s AND i.question_id=q.question_id)
                ORDER BY abs(difficulty-%s),question_id LIMIT 1""",
                (skill,"retake" if s["retake_skill"] else "initial",uid,difficulty)).fetchone()
            if q:
                db.execute("""INSERT INTO pilot_issues(session_id,student_id,question_id,question_version_id)
                    VALUES (%s,%s,%s,%s)""",(sid,uid,q["question_id"],q["question_version_id"]))
                break
            missing = True
        if not q:
            return finish(db,s,answers,skills,"exhausted" if missing else "sufficient")
    public = {k:q[k] for k in ("question_version_id","question_text","answer_type","options_snapshot")}
    if public["options_snapshot"]:
        public["options_snapshot"] = list(public["options_snapshot"])
        random.Random(f"{uid}-{sid}-{q['question_version_id']}").shuffle(public["options_snapshot"])
    return {"session_id":sid,"done":False,"question":public}


class Start(BaseModel):
    skill: int | None = None


class Answer(BaseModel):
    version: int
    value: str = Field(min_length=1,max_length=256)


@router.get("/{slug}/preview")
def preview(slug: str,db=DB):
    config,nodes,edges = graph(slug,db)
    return {**config,"nodes":nodes,"edges":edges, "availability":inventory(db,slug,nodes,edges,KEY_SKILLS[slug],rules()["votes"]),
            "synthetic":os.getenv("PGDATABASE","").endswith("_demo")}


@router.post("/{slug}/start")
def start(slug: str,data: Start,person=Depends(owner),db=DB):
    uid = person["student_id"]
    lock_owner(db,uid)
    cfg,nodes,edges = graph(slug,db)
    goal = next(n["competency_id"] for n in nodes if n["name"]==cfg["goal"])
    if data.skill is not None and data.skill not in [n["competency_id"] for n in nodes]:
        raise HTTPException(422,"Навык вне маршрута.")
    active = db.execute("""SELECT * FROM diagnostic_sessions WHERE student_id=%s AND pilot_slug=%s
                           AND status='in_progress'""",(uid,slug)).fetchone()
    if active and active["retake_skill"]!=data.skill:
        raise HTTPException(409,"Сначала завершите текущую проверку.")
    if data.skill and not db.execute("""SELECT 1 FROM diagnostic_sessions WHERE student_id=%s
            AND pilot_slug=%s AND retake_skill IS NULL AND status<>'in_progress'""",(uid,slug)).fetchone():
        raise HTTPException(409,"Сначала пройдите начальную диагностику.")
    if not active:
        capacity = inventory(db,slug,nodes,edges,KEY_SKILLS[slug],rules()["votes"],uid)
        if not capacity["available"]:
            raise HTTPException(409,"Диагностика ожидает допуска. Доступен обзор карты.")
        if not (capacity["remaining"][data.skill]["retake"] if data.skill else capacity["initial_remaining"]):
            return {"session_id":None,"done":True,"reason":"exhausted"}
        active = db.execute("""INSERT INTO diagnostic_sessions(student_id,pilot_slug,target_competency_id,
            status,retake_skill,pilot_rules) VALUES (%s,%s,%s,'in_progress',%s,%s) RETURNING *""",
            (uid,slug,goal,data.skill,Jsonb(rules()))).fetchone()
    return advance(db,active)


@router.post("/sessions/{sid}/answer")
def answer(sid:int,data: Answer,person=Depends(owner),db=DB):
    uid = person["student_id"]
    lock_owner(db,uid)
    s = session(db,uid,sid)
    previous = db.execute("""SELECT a.is_correct,a.answer_text FROM pilot_issues i
        JOIN student_answers a USING(answer_id) WHERE i.session_id=%s AND i.question_version_id=%s""",
        (sid,data.version)).fetchone()
    if previous and previous["answer_text"]==data.value:
        return {"correct":previous["is_correct"],**advance(db,s)}
    db.execute("""SELECT q.question_id FROM questions q JOIN pilot_issues i USING(question_id)
        WHERE i.session_id=%s AND i.question_version_id=%s FOR SHARE OF q""",(sid,data.version))
    q = db.execute("""SELECT q.* FROM pilot_issues i JOIN approved_pilot_questions q USING(question_version_id)
        WHERE i.session_id=%s AND i.question_version_id=%s AND i.answer_id IS NULL AND NOT i.withdrawn
        FOR SHARE OF i""",(sid,data.version)).fetchone()
    if not q or s["status"]!="in_progress":
        raise HTTPException(409,"Вопрос уже изменился. Обновите проверку.")
    correct = grade(q,data.value)
    aid = db.execute("""INSERT INTO student_answers(session_id,question_id,question_version_id,answer_text,
        is_correct,grading_method,grading_details) VALUES (%s,%s,%s,%s,%s,'automatic',%s) RETURNING answer_id""",
        (sid,q["question_id"],data.version,data.value,correct,q["evaluation_rules"])).fetchone()["answer_id"]
    db.execute("UPDATE pilot_issues SET answer_id=%s WHERE session_id=%s AND question_version_id=%s",(aid,sid,data.version))
    return {"correct":correct,**advance(db,s)}


@router.post("/sessions/{sid}/stop")
def stop(sid:int,person=Depends(owner),db=DB):
    lock_owner(db,person["student_id"])
    return advance(db,session(db,person["student_id"],sid),stop=True)


def study_steps(goal, key_skills, edges, latest):
    """Order unfinished skills by prerequisites; keep one illustrative path to the goal."""
    parents = defaultdict(list)
    for edge in edges:
        parents[edge["competency_id"]].append(edge["prerequisite_id"])

    paths = {goal: [goal]}
    queue = deque([goal])
    while queue:
        child = queue.popleft()
        for parent in sorted(parents[child]):
            if parent not in paths:
                paths[parent] = [parent, *paths[child]]
                queue.append(parent)

    ranks = {"possible_gap": 0, "needs_review": 1, "not_assessed": 2}
    states = {skill: latest.get(skill, {}).get("knowledge_status", "not_assessed")
              for skill in paths}
    pending = {skill for skill, state in states.items()
               if state in ranks and (state != "not_assessed" or skill in key_skills)}
    # A shared prerequisite may sit on a different path from the one shown to the student.
    ancestors = {}
    def prerequisites(skill):
        if skill not in ancestors:
            found = set(parents[skill])
            for parent in parents[skill]:
                found.update(prerequisites(parent))
            ancestors[skill] = found
        return ancestors[skill]

    steps = []
    while pending:
        ready = (skill for skill in pending if pending.isdisjoint(prerequisites(skill)))
        skill = min(ready, key=lambda k: (ranks[states[k]], -len(paths[k]), k))
        steps.append({"skill": skill, "status": states[skill], "path": paths[skill]})
        pending.remove(skill)
    return steps


def profile_estimates(db,uid,ids):
    estimates = db.execute("""SELECT e.competency_id,e.estimate_id,s.pilot_slug,e.knowledge_status,e.session_id,
        count(a.answer_id)::int AS total,count(a.answer_id) FILTER (WHERE a.is_correct)::int AS correct
        FROM mastery_estimates e JOIN diagnostic_sessions s USING(session_id,student_id)
        LEFT JOIN estimate_evidence ev USING(estimate_id) LEFT JOIN student_answers a USING(answer_id)
        WHERE e.student_id=%s AND s.pilot_slug IS NOT NULL AND e.competency_id=ANY(%s) GROUP BY e.estimate_id,s.pilot_slug ORDER BY e.estimate_id""",(uid,ids)).fetchall()
    latest = {}
    for row in estimates:
        skill = row["competency_id"]
        sufficient = row["knowledge_status"] in ("mastered","possible_gap")
        prior = latest.get(skill)
        if not prior or sufficient or (prior["knowledge_status"] not in ("mastered","possible_gap") and row["total"]):
            latest[skill] = row
    return estimates,latest


@router.get("/{slug}/progress")
def progress(slug:str,person=Depends(owner),db=DB):
    cfg,nodes,edges = graph(slug,db)
    uid = person["student_id"]
    history = db.execute("""SELECT s.session_id,s.started_at,s.status,s.stop_reason,s.retake_skill,
        c.name AS skill FROM diagnostic_sessions s LEFT JOIN competencies c ON c.competency_id=s.retake_skill
        WHERE student_id=%s AND pilot_slug=%s ORDER BY s.session_id DESC""",(uid,slug)).fetchall()
    estimates, latest = profile_estimates(db,uid,[n["competency_id"] for n in nodes])
    by_session = defaultdict(list)
    for row in estimates:
        if row["pilot_slug"] == slug:
            by_session[row["session_id"]].append(row)
    for s in history:
        s["estimates"] = by_session[s["session_id"]]
    ids = {n["name"]:n["competency_id"] for n in nodes}
    steps = study_steps(ids[cfg["goal"]], {ids[k] for k in KEY_SKILLS[slug]}, edges, latest)
    return {"availability":inventory(db,slug,nodes,edges,KEY_SKILLS[slug],rules()["votes"],uid), "history": history, "results": latest, "steps": steps,
            "next": steps[0]["skill"] if steps else None}


@router.get("/{slug}/skills/{skill}/materials")
def materials(slug:str,skill:int,person=Depends(owner),db=DB):
    cfg,nodes,edges = graph(slug,db)
    node = next((n for n in nodes if n["competency_id"]==skill),None)
    if not node:
        raise HTTPException(404,"Навык не найден.")
    _, latest = profile_estimates(db,person["student_id"],[skill])
    row = latest.get(skill,{})
    return recommend(db,cfg["goal"],node,LABELS[row.get("knowledge_status","not_assessed")],
                     row.get("correct",0),row.get("total",0))

