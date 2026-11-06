"""Каталог дисциплин RemI AI: HTTP-интерфейс и чтение из PostgreSQL."""

import logging
import os
from pathlib import Path

import psycopg
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from psycopg.rows import dict_row


BASE_DIR = Path(__file__).resolve().parent
logger = logging.getLogger("remi")
app = FastAPI(title="RemI AI", version="0.1.0")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")


def open_database():
    """Пароль берётся из PGPASSWORD или настроенного файла pgpass, не из кода."""
    return psycopg.connect(
        host=os.environ.get("PGHOST", "127.0.0.1"),
        port=os.environ.get("PGPORT", "5432"),
        dbname=os.environ.get("PGDATABASE", "RemI_AI"),
        user=os.environ.get("PGUSER", "postgres"),
        connect_timeout=3,
        row_factory=dict_row,
    )


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
                    "SELECT discipline_id, name FROM remi_project.disciplines WHERE discipline_id = %s",
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
                return {"discipline": discipline, "topics": cursor.fetchall()}
    except psycopg.Error:
        logger.warning("Не удалось получить темы из PostgreSQL")
        raise HTTPException(status_code=503, detail="Не удалось загрузить темы. Проверьте подключение к базе.") from None
