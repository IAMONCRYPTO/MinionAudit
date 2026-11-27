import json
import os
import shutil
from pathlib import Path
import tempfile
import unittest

from minion_audit.tools import scan_tree, protect_environment, redact
from minion_audit.report import write_report
from minion_audit.agent import compare_findings


class AuditTests(unittest.TestCase):
    def test_fix_refuses_hard_link_outside_repository(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as temporary:
            parent = Path(temporary)
            root = parent / "repository"
            root.mkdir()
            external = parent / "external.txt"
            external.write_text("preserve me")
            os.link(external, root / ".gitignore")
            with self.assertRaises(ValueError):
                protect_environment(root)
            self.assertEqual(external.read_text(), "preserve me")

    def test_regression_counts_only_removed_candidates(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = root / "agent.py"
            path.write_text("eval(user_input)\nexec(user_input)\n")
            first = scan_tree(root)
            baseline = {"ids": [f["id"] for f in first["findings"]]}
            path.write_text("# Dynamic eval removed\nexec(user_input)\n")
            current = scan_tree(root)
            self.assertEqual(compare_findings(current["findings"], baseline, True),
                             {"previous": 2, "current": 1, "resolved": 1, "new": 0, "comparable": True})
            self.assertEqual(compare_findings(current["findings"], baseline, False)["resolved"], 0)

    def test_planted_rules_and_no_secret_disclosure(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for name in ("Vault.sol", "agent.py"):
                shutil.copy(Path("sample_target") / name, root / name)
            shutil.copy("fixtures/sample.env.example", root / ".env")
            scan = scan_tree(root.resolve())
        self.assertEqual(len(scan["findings"]), 12)
        self.assertEqual({f["rule"] for f in scan["findings"]}, {"SEC001", "SEC002", "SOL001", "SOL002", "SOL003", "SOL004", "PY001", "PY002", "PY003"})
        self.assertNotIn("0123456789abcdef", json.dumps(scan))

    def test_skip_and_ast_multiline_and_stable_ids(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "node_modules").mkdir()
            (root / "node_modules" / "bad.py").write_text("eval(x)")
            path = root / "code.py"
            path.write_text('import subprocess\nsubprocess.run(\n "echo hi",\n shell=True\n)\n# eval(x)\ntext="eval(x)"\n')
            first = scan_tree(root)
            self.assertEqual([f["rule"] for f in first["findings"]], ["PY002"])
            path.write_text("\n" + path.read_text())
            self.assertEqual(first["findings"][0]["id"], scan_tree(root)["findings"][0]["id"])

    def test_safe_fix_idempotency_and_redaction(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / ".gitignore").write_text("build/")
            self.assertTrue(protect_environment(root)["changed"])
            self.assertFalse(protect_environment(root)["changed"])
            self.assertEqual((root / ".gitignore").read_text(), "build/\n.env\n")
        self.assertNotIn("secretvalue123", redact('API_KEY="secretvalue123"'))

    def test_report_escapes_untrusted_text(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "report.html"
            run = dict(repo="<script>oops</script>", timestamp="now", model="nim", session="test", status="complete", elapsed_seconds=1,
                       findings=[], remediation="<script>alert(1)</script>", trace=[])
            write_report(run, path)
            html = path.read_text()
            self.assertNotIn("<script>alert(1)</script>", html)
            self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", html)
            self.assertNotIn('<link ', html)


if __name__ == "__main__":
    unittest.main()
