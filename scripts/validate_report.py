#!/usr/bin/env python3
"""Validate Codebase Sense's optional JSON report structure and source paths.

Does not establish the truth of report claims or run application tests.
Python 3.9+, standard library only. Usage:
    python3 scripts/validate_report.py path/to/report.json [--repo path/to/repo]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path, PurePosixPath

MODES = {"audit", "plan", "implement", "review", "verify"}
DECISIONS = {"change", "investigate", "keep"}
INVARIANT_STATUSES = {"verified", "violated", "missing", "unknown"}
CHECK_STATUSES = {"passed", "failed", "blocked", "not_run"}


class InvalidReport(ValueError):
    """User-readable validation error."""


def fail(location: str, detail: str) -> None:
    raise InvalidReport(f"{location}: {detail}")


def require_obj(value, loc: str) -> dict:
    if not isinstance(value, dict):
        fail(loc, "expected JSON object")
    return value


def require_list(value, loc: str, minimum: int = 0, maximum=None) -> list:
    if not isinstance(value, list):
        fail(loc, "expected JSON array")
    if len(value) < minimum or (maximum is not None and len(value) > maximum):
        fail(loc, f"expected between {minimum} and {maximum or 'unlimited'} entries")
    return value


def require_text(obj: dict, field: str, loc: str) -> str:
    value = obj.get(field)
    if not isinstance(value, str) or not value.strip():
        fail(f"{loc}.{field}", "expected non-empty string")
    return value.strip()


def require_string_list(obj: dict, field: str, loc: str) -> None:
    for i, val in enumerate(require_list(obj.get(field), f"{loc}.{field}")):
        if not isinstance(val, str) or not val.strip():
            fail(f"{loc}.{field}[{i}]", "expected non-empty string")


def valid_repo_path(path: str, loc: str, repo: Path | None) -> None:
    # Enforce portable, repository-relative references; no traversal and no embedded NULL.
    if (not path or "\\" in path or "\x00" in path or path.startswith("/")
            or ":" in path or any(p in {"", ".", ".."} for p in path.split("/"))):
        fail(loc, "expected normalized relative repository path without traversal")
    pure = PurePosixPath(path)
    if pure.is_absolute():
        fail(loc, "absolute path not allowed")
    if repo is not None:
        root = repo.resolve()
        resolved = (root / path).resolve()
        if not resolved.is_relative_to(root):
            fail(loc, "reference escapes repository root")
        if not resolved.is_file():
            fail(loc, f"referenced source file does not exist: {path}")


def evidence_entries(value, loc: str, repo: Path | None, min_count=0) -> None:
    for i, item in enumerate(require_list(value, loc, minimum=min_count)):
        row_loc = f"{loc}[{i}]"
        item = require_obj(item, row_loc)
        path = require_text(item, "path", row_loc)
        valid_repo_path(path, f"{row_loc}.path", repo)
        if "line" in item:
            line = item["line"]
            if type(line) is not int or line <= 0:
                fail(f"{row_loc}.line", "expected positive integer")
            if repo is not None:
                try:
                    with (repo / path).open("rb") as f:
                        total_lines = sum(1 for _ in f)
                except OSError as exc:
                    fail(f"{row_loc}.path", f"cannot read source file: {exc}")
                if line > total_lines:
                    fail(f"{row_loc}.line", f"line exceeds file length ({total_lines})")
        for optional_field in ("symbol", "detail"):
            if optional_field in item:
                require_text(item, optional_field, row_loc)


def validate(report: dict, repo: Path | None = None) -> None:
    report = require_obj(report, "report")
    version = report.get("schema_version")
    if version not in ("1.0", "1.1"):
        fail("schema_version", "expected '1.0' or '1.1'")
    require_text(report, "scope", "report")
    mode = require_text(report, "mode", "report")
    if mode not in MODES:
        fail("mode", f"expected one of {sorted(MODES)}")
    require_text(report, "summary", "report")
    workflows = require_list(report.get("workflows"), "workflows", minimum=1)
    for i, workflow in enumerate(workflows):
        loc = f"workflows[{i}]"
        workflow = require_obj(workflow, loc)
        for field in ("name", "promise", "owner", "change_entry_point"):
            require_text(workflow, field, loc)
        entry = require_text(workflow, "entry_point", loc)
        valid_repo_path(entry, f"{loc}.entry_point", repo)
        trace = require_list(workflow.get("trace"), f"{loc}.trace", minimum=1)
        for j, trace_item in enumerate(trace):
            tl = f"{loc}.trace[{j}]"
            trace_item = require_obj(trace_item, tl)
            path = require_text(trace_item, "path", tl)
            valid_repo_path(path, f"{tl}.path", repo)
            require_text(trace_item, "symbol", tl)
            require_text(trace_item, "role", tl)
        invariants = require_list(workflow.get("invariants"), f"{loc}.invariants", minimum=1)
        for j, inv in enumerate(invariants):
            il = f"{loc}.invariants[{j}]"
            inv = require_obj(inv, il)
            require_text(inv, "statement", il)
            status = require_text(inv, "status", il)
            allowed_statuses = INVARIANT_STATUSES if version == "1.1" else INVARIANT_STATUSES - {"violated"}
            if status not in allowed_statuses:
                fail(f"{il}.status", f"expected one of {sorted(allowed_statuses)}")
            evidence_entries(inv.get("evidence"), f"{il}.evidence", repo,
                             min_count=1 if status in {"verified", "violated"} else 0)
        require_string_list(workflow, "unknowns", loc)

    candidates = require_list(report.get("candidates"), "candidates", maximum=3)
    ids = set()
    for i, candidate in enumerate(candidates):
        loc = f"candidates[{i}]"
        candidate = require_obj(candidate, loc)
        ident = require_text(candidate, "id", loc)
        if ident in ids:
            fail(f"{loc}.id", "candidate id must be unique")
        ids.add(ident)
        for field in ("title", "reason", "counterargument", "possible_contract",
                      "test_implication", "next_step"):
            require_text(candidate, field, loc)
        decision = require_text(candidate, "recommendation", loc)
        if decision not in DECISIONS:
            fail(f"{loc}.recommendation", f"expected one of {sorted(DECISIONS)}")
        evidence_entries(candidate.get("evidence"), f"{loc}.evidence", repo, min_count=1)

    verification = require_obj(report.get("verification"), "verification")
    checks = require_list(verification.get("checks"), "verification.checks")
    for i, check in enumerate(checks):
        loc = f"verification.checks[{i}]"
        check = require_obj(check, loc)
        require_text(check, "command", loc)
        status = require_text(check, "status", loc)
        if status not in CHECK_STATUSES:
            fail(f"{loc}.status", f"expected one of {sorted(CHECK_STATUSES)}")
        require_text(check, "details", loc)
    require_string_list(verification, "unverified", "verification")
    require_text(report, "next_step", "report")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    parser.add_argument("--repo", type=Path, help="verify cited source paths under this root")
    args = parser.parse_args(argv)
    if args.repo is not None and not args.repo.is_dir():
        print(f"INVALID: repo is not a directory: {args.repo}", file=sys.stderr)
        return 2
    try:
        if args.report.stat().st_size > 2_000_000:
            fail("report", "file is too large (maximum 2 MB)")
        with args.report.open("r", encoding="utf-8") as f:
            report = json.load(f)
        validate(report, args.repo)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"INVALID: {exc}", file=sys.stderr)
        return 1
    print("VALID: report shape and path references check out. Claims are not independently verified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
