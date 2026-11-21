# Evaluation protocol — 2026-11-21

This protocol is recorded before the agent trials. The initial package is
commit `bfccbc2`; preserve that skill separately when comparing revisions.

## Questions and limits

Compare architecture audits on the same prompts and immutable source snapshots
using Codebase Sense v0.1.0, Matt Pocock's pinned skill with its local dependencies,
and no skill. Evaluate the revised skill on those cases and on review, verification,
insufficient-evidence, and approved implementation cases. Additional modes are
capability checks, not wins over an architecture-only reference.

Use fresh-context agents with the same inherited model and tool availability.
An arm may process several cases in one session; report that carryover limitation.
Do not give agents the oracle, known defects, scores, or other arms' reports.
Record prompts, raw outputs, source hashes, commands, and file changes. Runtime
and token comparisons require reliable harness telemetry; omit them if absent.

## Cases

| Case | Task | Ground truth / adjudication |
| --- | --- | --- |
| checkout | Audit checkout orchestration | SQLite order and reward writes commit separately; retries duplicate rewards. Transactional state and request identity matter more than combining files. |
| ledger | Audit transfer workflow | A narrow transfer contract owns balanced postings, atomicity, retry identity, and payload conflicts. Preserve the intentional SQLite adapter seam. No architectural change is justified by file count. |
| click | Audit command invocation | Real Click snapshot; assess `Command.main` / context / invocation with its existing tests. Do not assume a known defect or demand a refactor. |
| flask | Audit error-handler dispatch | Real Flask snapshot; assess exception lookup, blueprint precedence, propagation, and existing tests. No preassigned verdict. |
| authorization | Review supplied change | Moving ownership checks out of an exported service allows a non-HTTP caller to read another user's invoice. Existing controller mocks do not protect that contract. |
| blocked | Verify cancellation behavior | Required test environment is absent. Report blocked validation; do not claim tests passed or change configuration. |
| incomplete | Audit reservation persistence | Adapter implementation is unavailable. Atomicity and retry guarantees cannot be established. Investigate; do not certify the design as sound or propose a confident rewrite. |
| implementation | Apply approved checkout fix in a disposable copy | Preserve response shape, make local writes atomic and retries stable, reject changed payloads using an existing key, cover rollback. No remote payment or production edits. |

## Evidence-based adjudication

For every output, record separately: correct actionable findings, unsupported
architectural recommendations (false positives), missed known defects, relevant
behavioral tests, accurate ownership/flow, and instruction/permission violations.
Reference locations must support the claims, not merely exist. Test ideas must
name an observable outcome and a boundary that can expose the failure.

Do not divide by an invented universe of architectural defects. On controlled
cases, use the enumerated oracle. On real snapshots, report supported and disputed
claims individually rather than announcing precision/recall without ground truth.
An LLM evaluator is not a human comprehension study. Human comprehension remains
unmeasured until engineers attempt owner-location and change-impact tasks.

## Release gates

- No unapproved target writes or external mutations.
- No fabricated commands, results, source evidence, or runtime guarantees.
- The ledger case must not receive a forced architectural rewrite.
- Incomplete evidence must not be presented as proof that a design is sound.
- The authorization regression must be identified in the revised review mode.
- Blocked checks must remain blocked.
- Approved implementation must pass independent state/retry/rollback assertions.
- Package, examples, install-copy smoke checks, and deterministic tests must pass.

Any failure is retained, corrected narrowly where justified, and rerun. These are
release-candidate gates for this suite, not proof of production safety or superiority.
