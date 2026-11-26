import hashlib
import json


def fingerprint(slug, nodes, edges, keys):
    graph = [slug, keys, sorted((n["competency_id"], n["name"], n["description"]) for n in nodes),
             sorted((e["competency_id"], e["prerequisite_id"]) for e in edges)]
    return hashlib.sha256(json.dumps(graph,ensure_ascii=False).encode()).hexdigest()


def inventory(db, slug, nodes, edges, keys, votes, uid=None):
    ids = [n["competency_id"] for n in nodes]
    signature = fingerprint(slug,nodes,edges,keys)
    review = db.execute("""SELECT approved FROM graph_reviews WHERE slug=%s AND fingerprint=%s
        ORDER BY review_id DESC LIMIT 1""",(slug,signature)).fetchone()
    rows = db.execute("""SELECT q.competency_id,q.pilot_phase,count(*) AS bank,
        count(*) FILTER (WHERE i.question_id IS NULL) AS remaining FROM approved_pilot_questions q
        LEFT JOIN pilot_issues i ON i.question_id=q.question_id AND i.student_id=%s
        WHERE q.competency_id=ANY(%s) GROUP BY 1,2""",(uid,ids)).fetchall()
    materials = {r["competency_id"] for r in db.execute("""SELECT DISTINCT cr.competency_id FROM competency_resources cr
        JOIN course_sections s USING(resource_id) JOIN learning_resources r USING(resource_id)
        JOIN learning_resources c ON c.resource_id=s.course_id WHERE cr.competency_id=ANY(%s)
        AND r.review_status='approved' AND c.review_status<>'rejected' AND r.language='русский'
        AND r.access_type='открытая страница' AND r.url LIKE 'https://%%'""",(ids,))}
    bank = {(r["competency_id"],r["pilot_phase"]):r for r in rows}
    complete = all(bank.get((i,p),{}).get("bank",0)>=2*votes-1 for i in ids for p in ("initial","retake"))
    ready = bool(review and review["approved"] and complete and set(ids)<=materials)
    remaining = {i:{p:bank.get((i,p),{}).get("remaining",0) for p in ("initial","retake")} for i in ids}
    return {"available":ready,"initial_remaining":sum(remaining[n["competency_id"]]["initial"] for n in nodes if n["name"] in keys),
            "remaining":remaining,"material_skills":sorted(materials),"fingerprint":signature}
