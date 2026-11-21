#!/usr/bin/env python3
"""Ask a local Codex app-server to discover an installed skill, without a model call.

Usage: python3 scripts/smoke_codex.py PROJECT_DIR NEW_SCRATCH_DIR
Codex must be installed. Writes operational state only into the scratch directory.
No source changes, authentication changes, or agent turn is requested.
"""
import argparse
import json
import selectors
import subprocess
import time
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path)
    parser.add_argument("scratch", type=Path)
    args = parser.parse_args()
    scratch = args.scratch.resolve()
    scratch.mkdir(parents=True, exist_ok=False)
    command = ["codex", "app-server", "--stdio", "-c", f"sqlite_home={json.dumps(str(scratch / 'state'))}",
               "-c", f"log_dir={json.dumps(str(scratch / 'logs'))}"]
    with (scratch / "stderr.log").open("w") as errors:
        process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=errors, text=True, bufsize=1)
        selector = selectors.DefaultSelector()
        selector.register(process.stdout, selectors.EVENT_READ)

        def send(value):
            process.stdin.write(json.dumps(value) + "\n")
            process.stdin.flush()

        try:
            send({"id": 1, "method": "initialize", "params": {
                "clientInfo": {"name": "codebase_sense_smoke", "version": "0.1"},
                "capabilities": {"experimentalApi": True}}})
            deadline = time.monotonic() + 30
            while time.monotonic() < deadline:
                if not selector.select(1):
                    continue
                line = process.stdout.readline()
                if not line:
                    raise SystemExit(f"Codex exited before discovery; inspect {scratch / 'stderr.log'}")
                response = json.loads(line)
                if response.get("id") not in (1, 2):
                    continue
                if "error" in response:
                    raise SystemExit(f"Codex RPC error: {response['error']}")
                if response["id"] == 1:
                    send({"method": "initialized", "params": {}})
                    send({"id": 2, "method": "skills/list", "params": {
                        "cwds": [str(args.project.resolve())], "forceReload": True}})
                    continue
                found = []

                def walk(value):
                    if isinstance(value, dict):
                        if value.get("name") == "codebase-sense":
                            found.append(value)
                        else:
                            for child in value.values():
                                walk(child)
                    elif isinstance(value, list):
                        for child in value:
                            walk(child)

                walk(response["result"])
                if not found:
                    raise SystemExit("Codex did not discover codebase-sense")
                result = {"method": "skills/list", "skills": found}
                (scratch / "discovery.json").write_text(json.dumps(result, indent=2) + "\n")
                print(json.dumps(result, indent=2))
                return
            raise SystemExit("Codex local discovery timed out")
        finally:
            selector.close()
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()


if __name__ == "__main__":
    main()
