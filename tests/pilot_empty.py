"""Regression checks before approving any content on a new *_demo installation."""
from unittest.mock import patch

from app.encoder import recommend
from app.main import get_pilot_graph
from app.pilot_db import open_database
from app.pilot_content import ERROR
from pilot_acceptance import profile, checked


def main():
    with open_database() as db:
        assert db.info.dbname.endswith("_demo")
        assert not db.execute("SELECT 1 FROM approved_pilot_questions LIMIT 1").fetchone()
    client,_ = profile("Пустой банк")
    assert not checked(client.get("/api/learn/control/preview"))["availability"]["available"]
    assert client.post("/api/learn/control/start",json={}).status_code == 409
    progress = checked(client.get("/api/learn/control/progress"))
    assert not progress["history"]
    assert all(r["knowledge_status"]=="not_assessed" for r in progress["results"].values())
    config,nodes,_edges,_resources = get_pilot_graph("control")
    node = next(n for n in nodes if n["name"]==ERROR)
    url = f"/api/learn/control/skills/{node['competency_id']}/materials"
    assert checked(client.get(url))=={"mode":"empty","items":[]}
    with open_database() as db, db.transaction(force_rollback=True):
        row = db.execute("""SELECT r.resource_id FROM course_sections s JOIN learning_resources r USING(resource_id)
            JOIN competency_resources cr USING(resource_id) WHERE cr.competency_id=%s LIMIT 1""",(node["competency_id"],)).fetchone()
        rid = row["resource_id"]
        db.execute("UPDATE learning_resources SET review_status='approved' WHERE resource_id=%s",(rid,))
        from app.encoder import index_section
        index_section(db,rid)
        def get():
            return recommend(db,config["goal"],node,"Требует уточнения",0,1)
        assert get()["mode"]=="semantic"
        with patch("app.encoder.encode",side_effect=FileNotFoundError):
            assert get()["mode"]=="links" and get()["items"]
        db.execute("UPDATE learning_resources SET access_type='уточнить' WHERE resource_id=%s",(rid,))
        assert get()["mode"]=="empty"
        db.execute("UPDATE learning_resources SET access_type='открытая страница',language='en' WHERE resource_id=%s",(rid,))
        assert get()["mode"]=="empty"
    print("Пустой банк, неопределённость, фильтры допуска, языка и доступа, резервный подбор — OK")


if __name__=="__main__":
    main()

