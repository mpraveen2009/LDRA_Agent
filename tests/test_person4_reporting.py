import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

# Import modules from src directory.
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import github_reporter  # noqa: E402
import report_generator  # noqa: E402


class TestReportGenerator(unittest.TestCase):
    def setUp(self):
        self.sample_results = {
            "total_tests": 12,
            "passed": 11,
            "failed": 1,
            "coverage": {
                "statement": 91.5,
                "branch": 83.2,
                "mcdc": 77.0,
            },
            "failures": [
                {
                    "file": "math.c",
                    "function": "divide",
                    "reason": "division by zero mismatch",
                }
            ],
        }

    def test_build_markdown_contains_summary(self):
        markdown = report_generator._build_markdown(self.sample_results)
        self.assertIn("LDRA Test Report", markdown)
        self.assertIn("11/12 passed", markdown)
        self.assertIn("SC=91.5%", markdown)
        self.assertIn("math.c::divide", markdown)

    def test_build_html_contains_failure_row(self):
        html = report_generator._build_html(self.sample_results)
        self.assertIn("Status: FAIL", html)
        self.assertIn("math.c", html)
        self.assertIn("divide", html)

    def test_load_results_supports_utf8_bom(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "results.json"
            path.write_bytes("\ufeff".encode("utf-8") + json.dumps(self.sample_results).encode("utf-8"))
            loaded = report_generator._load_results(path)
            self.assertEqual(loaded["total_tests"], 12)


class TestGithubReporter(unittest.TestCase):
    def test_build_state_success_when_no_failures_and_threshold_met(self):
        results = {
            "failed": 0,
            "coverage": {"statement": 85.0},
        }
        state, description, success = github_reporter._build_state(results, 80.0)
        self.assertEqual(state, "success")
        self.assertTrue(success)
        self.assertIn("85.0%", description)

    def test_build_state_failure_when_threshold_not_met(self):
        results = {
            "failed": 0,
            "coverage": {"statement": 70.0},
        }
        state, _description, success = github_reporter._build_state(results, 80.0)
        self.assertEqual(state, "failure")
        self.assertFalse(success)

    def test_read_pr_number_from_event(self):
        with tempfile.TemporaryDirectory() as td:
            event = Path(td) / "event.json"
            event.write_text(json.dumps({"pull_request": {"number": 42}}), encoding="utf-8")
            with patch.dict(os.environ, {"GITHUB_EVENT_PATH": str(event)}, clear=False):
                self.assertEqual(github_reporter._read_pr_number_from_event(), 42)


if __name__ == "__main__":
    unittest.main()
