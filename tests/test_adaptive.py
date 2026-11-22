import unittest

from fastapi import HTTPException
from app.adaptive import grade, planned, status, study_steps
from app.pilot_content import ERROR, LOOP, FEEDBACK


class AdaptiveRules(unittest.TestCase):
    def test_route_respects_shared_and_indirect_prerequisites(self):
        edges = [{"competency_id": child, "prerequisite_id": parent}
                 for child, parent in [(5, 3), (5, 4), (4, 2), (3, 2), (2, 1)]]
        latest = {1: {"knowledge_status": "needs_review"}, 2: {"knowledge_status": "mastered"},
                  4: {"knowledge_status": "possible_gap"}}
        steps = study_steps(5, {4, 5}, edges, latest)
        self.assertEqual([s["skill"] for s in steps], [1, 4, 5])
        self.assertEqual(steps[0]["path"], [1, 2, 3, 5])
        self.assertEqual(steps[-1]["status"], "not_assessed")
        latest[1]["knowledge_status"] = "mastered"
        self.assertEqual(study_steps(5, {4, 5}, edges, latest)[0]["skill"], 4)

    def test_insufficient_and_majority(self):
        for answers,expected in [([],"not_assessed"),([False],"needs_review"),([True,False],"needs_review"),
                                 ([True,False,True],"mastered"),([False,True,False],"possible_gap")]:
            self.assertEqual(status([{"is_correct":v} for v in answers],2),expected)

    def test_check_foundation_only_after_independent_evidence(self):
        nodes = [{"name":name,"competency_id":i} for i,name in enumerate([ERROR,LOOP,FEEDBACK,"Основа"],1)]
        edges = [{"competency_id":1,"prerequisite_id":4},{"competency_id":2,"prerequisite_id":4}]
        session = {"pilot_slug":"control","retake_skill":None,"pilot_rules":{"votes":2,"depth":3}}
        answers = {i:[] for i in range(1,5)}
        answers[1] = [{"is_correct":False}]
        self.assertEqual(planned(session,nodes,edges,answers),[1,2,3])
        answers[1].append({"is_correct":False})
        answers[2] = answers[1]
        self.assertEqual(planned(session,nodes,edges,answers),[1,4,2,3])
        session["pilot_rules"]["depth"] = 0
        self.assertEqual(planned(session,nodes,edges,answers),[1,2,3])

    def test_rubric_and_finite_numbers(self):
        q = {"answer_type":"numeric","expected_answer":"-1.5","numeric_tolerance":0}
        self.assertTrue(grade(q,"−1,50"))
        for value in ["NaN","Infinity","1e9999",""]:
            with self.assertRaises(HTTPException):
                grade(q,value)
        word = {"answer_type":"short_text","expected_answer":"замкнутый"}
        self.assertTrue(grade(word,"  ЗАМКНУТЫЙ "))
        self.assertFalse(grade(word,"разомкнутый"))


