import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("check_skill", ROOT / "scripts/check_skill.py")
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


class SkillPackagingTests(unittest.TestCase):
    def package(self, frontmatter, body="Instructions."):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name) / "example-skill"
        (root / "agents").mkdir(parents=True)
        (root / "SKILL.md").write_text(f"---\n{frontmatter}\n---\n{body}\n", encoding="utf-8")
        (root / "agents/openai.yaml").write_text(
            'interface:\n  display_name: "Example"\n'
            '  short_description: "A useful example skill description"\n'
            '  default_prompt: "Use $example-skill to inspect code."\n', encoding="utf-8")
        return root

    def test_accepts_yaml_quoted_name_and_multiline_description(self):
        root = self.package('name: "example-skill"\ndescription: >-\n  Inspect code\n  and explain it.\nmetadata:\n  version: "1.0"')
        self.assertEqual(checker.validate_skill(root)["description"], "Inspect code and explain it.")

    def test_rejects_duplicate_yaml_keys(self):
        root = self.package("name: example-skill\nname: example-skill\ndescription: Inspect code")
        with self.assertRaisesRegex(ValueError, "duplicate"):
            checker.validate_skill(root)

    def test_rejects_nonstring_metadata(self):
        root = self.package("name: example-skill\ndescription: Inspect code\nmetadata:\n  version: 1")
        with self.assertRaisesRegex(ValueError, "metadata"):
            checker.validate_skill(root)

    def test_rejects_missing_reference(self):
        root = self.package("name: example-skill\ndescription: Inspect code", "Read references/missing.md.")
        with self.assertRaisesRegex(ValueError, "reference"):
            checker.validate_skill(root)

    def test_rejects_wrong_install_directory(self):
        root = self.package("name: other-skill\ndescription: Inspect code")
        with self.assertRaisesRegex(ValueError, "directory"):
            checker.validate_skill(root)

    def test_rejects_invalid_ui_prompt(self):
        root = self.package("name: example-skill\ndescription: Inspect code")
        config = root / "agents/openai.yaml"
        config.write_text(config.read_text().replace("$example-skill", "another skill"))
        with self.assertRaisesRegex(ValueError, "default_prompt"):
            checker.validate_skill(root)
