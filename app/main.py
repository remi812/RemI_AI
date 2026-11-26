"""Каталог дисциплин RemI AI: HTTP-интерфейс и чтение из PostgreSQL."""

from contextlib import nullcontext
import logging
from pathlib import Path

import psycopg
from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from app.pilot_db import open_database
from app.catalog_routes import PILOTS as CATALOG_ROUTES
from app import accounts, adaptive, moderation
from pydantic import BaseModel

from app.derivatives import GOAL, QUESTIONS, RETAKE_QUESTIONS, evaluate, public_questions
from app.derivative_resources import add_curated
from app.encoder import recommend


BASE_DIR = Path(__file__).resolve().parent
# Fixed demonstration endpoints retain the goals their original bank covers.
PILOTS = {slug: CATALOG_ROUTES[slug] for slug in (
    "derivatives", "programming", "programming-variables", "programming-types", "programming-conditions",
    "control", "control-signals", "control-system", "modeling")}
PILOTS["programming-types"] = dict(PILOTS["programming-types"], goal="Различать типы данных Python")
logger = logging.getLogger("remi")
legacy = APIRouter()  # Historical contract, retained only for offline regression tests.
from app.operations import install, lifespan
app = FastAPI(title="RemI AI", version="0.2.0",lifespan=lifespan)
install(app)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")


app.include_router(accounts.router)
app.include_router(adaptive.router)
app.include_router(moderation.router)


@app.get("/learn/{slug}", include_in_schema=False)
def learning_page(slug: str):
    if slug not in adaptive.KEY_SKILLS:
        raise HTTPException(404, "Маршрут не найден.")
    return FileResponse(BASE_DIR / "static" / "learn.html")


@app.get("/profile", include_in_schema=False)
def profile_page():
    return FileResponse(BASE_DIR / "static" / "profile.html")


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(BASE_DIR / "static" / "index.html")


