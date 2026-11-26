"""Opt-in checks on seeded disposable databases. Roll back all review and profile changes."""
import math
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from app.accounts import database
from app.encoder import encode, encoder
from app.main import app
from app.pilot_content import LOOP
from app.pilot_db import open_database
from pilot_acceptance import NOTE, checked, profile


def cosine(a, b):
    return sum(x*y for x,y in zip(a,b)) / (math.sqrt(sum(x*x for x in a))*math.sqrt(sum(y*y for y in b)))


def verify(db):
    student,_ = profile("Проверка ветки")
    outsider,_ = profile("Второй профиль")
    mod,auth = profile("Проверка модерации")
    mid = db.execute("""INSERT INTO moderators(student_id,email,display_name)
        SELECT student_id,email,display_name FROM students WHERE email=%s RETURNING moderator_id""",
        (auth["email"],)).fetchone()["moderator_id"]
    graph = checked(student.get("/api/learn/control/preview"))
    skill = next(n for n in graph["nodes"] if n["name"] == LOOP)
    url = f"/api/learn/control/skills/{skill['competency_id']}/materials"
    sections = db.execute("""SELECT r.resource_id,r.title,s.vector FROM competency_resources cr
        JOIN course_sections s USING(resource_id) JOIN learning_resources r USING(resource_id)
        WHERE competency_id=%s AND r.review_status='approved' ORDER BY r.resource_id""",(skill["competency_id"],)).fetchall()
    assert len(sections)==2
    query = encode(f"{graph['goal']}. {skill['name']}. {skill['description']}").tolist()
    scores = [(cosine(query,s["vector"]),s["title"]) for s in sections]
    semantic = checked(student.get(url))
    assert semantic["mode"]=="semantic"
    assert [i["title"] for i in semantic["items"]]==[name for _,name in sorted(scores,reverse=True)]
    # An actually missing model with the production inference cache initially empty.
    with TemporaryDirectory() as folder, patch.dict(os.environ, REMI_MODEL_DIR=str(Path(folder)/"absent")):
        encode.cache_clear()
        encoder.cache_clear()
        fallback = checked(student.get(url))
    assert fallback["mode"]=="links"
    assert [i["title"] for i in fallback["items"]]==[s["title"] for s in sections]
    assert fallback["items"][0]["title"] != semantic["items"][0]["title"]
    for score,name in sorted(scores,reverse=True):
        print(f"{score:.6f}  {name}")
    print("По связям:", [i["title"] for i in fallback["items"]])

    decision = {"decision":"rejected","note":NOTE}
    start = checked(student.post("/api/learn/control/start",json={}))
    sid = start["session_id"]
    q = start["question"]
    assert set(q)=={"question_version_id","question_text","answer_type","options_snapshot"}
    payload = {"version":q["question_version_id"],"value":"0"}
    answer_url = f"/api/learn/sessions/{sid}/answer"
    assert outsider.post(answer_url,json=payload).status_code==404
    assert outsider.post(f"/api/learn/sessions/{sid}/stop",json={}).status_code==404
    assert not checked(outsider.get("/api/learn/control/progress"))["history"]
    assert checked(student.get("/api/learn/control/progress"))["history"][0]["session_id"]==sid
    review = f"/api/review/questions/{payload['version']}"
    assert outsider.get("/api/review").status_code==403
    assert outsider.post(review,json=decision).status_code==403
    checked(mod.post(review,json=decision))
    assert student.post(answer_url,json=payload).status_code==409
    fresh = checked(student.post("/api/learn/control/start",json={}))
    assert fresh["question"]["question_version_id"]!=payload["version"]
    assert not db.execute("SELECT 1 FROM student_answers WHERE session_id=%s",(sid,)).fetchone()
    log = db.execute("""SELECT decision,details FROM question_reviews WHERE question_version_id=%s
        AND moderator_id=%s ORDER BY review_id""",(payload["version"],mid)).fetchall()
    assert log==[{"decision":"rejected","details":NOTE}]
    for section in sections:
        endpoint = f"/api/review/sections/{section['resource_id']}"
        checked(mod.post(endpoint,json=decision))
    assert checked(student.get(url))=={"mode":"empty","items":[]}
    section = sections[0]["resource_id"]
    checked(mod.post(f"/api/review/sections/{section}",json={"decision":"approved","note":NOTE}))
    items = checked(student.get(url))["items"]
    assert [i["title"] for i in items]==[sections[0]["title"]]
    log = db.execute("""SELECT decision,details FROM resource_reviews WHERE resource_id=%s
        AND moderator_id=%s ORDER BY review_id""",(section,mid)).fetchall()
    assert log==[{"decision":decision,"details":NOTE} for decision in ("rejected","approved")]
    print("Журналы и повторный допуск, отзыв выданной версии, разделение профилей — OK")


if __name__=="__main__":
    if not os.getenv("PGDATABASE","").endswith("_demo"):
        raise SystemExit("Укажите отдельную базу *_demo")
    with open_database() as db, db.transaction(force_rollback=True):
        assert db.info.dbname==os.environ["PGDATABASE"]
        app.dependency_overrides[database] = lambda: db
        try:
            verify(db)
        finally:
            del app.dependency_overrides[database]

