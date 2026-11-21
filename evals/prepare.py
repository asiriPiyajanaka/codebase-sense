#!/usr/bin/env python3
"""Fetch hash-pinned public snapshots into a new scratch directory (Python 3.12+).

Does not install dependencies or run downloaded code. Requires network access.
"""
import argparse
import hashlib
import io
import json
import shutil
import tarfile
import urllib.request
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path, help="new, nonexistent scratch directory")
    args = parser.parse_args()
    args.destination.mkdir(parents=True, exist_ok=False)
    sources = json.loads(Path(__file__).with_name("sources.json").read_text())
    for item in sources:
        request = urllib.request.Request(item["url"], headers={"User-Agent": "codebase-sense-evaluation"})
        with urllib.request.urlopen(request, timeout=60) as response:
            data = response.read()
        if hashlib.sha256(data).hexdigest() != item["sha256"]:
            raise SystemExit(f"Archive hash mismatch: {item['id']}")
        target = args.destination / item["id"]
        target.mkdir()
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as archive:
            archive.extractall(target, filter="data")
        print(f"{item['id']}: {next(target.iterdir())}")
    shutil.copytree(Path(__file__).with_name("fixtures"), args.destination / "fixtures")


if __name__ == "__main__":
    main()
