import unittest

from v5.evaluate import summarize
from v5.oracle import evaluate_source
from v5.tasks import TASKS


class EvaluationTest(unittest.TestCase):
    def test_all_task_oracles_reject_baseline_and_accept_reference(self):
        self.assertEqual(len(TASKS), 20)
        self.assertEqual(len({task.id for task in TASKS}), 20)
        for task in TASKS:
            with self.subTest(task=task.id):
                self.assertTrue(evaluate_source(task, task.solution)["success"])
                self.assertFalse(evaluate_source(task, task.source)["success"])

    def test_matched_pair_summary(self):
        base = dict(task="a", repeat=0, variant="full", success=True, tests_passed=3, tests_total=3,
                    steps=4, tool_calls=2, tokens=100, input_tokens=80, latency_seconds=2,
                    files_read=1, failure=None)
        other = {**base, "variant": "no_memory", "tokens": 120, "success": False,
                 "tests_passed": 2, "failure": "code_or_edit"}
        result = summarize([base, other])
        self.assertEqual(result["no_memory"]["paired"]["token_delta"], 20)
        self.assertEqual(result["no_memory"]["paired"]["success_delta"], -1)
