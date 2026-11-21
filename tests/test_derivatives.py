import os
import unittest
from unittest.mock import patch

import psycopg
from fastapi.testclient import TestClient

from app.derivatives import QUESTIONS, RETAKE_QUESTIONS, evaluate, public_questions
from app.main import PILOTS, app


client = TestClient(app)
nodes = [
    {"competency_id": 1, "name": "Вычислять значение функции", "topic": "Функции", "description": "Пример"},
    {"competency_id": 2, "name": "Находить производную", "topic": "Производные", "description": "Пример"},
]
edges = [{"competency_id": 2, "prerequisite_id": 1}]


class DerivativePilotTests(unittest.TestCase):
    @patch('app.main.read_pilot_graph')
    def test_new_topic_routes_have_questions_and_retake(self, graph):
        for slug in ('programming-variables', 'programming-types', 'programming-conditions', 'control-system', 'control-signals'):
            with self.subTest(slug=slug):
                config = PILOTS[slug]
                node = {'competency_id': 99, 'name': config['goal'], 'topic': config['topic'], 'description': ''}
                graph.return_value = ([node], [], [])
                response = client.get(f'/api/pilot/{slug}')
                self.assertEqual(response.status_code, 200)
                self.assertEqual(len(response.json()['questions']), 2)
                retake = client.get(f'/api/pilot/{slug}/retake/99')
                self.assertEqual(retake.status_code, 200)
                self.assertEqual(len(retake.json()['questions']), 2)

    def test_question_bank_has_unique_valid_choices(self):
        self.assertEqual(set(QUESTIONS), set(RETAKE_QUESTIONS))
        for name in QUESTIONS:
            for bank in (QUESTIONS, RETAKE_QUESTIONS):
                self.assertEqual(len(bank[name]), 2)
                for text, options, correct in bank[name]:
                    self.assertTrue(text)
                    self.assertEqual(len(options), len(set(options)))
                    self.assertIn(correct, range(len(options)))
            self.assertTrue(set(q[0] for q in QUESTIONS[name]).isdisjoint(q[0] for q in RETAKE_QUESTIONS[name]))

    def test_correct_incorrect_and_unassessed(self):
        names = [nodes[0]["name"], nodes[1]["name"], "Неизвестный навык"]
        answers = {"Вычислять значение функции:0": 1, "Вычислять значение функции:1": 1,
                   "Находить производную:0": 0, "Находить производную:1": 0}
        result = evaluate(names, answers)
        self.assertEqual(result["results"][names[0]]["status"], "preliminary_correct")
        self.assertEqual(result["results"][names[1]]["status"], "needs_review")
        self.assertEqual(result["results"][names[2]]["status"], "not_assessed")
        self.assertFalse(result["feedback"]["Находить производную:0"])
        with self.assertRaises(ValueError):
            evaluate(names, {"Находить производную:0": 1})

    @patch("app.main.derivative_graph", return_value=(nodes, edges, []))
    def test_http_flow_hides_answers_and_checks_input(self, graph):
        response = client.get("/api/pilot/derivatives")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["edges"], edges)
        self.assertEqual(len(body["questions"]), 4)
        self.assertNotIn("answer", body["questions"][0])
        answers = {question["id"]: 0 for question in body["questions"]}
        result = client.post("/api/pilot/derivatives/check", json={"answers": answers})
        self.assertEqual(result.status_code, 200)
        self.assertEqual(len(result.json()["results"]), 2)
        self.assertEqual(client.post("/api/pilot/derivatives/check", json={"answers": {}}).status_code, 422)
        self.assertEqual(client.get('/pilot/derivatives').status_code, 200)

    @patch("app.main.open_database", side_effect=psycopg.OperationalError("secret"))
    def test_database_failure_does_not_expose_details(self, connect):
        response = client.get("/api/pilot/derivatives")
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("secret", response.text)

    @patch("app.main.derivative_graph", return_value=(nodes, edges, []))
    def test_retake_only_changes_requested_skill(self, graph):
        response = client.get('/api/pilot/derivatives/retake/1')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()['questions']), 2)
        self.assertNotIn('answer', response.json()['questions'][0])
        competency = nodes[0]['name']
        answers = {f'{competency}:{i}': item[2] for i, item in enumerate(RETAKE_QUESTIONS[competency])}
        response = client.post('/api/pilot/derivatives/retake', json={'competency_id':1,'answers':answers})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.json()['results']), [competency])
        self.assertEqual(response.json()['results'][competency]['status'], 'preliminary_correct')
        answers[f'{competency}:0'] = (answers[f'{competency}:0'] + 1) % 3
        response = client.post('/api/pilot/derivatives/retake', json={'competency_id':1,'answers':answers})
        self.assertEqual(response.json()['results'][competency]['status'], 'needs_review')
        self.assertEqual(client.get('/api/pilot/derivatives/retake/999').status_code, 404)
        self.assertEqual(client.post('/api/pilot/derivatives/retake', json={'competency_id':2,'answers':answers}).status_code, 422)

    @unittest.skipUnless(os.environ.get('REMI_PILOT_DB_TEST') == '1', 'Нужна отдельная тестовая база')
    def test_database_graph_and_different_answers(self):
        response = client.get('/api/pilot/derivatives')
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertTrue(any(node['name'] == 'Вычислять производную многочлена' for node in payload['nodes']))
        self.assertTrue(payload['edges'])
        self.assertTrue(payload['resources'])
        correct = {q['id']: QUESTIONS[q['competency']][int(q['id'].rsplit(':', 1)[1])][2]
                   for q in payload['questions']}
        first = client.post('/api/pilot/derivatives/check', json={'answers': correct})
        self.assertEqual(first.status_code, 200, first.text)
        self.assertTrue(all(item['status'] == 'preliminary_correct' for item in first.json()['results'].values()))
        question = payload['questions'][0]
        correct[question['id']] = (correct[question['id']] + 1) % len(question['options'])
        second = client.post('/api/pilot/derivatives/check', json={'answers': correct})
        self.assertEqual(second.json()['results'][question['competency']]['status'], 'needs_review')
        node = next(node for node in payload['nodes'] if node['name'] == question['competency'])
        repeated = client.get(f"/api/pilot/derivatives/retake/{node['competency_id']}")
        self.assertEqual(repeated.status_code, 200)
        retake = {q['id']: RETAKE_QUESTIONS[q['competency']][int(q['id'].rsplit(':', 1)[1])][2]
                  for q in repeated.json()['questions']}
        result = client.post('/api/pilot/derivatives/retake', json={'competency_id':node['competency_id'], 'answers':retake})
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json()['results'][question['competency']]['status'], 'preliminary_correct')
        self.assertEqual(len(result.json()['results']), 1)

    @unittest.skipUnless(os.environ.get('REMI_PILOT_DB_TEST') == '1', 'Нужна отдельная тестовая база')
    def test_other_disciplines_have_complete_learning_pilots(self):
        for slug in ('programming', 'modeling', 'control'):
            with self.subTest(slug=slug):
                response = client.get(f'/api/pilot/{slug}')
                self.assertEqual(response.status_code, 200, response.text)
                payload = response.json()
                self.assertEqual(payload['slug'], slug)
                self.assertGreaterEqual(len(payload['nodes']), 2)
                self.assertTrue(payload['edges'])
                self.assertEqual(set(item['name'] for item in payload['nodes']), set(item['competency'] for item in payload['questions']))
                answers = {q['id']: QUESTIONS[q['competency']][int(q['id'].rsplit(':',1)[1])][2] for q in payload['questions']}
                result = client.post(f'/api/pilot/{slug}/check', json={'answers':answers})
                self.assertEqual(result.status_code, 200, result.text)
                self.assertTrue(all(item['status'] == 'preliminary_correct' for item in result.json()['results'].values()))
                target = next(n for n in payload['nodes'] if n['name'] == payload['goal'])
                self.assertEqual(client.get(f"/api/pilot/{slug}/retake/{target['competency_id']}").status_code, 200)
        self.assertEqual(client.get('/api/pilot/unknown').status_code, 404)


if __name__ == '__main__':
    unittest.main()
