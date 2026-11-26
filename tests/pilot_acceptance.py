"""Opt-in integration check on a dedicated *_demo database. Never grants real subject approval."""
import argparse
import secrets
import uuid

from fastapi.testclient import TestClient
from app.main import app
from app.pilot_content import ERROR, LOOP, KEY_SKILLS
from app.pilot_db import open_database

NOTE = "Имитированное решение для вымышленных студентов. Предметная экспертиза ожидается."


def checked(response):
    assert response.is_success, (response.status_code,response.text)
    return response.json()


def profile(prefix):
    client = TestClient(app)
    auth = {"email":f"pilot-{uuid.uuid4().hex}@example.invalid","alias":prefix,"password":secrets.token_urlsafe(20)}
    checked(client.post("/api/account/register",json=auth))
    return client,auth


def synthetic_reviews():
    with open_database() as db:
        if not db.info.dbname.endswith("_demo"):
            raise RuntimeError("Применять тестовые допуски можно только в выделенной базе *_demo")
    mod,auth = profile("Тестовый модератор")
    with open_database() as db:
        db.execute("""INSERT INTO moderators(student_id,email,display_name)
            SELECT student_id,email,display_name FROM students WHERE email=%s""",(auth["email"],))
    content = checked(mod.get("/api/review"))
    for kind,items in content.items():
        for item in items:
            if item["status"]=="pending":
                checked(mod.post(f"/api/review/{kind}/{item['id']}",json={"decision":"approved","note":NOTE}))
    for slug in KEY_SKILLS:
        view = checked(mod.get(f"/api/learn/{slug}/preview"))
        checked(mod.post(f"/api/review/graph/{slug}/decision",json={
            "fingerprint":view["availability"]["fingerprint"],"approved":True}))
    return content


def run_quiz(client,slug,weak,skill=None):
    result = checked(client.post(f"/api/learn/{slug}/start",json={"skill":skill}))
    seen = []
    with open_database() as db:
        while not result["done"]:
            q = result["question"]
            assert "expected_answer" not in q
            version = q["question_version_id"]
            item = db.execute("""SELECT c.name,v.expected_answer FROM question_versions v
                                 JOIN competencies c USING(competency_id) WHERE question_version_id=%s""",(version,)).fetchone()
            correct = item["name"] not in weak
            value = item["expected_answer"].split("|")[0]
            if not correct:
                value = next((o for o in q["options_snapshot"] or [] if o!=value),"999" if q["answer_type"]=="numeric" else "пропуск")
            result = checked(client.post(f"/api/learn/sessions/{result['session_id']}/answer",json={"version":version,"value":value}))
            assert result["correct"]==correct
            seen.append(version)
    return seen,result


def verify(slug):
    students = []
    roles = [ERROR,LOOP] if slug=="control" else [KEY_SKILLS[slug][0]]
    for weak in roles:
        client,auth = profile("Участник")
        assert client.get("/api/review").status_code==403
        seen,result = run_quiz(client,slug,{weak})
        assert result["reason"]=="sufficient", result
        progress_url = f"/api/learn/{slug}/progress"
        progress = checked(client.get(progress_url))
        graph = checked(client.get(f"/api/learn/{slug}/preview"))
        target = next(n["competency_id"] for n in graph["nodes"] if n["name"]==weak)
        assert progress["next"]==target, (weak,progress)
        assert progress["results"][str(target)]["knowledge_status"]=="possible_gap"
        materials = checked(client.get(f"/api/learn/{slug}/skills/{target}/materials"))
        assert materials["mode"]=="semantic",materials
        pick = materials["items"][0]
        assert weak in pick["reason"] and "0 из 2" in pick["reason"]
        new,retake = run_quiz(client,slug,set(),target)
        assert len(new)>=2 and set(new).isdisjoint(seen)
        after = checked(client.get(progress_url))
        assert after["next"]!=target and after["results"][str(target)]["knowledge_status"]=="mastered"
        checked(client.post("/api/account/logout",json={}))
        assert client.get(progress_url).status_code==401
        checked(client.post("/api/account/login",json=auth))
        assert checked(client.get(progress_url))==after
        other,_ = profile("Другой участник")
        assert not checked(other.get(progress_url))["history"]
        assert other.post(f"/api/learn/sessions/{result['session_id']}/stop",json={}).status_code==404
        # No previously issued item can be shown, even in a new retake.
        last,exhausted = run_quiz(client,slug,set(),target)
        assert exhausted["reason"]=="exhausted" and set(last).isdisjoint(new+seen)
        students.append((seen,pick["title"]))
        print(slug,weak,"=>",pick["title"],"|",len(seen),"вопросов, повторная",len(new))
    if len(students)==2:
        a,b = students
        assert a[0][0]==b[0][0] and a[0][1]!=b[0][1] and a[1]!=b[1]


if __name__=="__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("routes",nargs="+",choices=list(KEY_SKILLS))
    args = parser.parse_args()
    synthetic_reviews()
    for slug in args.routes:
        verify(slug)


