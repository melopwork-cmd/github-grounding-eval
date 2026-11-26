import json
from pathlib import Path
import subprocess
import sys
import unittest

from grounding_eval.evaluate import Case, Reply, evaluate, load_replies


class GroundingTests(unittest.TestCase):
    def setUp(self):
        self.sources = {"a/project": {"language": "TypeScript"}, "b/project": {"language": "TypeScript"}}
        self.case = Case("example", "Which language?", "a/project", "language")

    def test_normalizes_case_and_whitespace(self):
        reply = Reply("example", "  typescript ", ("a/project",))
        actual = evaluate([self.case], self.sources, {"example": reply})[0]
        self.assertTrue(actual.correct)
        self.assertTrue(actual.grounded)

    def test_right_answer_from_wrong_repository(self):
        reply = Reply("example", "TypeScript", ("b/project",))
        actual = evaluate([self.case], self.sources, {"example": reply})[0]
        self.assertTrue(actual.correct)
        self.assertFalse(actual.grounded)

    def test_unsourced_abstention(self):
        case = Case("unknown", "What is the budget?", None, None)
        reply = Reply("unknown", None, ())
        self.assertTrue(evaluate([case], self.sources, {"unknown": reply})[0].grounded)

    def test_missing_reply_is_counted(self):
        self.assertFalse(evaluate([self.case], self.sources, {})[0].correct)

    def test_duplicate_reply_is_an_error(self):
        item = {"id": "example", "answer": None, "citations": []}
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            load_replies([item, item])

    def test_fixture_report_and_threshold(self):
        root = Path(__file__).resolve().parents[1]
        result = subprocess.run(
            [sys.executable, "-m", "grounding_eval", "examples/replies.json", "--min-grounded", "0.8"],
            cwd=root, capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 1, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual((report["total"], report["correct"], report["grounded"]), (7, 6, 5))


if __name__ == "__main__":
    unittest.main()
