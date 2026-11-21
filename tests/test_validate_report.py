import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("validate_report", ROOT / "scripts" / "validate_report.py")
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)
BASE = json.loads((ROOT / "examples" / "learning-progress-report.json").read_text())


class ReportValidationTests(unittest.TestCase):
    def test_sample_is_structurally_valid(self):
        validator.validate(BASE)

    def test_rejects_unknown_mode(self):
        report = copy.deepcopy(BASE)
        report["mode"] = "magic"
        with self.assertRaisesRegex(validator.InvalidReport, "mode"):
            validator.validate(report)

    def test_accepts_evidenced_violated_invariant_in_new_schema(self):
        report = copy.deepcopy(BASE)
        report["schema_version"] = "1.1"
        invariant = report["workflows"][0]["invariants"][0]
        invariant["status"] = "violated"
        invariant["evidence"] = copy.deepcopy(report["candidates"][0]["evidence"])
        validator.validate(report)

    def test_violated_invariant_requires_evidence(self):
        report = copy.deepcopy(BASE)
        report["schema_version"] = "1.1"
        report["workflows"][0]["invariants"][0]["status"] = "violated"
        with self.assertRaisesRegex(validator.InvalidReport, "evidence"):
            validator.validate(report)

    def test_legacy_schema_preserves_its_status_vocabulary(self):
        report = copy.deepcopy(BASE)
        report["workflows"][0]["invariants"][0]["status"] = "violated"
        with self.assertRaisesRegex(validator.InvalidReport, "status"):
            validator.validate(report)

    def test_rejects_unfounded_verified_invariant(self):
        report = copy.deepcopy(BASE)
        report["workflows"][0]["invariants"][0]["status"] = "verified"
        with self.assertRaisesRegex(validator.InvalidReport, "evidence"):
            validator.validate(report)

    def test_rejects_traversal(self):
        report = copy.deepcopy(BASE)
        report["candidates"][0]["evidence"][0]["path"] = "../../secret.txt"
        with self.assertRaisesRegex(validator.InvalidReport, "path"):
            validator.validate(report)

    def test_rejects_absent_source_when_repo_is_supplied(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(validator.InvalidReport, "does not exist"):
                validator.validate(BASE, Path(tmp))

    def test_accepts_real_cited_sources(self):
        report = copy.deepcopy(BASE)
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "src").mkdir()
            for name in ("level-controller.ts", "progress-service.ts", "reward-service.ts"):
                (repo / "src" / name).write_text("export const example = true;\n")
            report["candidates"][0]["evidence"][0]["line"] = 1
            validator.validate(report, repo)

    def test_rejects_out_of_range_line(self):
        report = copy.deepcopy(BASE)
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "src").mkdir()
            for name in ("level-controller.ts", "progress-service.ts", "reward-service.ts"):
                (repo / "src" / name).write_text("one line\n")
            report["candidates"][0]["evidence"][0]["line"] = 400
            with self.assertRaisesRegex(validator.InvalidReport, "file length"):
                validator.validate(report, repo)

    def test_rejects_symlink_outside_repo(self):
        report = copy.deepcopy(BASE)
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as outside:
            repo = Path(tmp)
            (repo / "src").mkdir()
            (Path(outside) / "secret.ts").write_text("secret\n")
            for name in ("level-controller.ts", "progress-service.ts"):
                (repo / "src" / name).write_text("one line\n")
            (repo / "src" / "reward-service.ts").symlink_to(Path(outside) / "secret.ts")
            with self.assertRaisesRegex(validator.InvalidReport, "escapes"):
                validator.validate(report, repo)

    def test_rejects_too_many_candidates(self):
        report = copy.deepcopy(BASE)
        report["candidates"] = [copy.deepcopy(BASE["candidates"][0]) for _ in range(4)]
        with self.assertRaisesRegex(validator.InvalidReport, "candidates"):
            validator.validate(report)


if __name__ == "__main__":
    unittest.main()
