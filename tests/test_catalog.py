"""Проверки HTTP-каталога; интеграционные проверки требуют отдельной тестовой БД."""

import os
import unittest
from unittest.mock import patch

import psycopg
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


class CatalogTests(unittest.TestCase):
    def test_home_page_and_static_assets(self):
        self.assertEqual(client.get("/").status_code, 200)
        self.assertIn("RemI AI", client.get("/").text)
        self.assertEqual(client.get("/static/app.js").status_code, 200)

    def test_connection_failure_does_not_expose_details(self):
        with patch("app.main.open_database", side_effect=psycopg.OperationalError("private connection details")):
            for endpoint in ("/api/disciplines", "/api/disciplines/1/topics"):
                response = client.get(endpoint)
                self.assertEqual(response.status_code, 503)
                self.assertNotIn("private connection details", response.text)

    def test_non_integer_discipline_is_rejected(self):
        self.assertEqual(client.get("/api/disciplines/not-an-id/topics").status_code, 422)

    @unittest.skipUnless(os.environ.get("REMI_RUN_DB_TESTS") == "1", "Нужна отдельная тестовая база")
    def test_reads_disciplines_and_topics_from_postgresql(self):
        response = client.get("/api/disciplines")
        self.assertEqual(response.status_code, 200)
        disciplines = response.json()["disciplines"]
        self.assertEqual(len(disciplines), 5)
        math = next(d for d in disciplines if d["name"] == "Высшая математика")
        self.assertEqual(math["topic_count"], 6)
        topics = client.get(f"/api/disciplines/{math['discipline_id']}/topics")
        self.assertEqual(topics.status_code, 200)
        self.assertIn("Производные", [topic["name"] for topic in topics.json()["topics"]])
        self.assertEqual(client.get("/api/disciplines/999999/topics").status_code, 404)


if __name__ == "__main__":
    unittest.main()
