from __future__ import annotations

import unittest

from example_service.main import as_record, build_summary, choose_colors, greet
from svc_a.handler import handle_request as handle_branch_a
from svc_a.handler import is_ready as branch_a_ready
from svc_a.handler import render_status as render_branch_a
from svc_a.handler import score_message as branch_a_score
from svc_b.handler import cap_message, handle_request as handle_branch_b, summarize as summarize_branch_b


class WorkspaceSampleTests(unittest.TestCase):
    def test_example_service(self) -> None:
        self.assertEqual(greet(" Drew ").message, "Hello, Drew!")
        self.assertEqual(choose_colors(2), ["red", "green"])
        self.assertEqual(build_summary("Drew", 2), "Hello, Drew! Colors: red, green")

        record = as_record(" Drew ", 1)
        self.assertEqual(record["service"], "example_service")
        self.assertEqual(record["subject"], "Drew")
        self.assertEqual(record["colors"], ["red"])

    def test_svc_a(self) -> None:
        self.assertEqual(branch_a_score("go"), 2)
        self.assertTrue(branch_a_ready("go"))

        report = handle_branch_a("go")
        self.assertTrue(report.accepted)
        self.assertEqual(report.service, "svc_a")
        self.assertEqual(render_branch_a("go"), "svc_a:ready:2")

    def test_svc_b(self) -> None:
        self.assertEqual(cap_message("  hello world  ", 8), "hello...")

        report = handle_branch_b("  hello world  ")
        self.assertTrue(report.truncated)
        self.assertEqual(report.service, "svc_b")
        self.assertEqual(summarize_branch_b("  hello world  "), "svc_b:truncated:hello...")