@app.get("/api/disciplines")
def list_disciplines():
    try:
        with open_database() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT d.discipline_id, d.name, d.description, d.detail_level,
                           COUNT(t.topic_id) AS topic_count
                    FROM remi_project.disciplines AS d
                    LEFT JOIN remi_project.topics AS t ON t.discipline_id = d.discipline_id
                    WHERE d.is_active
                    GROUP BY d.discipline_id, d.name, d.description, d.detail_level
                    ORDER BY d.discipline_id
                    """
                )
                return {"disciplines": cursor.fetchall()}
    except psycopg.Error:
        logger.warning("Не удалось получить дисциплины из PostgreSQL")
        raise HTTPException(status_code=503, detail="Не удалось загрузить дисциплины. Проверьте подключение к базе.") from None


@app.get("/api/disciplines/{discipline_id}/topics")
def list_topics(discipline_id: int):
    try:
        with open_database() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT discipline_id, name FROM remi_project.disciplines WHERE discipline_id = %s AND is_active",
                    (discipline_id,),
                )
                discipline = cursor.fetchone()
                if discipline is None:
                    raise HTTPException(status_code=404, detail="Дисциплина не найдена.")
                cursor.execute(
                    """
                    SELECT topic_id, name
                    FROM remi_project.topics
                    WHERE discipline_id = %s
                    ORDER BY topic_id
                    """,
                    (discipline_id,),
                )
                topics = cursor.fetchall()
                slugs = {r["topic"]: slug for slug, r in CATALOG_ROUTES.items() if r["discipline"] == discipline["name"]}
                return {"discipline": discipline, "topics": [dict(t, slug=slugs.get(t["name"])) for t in topics]}
    except psycopg.Error:
        logger.warning("Не удалось получить темы из PostgreSQL")
        raise HTTPException(status_code=503, detail="Не удалось загрузить темы. Проверьте подключение к базе.") from None


@app.get("/api/disciplines/{discipline_id}/resources")
def list_resources(discipline_id: int):
    try:
        with open_database() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1 FROM remi_project.disciplines WHERE discipline_id = %s AND is_active", (discipline_id,))
                if cursor.fetchone() is None:
                    raise HTTPException(status_code=404, detail="Дисциплина не найдена.")
                cursor.execute("""
                    SELECT r.title, r.resource_type AS kind, r.url, r.description, r.provider,
                           c.priority, c.link_status, c.link_note, c.checked_on
                    FROM remi_project.catalog_resources c
                    JOIN remi_project.learning_resources r ON r.resource_id = c.resource_id
                    WHERE c.discipline_id = %s AND c.visible
                    ORDER BY c.priority DESC, r.title
                """, (discipline_id,))
                return {"resources": cursor.fetchall()}
    except psycopg.Error:
        logger.warning("Не удалось получить материалы из PostgreSQL")
        raise HTTPException(status_code=503, detail="Не удалось загрузить материалы. Проверьте подключение к базе.") from None


def read_pilot_graph(config, db=None, *, resources=True):
    """Читаем граф выбранной цели и связанные материалы, не меняя базу."""
    with (nullcontext(db) if db is not None else open_database()) as connection:
        with connection.cursor() as cursor:
            cursor.execute("""
                WITH RECURSIVE path AS (
                    SELECT c.competency_id, ARRAY[c.competency_id] AS visited
                    FROM remi_project.competencies c
                    JOIN remi_project.topics t ON t.topic_id=c.topic_id
                    JOIN remi_project.disciplines d ON d.discipline_id=t.discipline_id
                    WHERE c.name=%s AND t.name=%s AND d.name=%s AND d.is_active
                    UNION ALL
                    SELECT p.prerequisite_id, path.visited || p.prerequisite_id
                    FROM path JOIN remi_project.prerequisites p ON p.competency_id=path.competency_id
                    WHERE NOT p.prerequisite_id=ANY(path.visited)
                )
                SELECT DISTINCT c.competency_id, c.name, c.description, t.name AS topic
                FROM path JOIN remi_project.competencies c USING(competency_id)
                JOIN remi_project.topics t ON t.topic_id=c.topic_id
                ORDER BY c.competency_id
            """, (config['goal'], config['topic'], config['discipline']))
            nodes = cursor.fetchall()
            if not nodes:
                return [], [], []
            ids = [node["competency_id"] for node in nodes]
            cursor.execute("""SELECT competency_id, prerequisite_id FROM remi_project.prerequisites
                              WHERE competency_id=ANY(%s) AND prerequisite_id=ANY(%s)""", (ids, ids))
            edges = cursor.fetchall()
            if not resources:
                return nodes, edges, []
            cursor.execute("""SELECT cr.competency_id, r.title, r.url, r.provider, r.review_status
                              FROM remi_project.competency_resources cr
                              JOIN remi_project.learning_resources r USING(resource_id)
                              WHERE cr.competency_id=ANY(%s) AND r.url LIKE 'https://%%'
                                AND r.review_status <> 'rejected'
                              ORDER BY r.resource_id""", (ids,))
            resources = cursor.fetchall()
            return nodes, edges, resources


def derivative_graph():
    return read_pilot_graph(PILOTS['derivatives'])


class PilotAnswers(BaseModel):
    answers: dict[str, int]


@legacy.get("/pilot/derivatives", include_in_schema=False)
def derivatives_page(pilot: str = "derivatives"):
    if pilot in adaptive.KEY_SKILLS:
        return learning_page(pilot)
    return FileResponse(BASE_DIR / "static" / "derivatives.html")


@legacy.get("/api/pilot/derivatives")
def get_derivatives():
    try:
        nodes, edges, resources = derivative_graph()
    except psycopg.Error:
        logger.warning("Не удалось прочитать учебную карту")
        raise HTTPException(status_code=503, detail="Не удалось загрузить карту из базы.") from None
    if not nodes:
        raise HTTPException(status_code=404, detail="Цель не найдена в базе.")
    return {"slug": "derivatives", **PILOTS['derivatives'], "nodes": nodes, "edges": edges, "resources": add_curated(nodes, resources),
            "questions": public_questions([node["name"] for node in nodes])}


@legacy.post("/api/pilot/derivatives/check")
def check_derivatives(data: PilotAnswers):
    try:
        nodes, _, _ = derivative_graph()
    except psycopg.Error:
        raise HTTPException(status_code=503, detail="Не удалось загрузить карту из базы.") from None
    if not nodes:
        raise HTTPException(status_code=404, detail="Цель не найдена в базе.")
    try:
        return evaluate([node["name"] for node in nodes], data.answers)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None


class RetakeAnswers(PilotAnswers):
    competency_id: int


def retake_node(competency_id):
    try:
        nodes, _, _ = derivative_graph()
    except psycopg.Error:
        raise HTTPException(status_code=503, detail="Не удалось загрузить карту из базы.") from None
    node = next((node for node in nodes if node['competency_id'] == competency_id), None)
    if not node or not RETAKE_QUESTIONS.get(node['name']):
        raise HTTPException(status_code=404, detail="Повторная проверка для этого навыка не найдена.")
    return node


@legacy.get('/api/pilot/derivatives/retake/{competency_id}')
def get_retake(competency_id: int):
    node = retake_node(competency_id)
    return {'competency': node['name'], 'questions': public_questions([node['name']], RETAKE_QUESTIONS)}


@legacy.post('/api/pilot/derivatives/retake')
def check_retake(data: RetakeAnswers):
    node = retake_node(data.competency_id)
    try:
        return evaluate([node['name']], data.answers, RETAKE_QUESTIONS)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None


def get_pilot_graph(slug, *, catalog=False):
    config = (CATALOG_ROUTES if catalog else PILOTS).get(slug)
    if not config:
        raise HTTPException(status_code=404, detail='Такой учебный маршрут пока не подготовлен.')
    try:
        nodes, edges, resources = derivative_graph() if slug == 'derivatives' else read_pilot_graph(config)
    except psycopg.Error:
        raise HTTPException(status_code=503, detail='Не удалось загрузить карту из базы.') from None
    if not nodes:
        raise HTTPException(status_code=404, detail='Цель пока не найдена в базе.')
    if not catalog:
        nodes = [n for n in nodes if n["name"] in QUESTIONS]
        fixed_ids = {n["competency_id"] for n in nodes}
        edges = [e for e in edges if e["competency_id"] in fixed_ids and e["prerequisite_id"] in fixed_ids]
        resources = [r for r in resources if r["competency_id"] in fixed_ids]
    return config, nodes, edges, resources


@app.get("/api/overview/modeling")
def modeling_overview():
    config, nodes, edges, _ = get_pilot_graph("modeling",catalog=True)
    goal = next(n for n in nodes if n["name"] == config["goal"])
    with open_database() as db:
        materials = recommend(db, config["topic"], goal, "Обзор темы", 0, 0)["items"]
    return {**config, "nodes": nodes, "edges": edges,
            "materials": [{k: item[k] for k in ("course","title","url","description")} for item in materials]}


@legacy.get('/api/pilot/{slug}')
def get_pilot(slug: str):
    config, nodes, edges, resources = get_pilot_graph(slug)
    return {'slug':slug, **config, 'nodes':nodes, 'edges':edges, 'resources':add_curated(nodes, resources),
            'questions':public_questions([node['name'] for node in nodes])}


@legacy.post('/api/pilot/{slug}/check')
def check_pilot(slug: str, data: PilotAnswers):
    _, nodes, _, _ = get_pilot_graph(slug)
    try:
        return evaluate([node['name'] for node in nodes], data.answers)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None


def generic_retake_node(slug, competency_id):
    _, nodes, _, _ = get_pilot_graph(slug)
    node = next((node for node in nodes if node['competency_id'] == competency_id), None)
    if not node or not RETAKE_QUESTIONS.get(node['name']):
        raise HTTPException(status_code=404, detail='Повторная проверка для этого навыка не найдена.')
    return node


@legacy.get('/api/pilot/{slug}/retake/{competency_id}')
def get_pilot_retake(slug: str, competency_id: int):
    node = generic_retake_node(slug, competency_id)
    return {'competency':node['name'], 'questions':public_questions([node['name']], RETAKE_QUESTIONS)}


@legacy.post('/api/pilot/{slug}/retake')
def check_pilot_retake(slug: str, data: RetakeAnswers):
    node = generic_retake_node(slug, data.competency_id)
    try:
        return evaluate([node['name']], data.answers, RETAKE_QUESTIONS)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None


@app.get("/demo",include_in_schema=False)
def demo():
    return FileResponse(BASE_DIR.parent / "demo" / "index.html")
