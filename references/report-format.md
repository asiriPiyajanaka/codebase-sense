# Optional machine-checkable report

This format is **optional**; default to inline Markdown. Produce JSON only when requested by the user or a host workflow. Run:

```bash
python3 scripts/validate_report.py REPORT.json
python3 scripts/validate_report.py REPORT.json --repo /path/to/repo
```

`--repo` verifies that cited source paths resolve within that repository and exist. It cannot verify that an assertion is correct or that a test passes. A line number is optional when no stable line number is available. A sample lives in `examples/learning-progress-report.json` (fictional, so validate it without `--repo`).

Fields:
- `schema_version`: `"1.0"`
- `scope`, `mode`, `summary`: non-empty strings; `mode` one of `audit`, `plan`, `implement`, `review`, `verify`
- `workflows`: at least one entry with `name`, `promise`, `entry_point`, `trace` (each `{path, symbol, role}`), `owner`, `change_entry_point`, `invariants` (each `{statement, status, evidence}`), `unknowns`
- `candidates`: zero to three; each has `id`, `title`, `recommendation` (`change`, `investigate`, `keep`), `reason`, `counterargument`, `evidence`, `possible_contract`, `test_implication`, `next_step`
- `verification`: `{checks: [{command, status, details}], unverified: [string]}` with status `passed`, `failed`, `blocked`, `not_run`
- `next_step`: non-empty string
- `evidence` entries: `{path, symbol?, line?, detail?}`; cited paths must be relative to the repository root, not absolute, and must not traverse outside it

`status: "verified"` for an invariant requires at least one evidence entry; `missing` and `unknown` may have none. Validator enforces these structural rules, but the report author must be honest about what the evidence establishes.
