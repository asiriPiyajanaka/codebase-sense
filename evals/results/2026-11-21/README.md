# Evaluation record — 2026-11-21

**Result: a locally checked v0.2.0-rc.1 candidate, with no demonstrated superiority.**
The audits found useful defects, preserved appropriate designs, and proposed
specific outcome-based tests. The no-skill baseline and reference also performed
well. This small case series cannot establish that Codebase Sense is more accurate
or makes engineers understand software better.

## Method and provenance

- [Protocol](../../PROTOCOL.md) recorded the oracle and release criteria before trials.
- [Case prompts](../../cases.json) were identical for the overlapping audit tasks.
- [Source pins](../../sources.json) identify immutable archives and SHA-256 hashes.
- Initial skill: repository commit `bfccbc2`, metadata version 0.1.0.
- Reference: mattpocock/skills `abeeaf95660ba9e8b7c753eb38f441ca707a8823`, with
  codebase-design and supporting references available locally.
- Candidate A/B: preserved instruction snapshot, whose file hashes are in
  [candidate-snapshot-hashes.json](candidate-snapshot-hashes.json). The final skill
  additionally distinguishes a violated invariant in schema 1.1; that final
  structured-report check was completed by the primary agent.
- Fresh agent context per arm; cases within an arm share context. Same inherited
  model/tool access, no explicit model override. The delegation interface did not
  expose an exact model identifier, token totals or reliable latency telemetry.
- Reference adaptations: direct dependency-file loading instead of a `Skill`
  tool, no nested agents or window opening, HTML plus Markdown in scratch storage,
  no interactive design phase. Native visual/interactive usefulness was not compared.
- Cases used separate source copies. [Target integrity](target-integrity.json)
  records zero changed files in every audit/review/verify target copy, including
  interrupted runs. Implementation was authorized only in a disposable fixture.

## Case-level findings

| Case | v0.1.0 | Reference | No skill | Candidate A / B |
| --- | --- | --- | --- | --- |
| Checkout | Finds retry duplication, payload conflict, partial commit | Same three defects | Same three defects | Both find all three; recommend behavioral regressions and one persistence owner |
| Ledger | Keep intentional facade/adapter seam | Keep | Keep | Both Keep; specific additional failure/concurrency tests |
| Click 8.1.8 invocation | Finds exceptional-cleanup context leak; parse failures left unverified | Reproduces cleanup leak and abandoned cleanup after parse failure | Reproduces both failures | A reproduces cleanup leak; leaves parse-failure paths unverified |
| Flask 3.1.2 error dispatch | Keep existing dispatch; clarify precedence and failure tests | Keep; targeted precedence/failure tests | Keep; targeted tests | A Keep; specific precedence and handler-failure tests |

The controlled ledger case produced **no forced architectural rewrite** in any
condition. That is evidence of restraint on this case, not a general false-positive
rate. Real snapshots have no exhaustive defect oracle; supported findings were
adjudicated individually rather than assigned fabricated precision/recall scores.
The reference and no-skill arms investigated one Click failure that candidate A
did not reproduce. The case series therefore gives no basis for claiming superiority.

Candidate B also exercised modes outside the reference comparison:

| Case | Observed outcome |
| --- | --- |
| Authorization review | Reproduces service/export privacy bypass and recommends restoring the shared guard; no new authorization service |
| Blocked verification | Reports setup failure, zero executed tests and missing persistence evidence; does not install or fake infrastructure |
| Incomplete adapter | Investigate; does not infer a broken adapter or certify unavailable code as sound |

The primary agent independently reran the checkout, authorization and both Click
counterexamples. [Commands](primary-checks/commands.json) and outputs are preserved.
The existing fixture suites pass despite the checkout and authorization defects,
demonstrating why test presence alone is insufficient. Proposed test cases target
durable rows, payload identity, response shape, denial, cleanup and observable
exception outcomes. This evaluates their relevance; it does not prove every
proposed test was implemented or will catch all regressions.

## Runtime checks and retained failures

- Checkout existing suite: 2 passing tests; ledger: 5; authorization: 1. These
  counts are not architectural quality scores.
