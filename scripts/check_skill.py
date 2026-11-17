#!/usr/bin/env python3
"""Minimal dependency-free sanity check for the skill packaging.

This is not a full YAML parser or a replacement for an Agent Skills validator.
"""

from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
name = ROOT.name
content = (ROOT / "SKILL.md").read_text(encoding="utf-8")
match = re.match(r"\A---\n(.*?)\n---\n", content, re.S)
if not match:
    sys.exit("INVALID: missing YAML frontmatter")
frontmatter = match.group(1)
n = re.search(r"^name:\s*([^\n]+)$", frontmatter, re.M)
d = re.search(r"^description:\s*(.+)$", frontmatter, re.M)
if not n or n.group(1).strip() != name or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name) or len(name) > 64:
    sys.exit("INVALID: skill name does not match valid folder name")
if not d or not 1 <= len(d.group(1).strip()) <= 1024:
    sys.exit("INVALID: missing/invalid skill description")
for path in ("agents/openai.yaml", "README.md", "LICENSE", "references/sense-card.md"):
    if not (ROOT / path).is_file():
        sys.exit(f"INVALID: missing {path}")
print("VALID: basic skill layout and metadata")
