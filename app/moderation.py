from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.accounts import DB, moderator
from app.encoder import index_section

router = APIRouter(prefix="/api/review",dependencies=[Depends(moderator)])


@router.get("")
def inventory(db=DB):
    questions = db.execute("""SELECT DISTINCT ON(q.question_id) v.question_version_id AS id,v.version_number,
        q.pilot_phase,c.name AS skill,v.question_text AS title,v.expected_answer,v.options_snapshot,
        v.evaluation_rules,q.validation_status AS status FROM questions q JOIN question_versions v USING(question_id)
        JOIN competencies c ON c.competency_id=v.competency_id WHERE q.pilot_phase IS NOT NULL
        ORDER BY q.question_id,v.version_number DESC""").fetchall()
    sections = db.execute("""SELECT r.resource_id AS id,c.title AS course,r.title,r.url,r.description,
        r.review_status AS status,r.language,r.access_type,r.link_checked_at,
        ARRAY(SELECT k.name FROM competency_resources cr JOIN competencies k USING(competency_id)
        WHERE cr.resource_id=r.resource_id ORDER BY k.name) AS skills FROM course_sections s
        JOIN learning_resources r ON r.resource_id=s.resource_id JOIN learning_resources c ON c.resource_id=s.course_id
        ORDER BY c.title,r.title""").fetchall()
    return {"questions":questions,"sections":sections}


class Review(BaseModel):
    decision: Literal["approved","rejected","needs_review"]
    note: str = Field(max_length=1000)


@router.post("/{kind}/{item}")
def review(kind:Literal["questions","sections"],item:int,data:Review,mod=Depends(moderator),db=DB):
    status = "pending" if data.decision=="needs_review" else data.decision
    if kind=="questions":
        q = db.execute("""SELECT q.question_id FROM questions q JOIN question_versions v USING(question_id)
            WHERE question_version_id=%s AND q.pilot_phase IS NOT NULL AND v.version_number=(
            SELECT max(n.version_number) FROM question_versions n WHERE n.question_id=q.question_id)
            FOR UPDATE OF q""",(item,)).fetchone()
        if not q:
            raise HTTPException(404,"Версия не найдена.")
        db.execute("""INSERT INTO question_reviews(question_id,question_version_id,moderator_id,reviewer_type,
            decision,details) VALUES (%s,%s,%s,'expert',%s,%s)""",(q["question_id"],item,mod,data.decision,data.note))
        db.execute("UPDATE questions SET validation_status=%s WHERE question_id=%s",(status,q["question_id"]))
    else:
        row = db.execute("""UPDATE learning_resources r SET review_status=%s FROM course_sections s
            WHERE r.resource_id=s.resource_id AND r.resource_id=%s RETURNING r.resource_id""",(status,item)).fetchone()
        if not row:
            raise HTTPException(404,"Раздел не найден.")
        db.execute("INSERT INTO resource_reviews(resource_id,moderator_id,decision,details) VALUES (%s,%s,%s,%s)",
                   (item,mod,data.decision,data.note))
        db.execute("UPDATE course_sections SET vector=NULL,encoder=NULL WHERE resource_id=%s",(item,))
        if status=="approved":
            index_section(db,item)
    return {"status":status}


class GraphReview(BaseModel):
    fingerprint: str = Field(min_length=64,max_length=64)
    approved: bool


@router.post("/graph/{slug}/decision")
def decide_graph(slug:str,data:GraphReview,mod=Depends(moderator),db=DB):
    from app.adaptive import graph, KEY_SKILLS
    from app.availability import fingerprint
    _,nodes,edges = graph(slug,db)
    current = fingerprint(slug,nodes,edges,KEY_SKILLS[slug])
    if current != data.fingerprint:
        raise HTTPException(409,"Карта изменилась. Обновите страницу и проверьте связи.")
    db.execute("INSERT INTO graph_reviews(slug,fingerprint,moderator_id,approved) VALUES (%s,%s,%s,%s)",
               (slug,current,mod,data.approved))
    return {"approved":data.approved}


@router.get("/metrics")
def metrics(db=DB):
    from app.operations import counts,lock,resident_bytes
    with lock:
        result = dict(counts)
    result["resident_bytes"] = resident_bytes()
    result["database_connections"] = db.execute(
        "SELECT count(*) AS n FROM pg_stat_activity WHERE datname=current_database()").fetchone()["n"]
    result["exhausted_sessions"] = db.execute(
        "SELECT count(*) AS n FROM diagnostic_sessions WHERE stop_reason='exhausted'").fetchone()["n"]
    return result
