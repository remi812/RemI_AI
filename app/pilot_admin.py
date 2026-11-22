"""Operator commands. Run as python -m app.pilot_admin."""
import argparse
from pathlib import Path

from psycopg.types.json import Jsonb
from app.encoder import index_section
from app.main import PILOTS, read_pilot_graph
from app.pilot_content import KEY_SKILLS, SECTIONS, questions_for
from app.pilot_db import open_database

DATABASE = Path(__file__).resolve().parents[1] / "database"


def seed(db, slugs):
    for slug in slugs:
        nodes, _, _ = read_pilot_graph(PILOTS[slug])
        ids = {n["name"]: n["competency_id"] for n in nodes}
        if not all(name in ids for name in KEY_SKILLS[slug]):
            raise ValueError(f"Неполный граф {slug}")
        for name, skill in ids.items():
            for phase in ("initial", "retake"):
                for idx, (kind, text, key, options) in enumerate(questions_for(name, phase)):
                    existing = db.execute("""SELECT question_id FROM questions WHERE competency_id=%s
                        AND question_text=%s AND pilot_phase=%s""", (skill,text,phase)).fetchone()
                    if existing:
                        continue
                    rule = {"numeric":"Числовое равенство с допуском 0,000001.",
                            "choice":"Совпадение с одним вариантом.",
                            "short_text":"Одно слово из ключа, без учёта регистра и внешних пробелов."}[kind]
                    qid = db.execute("""INSERT INTO questions(competency_id, question_text,answer_type,
                        expected_answer,validation_status,pilot_phase,difficulty,evaluation_rules,numeric_tolerance)
                        VALUES (%s,%s,%s,%s,'pending',%s,%s,%s,%s) RETURNING question_id""",
                        (skill,text,kind,key,phase,[2,1,3][idx],rule,0.000001 if kind=="numeric" else None)).fetchone()["question_id"]
                    for option in options or []:
                        db.execute("INSERT INTO question_options(question_id,option_text) VALUES (%s,%s)",(qid,option))
                    db.execute("""INSERT INTO question_versions(question_id,version_number,competency_id,
                        answer_type,question_text,expected_answer,evaluation_rules,numeric_tolerance,options_snapshot)
                        SELECT question_id,1,competency_id,answer_type,question_text,expected_answer,
                        evaluation_rules,numeric_tolerance,%s FROM questions WHERE question_id=%s""",
                        (Jsonb(options) if options else None,qid))
        for (course, course_url), title, url, description, skills in SECTIONS[slug]:
            parent = db.execute("""SELECT r.resource_id FROM learning_resources r LEFT JOIN course_sections s
                USING(resource_id) WHERE r.url=%s AND s.resource_id IS NULL ORDER BY r.resource_id LIMIT 1""",(course_url,)).fetchone()
            if not parent:
                parent = db.execute("""INSERT INTO learning_resources(title,url,resource_type)
                    VALUES (%s,%s,'учебник') RETURNING resource_id""",(course,course_url)).fetchone()
            section = db.execute("""SELECT resource_id FROM course_sections JOIN learning_resources USING(resource_id)
                WHERE course_id=%s AND title=%s""",(parent["resource_id"],title)).fetchone()
            if not section:
                section = db.execute("""INSERT INTO learning_resources(title,url,description,resource_type,
                    language,access_type,link_checked_at) VALUES (%s,%s,%s,'раздел','русский','открытая страница',
                    DATE '2026-11-22') RETURNING resource_id""",(title,url,description)).fetchone()
                db.execute("INSERT INTO course_sections(resource_id,course_id) VALUES (%s,%s)",
                           (section["resource_id"],parent["resource_id"]))
            for name in skills:
                db.execute("INSERT INTO competency_resources VALUES (%s,%s) ON CONFLICT DO NOTHING",
                           (ids[name],section["resource_id"]))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["init","migrate","seed","index","moderator"])
    parser.add_argument("--route", choices=list(SECTIONS))
    parser.add_argument("--student-id", type=int)
    args = parser.parse_args()
    with open_database() as db:
        if args.command in ("init","migrate"):
            # SQL scripts own their transactions. Never replay the baseline on an existing schema.
            db.autocommit = True
            exists = db.execute("SELECT to_regnamespace('remi_project') AS schema").fetchone()["schema"]
            if args.command == "init" and exists:
                parser.error("init требует пустую базу")
            versions = [1,3,5,6,7,8,9,17,18] if args.command=="init" else [18]
            for version in versions:
                path, = DATABASE.glob(f"{version:02}_*.sql")
                db.execute(path.read_text(encoding="utf-8-sig"))
                print(path.name)
            db.autocommit = False
        if args.command in ("init","migrate","seed"):
            db.execute("SELECT pg_advisory_xact_lock(73642,18)")
            seed(db,[args.route] if args.route else SECTIONS)
        elif args.command == "index":
            for row in db.execute("SELECT resource_id FROM course_sections").fetchall():
                index_section(db,row["resource_id"])
        elif args.command == "moderator":
            result = db.execute("""INSERT INTO moderators(student_id,display_name,email)
                SELECT student_id,display_name,email FROM students WHERE student_id=%s AND password_hash IS NOT NULL
                ON CONFLICT(student_id) DO NOTHING RETURNING moderator_id""",(args.student_id,)).fetchone()
            if not result:
                parser.error("Профиль отсутствует или роль уже назначена")


if __name__ == "__main__":
    main()

