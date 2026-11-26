from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
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

    def test_text_report_keeps_threshold_exit_status(self):
        root = Path(__file__).resolve().parents[1]
        result = subprocess.run(
            [sys.executable, "-m", "grounding_eval", "examples/replies.json", "--format", "text",
             "--min-grounded", "0.8"],
            cwd=root, capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("overall: 6/7 correct, 5/7 grounded", result.stdout)
        self.assertIn("requires_abstention: 2/2 correct, 2/2 grounded", result.stdout)

    def test_abstention_threshold_is_independent_of_overall_score(self):
        root = Path(__file__).resolve().parents[1]
        replies = json.loads((root / "examples/replies.json").read_text(encoding="utf-8"))
        with TemporaryDirectory() as temp:
            path = Path(temp) / "replies.json"
            path.write_text(json.dumps([reply for reply in replies if reply["answer"] is not None]), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, "-m", "grounding_eval", str(path), "--min-abstention", "0.5"],
                cwd=root, capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertEqual(json.loads(result.stdout)["by_case_type"]["requires_abstention"]["grounded"], 0)

    def test_can_require_all_replies_without_hiding_the_report(self):
        root = Path(__file__).resolve().parents[1]
        replies = json.loads((root / "examples/replies.json").read_text(encoding="utf-8"))
        with TemporaryDirectory() as temp:
            path = Path(temp) / "replies.json"
            path.write_text(json.dumps(replies[1:]), encoding="utf-8")
            command = [sys.executable, "-m", "grounding_eval", str(path), "--require-all-replies"]
            result = subprocess.run(command, cwd=root, capture_output=True, text=True)
            self.assertEqual(result.returncode, 1, result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(report["missing_reply_count"], 1)
            self.assertIn("Missing reply", [item["reason"] for item in report["results"]])
            text_result = subprocess.run([*command, "--format", "text"], cwd=root, capture_output=True, text=True)
            self.assertIn("missing_reply_count: 1", text_result.stdout)

    def test_saves_report_even_when_a_threshold_fails(self):
        root = Path(__file__).resolve().parents[1]
        with TemporaryDirectory() as temp:
            path = Path(temp) / "report.json"
            command = [sys.executable, "-m", "grounding_eval", "examples/replies.json",
                       "--output", str(path), "--min-grounded", "0.8"]
            result = subprocess.run(command, cwd=root, capture_output=True, text=True)
            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertEqual(result.stdout, "")
            snapshot = path.read_text(encoding="utf-8")
            self.assertEqual(json.loads(snapshot)["grounded"], 5)
            self.assertEqual(subprocess.run(command, cwd=root, capture_output=True).returncode, 2)
            self.assertEqual(path.read_text(encoding="utf-8"), snapshot)

    def test_fixture_report_and_threshold(self):
        root = Path(__file__).resolve().parents[1]
        result = subprocess.run(
            [sys.executable, "-m", "grounding_eval", "examples/replies.json", "--min-grounded", "0.8"],
            cwd=root, capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 1, result.stderr)
        report = json.loads(result.stdout)
        snapshot = (root / "fixtures/repositories.json").read_bytes()
        self.assertEqual(report["source_sha256"], sha256(snapshot).hexdigest())
        for key, name in (("cases_sha256", "fixtures/cases.json"), ("replies_sha256", "examples/replies.json")):
            self.assertEqual(report[key], sha256((root / name).read_bytes()).hexdigest())
        self.assertEqual((report["total"], report["correct"], report["grounded"]), (7, 6, 5))
        self.assertEqual(report["by_case_type"], {
            "answerable": {"total": 5, "correct": 4, "grounded": 3},
            "requires_abstention": {"total": 2, "correct": 2, "grounded": 2},
        })


if __name__ == "__main__":
    unittest.main()
