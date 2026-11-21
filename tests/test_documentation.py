"""Keep shipped Markdown navigation usable; this does not validate web links."""
import re
import unittest
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]


class DocumentationTests(unittest.TestCase):
    def test_local_markdown_links_resolve(self):
        documents = list(ROOT.glob("*.md"))
        for name in ("references", "examples", "docs", "evals"):
            documents.extend(path for path in (ROOT / name).rglob("*.md")
                             if "raw" not in path.relative_to(ROOT).parts)
        for document in documents:
            for target in re.findall(r"\]\(([^)]+)\)", document.read_text(encoding="utf-8")):
                if "://" in target or target.startswith("#"):
                    continue
                target = unquote(target.split("#", 1)[0].strip("<>"))
                with self.subTest(document=document.name, target=target):
                    self.assertTrue((document.parent / target).exists())