- Click selections differed by arm: v0.1.0 163 passes; reference 160 passes plus
  1 xfail, then 3 selected passes; baseline 154 passes plus 1 xfail; candidate A
  141 passes. Different selected suites prevent a test-count comparison.
- Flask v0.1.0/baseline/candidate A selected 30 passing tests. Reference's broader
  run had **1 failure, 217 passes, 2 skips**; its focused set had 206 passes.
- The failed Flask malformed-host test expected 400 but observed 404. The primary
  reran it and reproduced the failure. Root cause remains unknown; it was not
  silently counted as green or assumed to be a dependency bug. No Flask code changed.
- Runtime environment: CPython 3.12.13, pytest 8.4.2, Click 8.1.8, Flask 3.1.2,
  Werkzeug 3.1.9, Jinja2 3.1.6, MarkupSafe 3.0.4, itsdangerous 2.2.0, blinker 1.9.0.
  Tests imported the pinned source snapshots using PYTHONPATH. Full commands are
  in raw reports. This records observed versions rather than a complete portable
  environment lock.

## Interrupted passes and implementation demonstration

Account usage limits interrupted candidate A's final notification after all four
reports were saved, the implementation worker before source changes, and the
final structured-report worker before reports were written. Candidate B and the
initial/reference/baseline arms completed. Partial final-schema execution logs
are retained under `raw/final-schema/`; they are not presented as a completed
independent trial.

The implementation worker wrote real SQLite regression tests before interruption.
The primary agent reran them against the original fixture (14 tests, failure
records retained), implemented the bounded capability in the disposable copy,
and obtained 14 passing tests. The prewritten independent oracle also passed.
See [implementation/README.md](implementation/README.md) for code, red/green
results, transaction compatibility changes and limitations. **This is a primary
agent implementation demonstration, not proof the skill independently completed
an implementation.** The final schema-1.1 report was likewise completed and
validated by the primary agent under `primary-checks/checkout-report.json`.

## Package and installation checks

The package passes the bundled skill-creator validator and the repository's
YAML-aware metadata/UI/reference checker. `skills@1.9.0` installed a copy into an
isolated project's `.agents/skills/codebase-sense`. Local Codex CLI 0.165.0
`skills/list` discovered it as enabled, repo-scoped, with its expected description
and UI prompt; [discovery response](codex-discovery.json). No model call was needed.
The first sandboxed discovery attempts were blocked by local runtime state/OS
permissions; the successful local smoke directed state/logs to scratch storage.

[validation.json](validation.json) records final deterministic checks on Python
3.9, 3.12 and 3.14. Release-archive checks are recorded in the local release handoff.
GitHub-hosted Actions has not been run by this work; local matrix execution does
not establish that a hosted run already passed.

## Limits and next evidence

This is one exploratory, non-randomized, same-model series, adjudicated by the
primary agent. No independent human reviewers, real engineer comprehension tasks,
live production deployment, full multi-repository test certification, or
statistical superiority test were performed. Broad architecture recall is unknown.
The interrupted independent implementation and final-schema passes should be
repeated when account capacity is available. Those limits are why this is a
pre-release candidate and why the README makes no superiority claim.

No target production source, remote branch, tag, release or issue was changed.

## Raw reports

- [v0.1.0](raw/initial/checkout.md): checkout, ledger, Click, Flask in the same folder.
- [Reference](raw/reference/checkout.md): Markdown, HTML and probe scripts.
- [No-skill baseline](raw/baseline/checkout.md).
- [Candidate A](raw/candidate-a/checkout.md): four overlapping audits.
- [Candidate B](raw/candidate-b/authorization.md): repeat fixtures, review, verify and incomplete evidence.

Raw reports preserve original paths and claims, including verbose output and
failures. Substitute the prepared case path and interpreter when reproducing
commands. Supplemental scripts that locate cases relative to their original job
can also use PYTHONPATH pointing at the prepared fixture or snapshot source.
Reference-derived HTML uses external CDN assets if opened; it was not executed
for these checks. The reference MIT license is retained alongside this record.
