#!/usr/bin/env python3
"""Create a deterministic, clean source/skill zip and SHA-256 checksum locally.

The destination must be outside the source tree. No commit, tag, push, or publish.
"""
import argparse
import hashlib
import re
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIRECTORIES = {"agents", "references", "scripts", "examples", "evals", "tests", "docs", ".github"}
FILES = {"SKILL.md", "README.md", "LICENSE", "CHANGELOG.md", "requirements-dev.txt", ".gitignore"}


def build(root, destination):
    root, destination = Path(root).resolve(), Path(destination).resolve()
    if destination.is_relative_to(root):
        raise ValueError("destination must be outside the source tree")
    match = re.search(r'^  version: "([0-9A-Za-z.+-]+)"$', (root / "SKILL.md").read_text(), re.M)
    if not match:
        raise ValueError("SKILL.md needs a quoted metadata version for release packaging")
    version = match.group(1)
    destination.mkdir(parents=True, exist_ok=True)
    archive = destination / f"codebase-sense-{version}.zip"
    # Never silently replace a previously reviewed release artifact.
    with zipfile.ZipFile(archive, "x", compression=zipfile.ZIP_DEFLATED) as output:
        for path in sorted(root.rglob("*")):
            relative = path.relative_to(root)
            if relative.parts[0] not in DIRECTORIES and str(relative) not in FILES:
                continue
            if not path.is_file() or path.is_symlink() or "__pycache__" in relative.parts or path.suffix == ".pyc":
                continue
            info = zipfile.ZipInfo(f"codebase-sense/{relative.as_posix()}", date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            output.writestr(info, path.read_bytes())
    checksum = hashlib.sha256(archive.read_bytes()).hexdigest()
    archive.with_suffix(".zip.sha256").write_text(f"{checksum}  {archive.name}\n")
    return archive, checksum


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    try:
        archive, checksum = build(ROOT, args.destination)
    except (OSError, ValueError) as exc:
        parser.exit(1, f"Cannot package release: {exc}\n")
    print(f"{archive}\nSHA256 {checksum}")


if __name__ == "__main__":
    main()
