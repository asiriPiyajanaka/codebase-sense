import importlib.util
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("package_release", ROOT / "scripts/package_release.py")
packager = importlib.util.module_from_spec(spec)
spec.loader.exec_module(packager)


class ReleasePackagingTests(unittest.TestCase):
    def test_clean_reproducible_archive_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            root = base / "codebase-sense"
            root.mkdir()
            (root / "SKILL.md").write_text('---\nname: codebase-sense\nmetadata:\n  version: "0.2.0-rc.1"\n---\nInstructions')
            (root / "README.md").write_text("Read me")
            for directory in (".git", ".venv", "scripts/__pycache__"):
                (root / directory).mkdir(parents=True)
                (root / directory / "private").write_text("do not ship")
            first, first_hash = packager.build(root, base / "one")
            second, second_hash = packager.build(root, base / "two")
            self.assertEqual(first_hash, second_hash)
            self.assertEqual(first.read_bytes(), second.read_bytes())
            with zipfile.ZipFile(first) as archive:
                self.assertEqual(set(archive.namelist()), {"codebase-sense/SKILL.md", "codebase-sense/README.md"})
            with self.assertRaises(FileExistsError):
                packager.build(root, base / "one")
            with self.assertRaisesRegex(ValueError, "outside"):
                packager.build(root, root / "dist")
