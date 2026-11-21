# Optional machine-checkable report

This format is **optional**; default to inline Markdown. Produce JSON only when requested by the user or a host workflow. Run:

```bash
python3 scripts/validate_report.py REPORT.json
python3 scripts/validate_report.py REPORT.json --repo /path/to/repo
```

`--repo` verifies that cited source paths resolve within that repository and exist. It cannot verify that an assertion is correct or that a test passes. A line number is optional when no stable line number is available. A sample lives in `examples/learning-progress-report.json` (fictional, so validate it without `--repo`).

Fields:
- `schema_version`: `"1.1"`; the validator also accepts legacy `"1.0"` reports, which do not support the `violated` invariant status
- `scope`, `mode`, `summary`: non-empty strings; `mode` one of `audit`, `plan`, `implement`, `review`, `verify`
- `workflows`: at least one entry with `name`, `promise`, `entry_point`, `trace` (each `{path, symbol, role}`), `owner`, `change_entry_point`, `invariants` (each `{statement, status, evidence}`), `unknowns`
- `candidates`: zero to three; each has `id`, `title`, `recommendation` (`change`, `investigate`, `keep`), `reason`, `counterargument`, `evidence`, `possible_contract`, `test_implication`, `next_step`
- `verification`: `{checks: [{command, status, details}], unverified: [string]}` with status `passed`, `failed`, `blocked`, `not_run`
- `next_step`: non-empty string
- `evidence` entries: `{path, symbol?, line?, detail?}`; cited paths must be relative to the repository root, not absolute, and must not traverse outside it

`status: "verified"` for an invariant requires at least one evidence entry. The author must also identify an actually passed relevant check in `verification.checks` and explain its boundary; citing source or an unrun test is insufficient. `violated` requires evidence of a concrete counterexample; a successful reproduction script may exit zero while demonstrating a violated guarantee, so explain what it asserted. `missing` means a demonstrated coverage gap, while `unknown` includes unrun checks and incomplete inspection. The validator enforces shape and references, not this semantic relationship or the truth of execution claims.
