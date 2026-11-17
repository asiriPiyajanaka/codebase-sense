---
name: codebase-sense
description: Preserve an engineer's understanding of a changing codebase. Use to map a feature's real behavior and ownership, investigate shallow or over-coupled modules, plan evidence-backed deep-module refactors, verify behavioral tests, or review agent-generated PRs for architectural drift. Default to a read-only audit; make code changes only when explicitly requested. Not for generic formatting or simple one-file edits.
license: MIT
metadata:
  version: "0.1.0"
---

# Codebase Sense

Keep building fast without losing the system. Optimize for **explainable ownership, narrow contracts, verified behavior, and safe changes**, not maximum abstraction or minimum file count.

## Entry and scope

Interpret the user's intent; do not expand it:

| Invocation / intent | Mode | Writes? |
| --- | --- | --- |
| `codebase-sense [area]`, "help me understand", "find shallow modules" | **sense + audit** | No |
| `codebase-sense plan [area]`, "design a refactor" | **plan** | No, unless asked for an RFC file |
| `codebase-sense implement [area]`, "apply the refactor" | **implement** | Yes, within approved scope |
| `codebase-sense review [diff or PR]`, "review AI-generated changes" | **review** | No |
| `codebase-sense verify [area]` | **verify** | No, except generated test artifacts if explicitly asked |

When unclear, use **sense + audit**, never automatic refactoring. A PR review is a review, not permission to fix code. State the scope and chosen mode at the start.

## Shared operating rules

1. Read repository-specific instructions (`AGENTS.md`, equivalent), module docs, domain glossary and relevant ADRs. Respect prior architecture decisions; note contradictions rather than silently replacing them.
2. Inspect the current working tree before touching files. Do not reset, clean, rebase, delete unrelated work, install tools, publish, open issues, or contact external services without explicit authorization. Avoid commands with side effects in audit/review modes; read-only git inspection is acceptable if available.
3. Anchor claims to **actual repository evidence**: `path:symbol` and line number when available, relevant callers, tests, or a reproduced failure. Mark deductions *inferred* and gaps *unknown*. Never claim code was run if it was not.
4. Prioritize a **single user-visible workflow**, bounded by the user's requested area. Prefer recent change hotspots only when git history is available and relevant. Do not scan an entire monorepo by default.
5. Consider security, privacy, authorization, idempotency, transactions, concurrency, error semantics, data integrity, performance, and compatibility as applicable; do not invent requirements.
6. **A deep module hides difficult decisions behind a simple contract.** More files, fewer files, more classes, or fewer classes are not goals. Don't create a "god module" or collapse genuine independently evolving responsibilities.
7. Some code should remain as-is. Always give a reasoned **keep / investigate / change** outcome; weak evidence means `investigate`, not a confident refactor proposal.

## Sense pass: trace before judging

For the one workflow, construct an evidence-based **Sense Card**:

- **Promise:** What can the user or caller expect to happen?
- **Entry -> decisions -> effects:** Trace the real path through the code. Separate external I/O from domain rules.
- **Owner:** Which module should be accountable for the workflow's consistency? State if ownership is split or uncertain.
- **Invariants:** What must stay true across failure, retries, and edge cases? Link to existing evidence/tests and mark each `verified`, `missing`, or `unknown`.
- **Change entry point:** If a bug or rule change landed tomorrow, where should an engineer look first and why?
- **Unknowns:** Say what could not be established without further inspection or execution.

Load `references/sense-card.md` for the output structure. Keep the result short enough for an engineer to retain mentally. Do not generate an exhaustive architecture diagram for its own sake.

## Audit: recommend changes only where they pay off

Inspect only proven friction around the workflow:

- Does a caller have to orchestrate steps that should be atomic within one capability?
- Does understanding or modifying one domain rule require crossing many unrelated modules?
- Does a thin wrapper merely rename or forward methods without hiding complexity?
- Are policy decisions duplicated among callers? Do interfaces leak storage, sequencing, or failure details?
- Do tests assert mocked calls while the workflow's real invariants are unprotected?

Read `references/decision-rubric.md`. For at most **three candidates**, show observed friction with evidence, a counterexample or reason to keep the design, possible contract, risks, test implications, and a `change / investigate / keep` recommendation. Do not assign invented numeric complexity scores. If nothing merits refactoring, say so.

**Stop after audit or plan unless implementation was explicitly requested.** Do not make a code change just because you identified a candidate.

## Plan: make the contract reviewable

For a selected candidate:

1. State the existing user-visible behavior and compatibility constraints.
2. Propose the **smallest useful public contract** with a caller example; describe what decisions become internal and what stays outside.
3. Provide a simple before/after call-flow sketch; label it proposed, not implemented.
4. Create a **behavioral test matrix**: success, failure, retry/idempotency, boundary conditions, authorization, and concurrency as relevant. Prefer boundary/integration tests where coordination bugs live; retain useful lower-level tests.
5. Define a sequence of small, reversible slices, including old-client compatibility, migration, rollback path, and a stop condition.
6. Give a specific verification plan using commands found in the repo; never invent runnable scripts.

Read `references/test-and-change-protocol.md` for the details. Ask for the user's choice before implementing if they requested planning only.

## Implement: protect behavior before moving code

Only enter when the user explicitly asked to change the code.

1. Confirm the expected scope, relevant dirty files, and observable pre-change behavior. If pre-change tests are missing, establish at least one characterization or contract test where practical; **don't invent passing baselines**.
2. Prefer red -> green -> refactor: demonstrate failure of new behavior tests when relevant, implement the smallest cohesive slice, then re-run relevant tests. Existing behavior preservation may instead call for green-before/green-after characterization tests.
3. Change the callers incrementally, avoid unrelated rewrites, preserve error handling and transaction semantics. Do not silently redefine the public contract.
4. Run available targeted tests, then broader relevant checks when possible. Report each result and any environment blocker. Never equate mock-heavy green tests with verified end-to-end behavior.
5. Review the diff for hidden coupling, changed behavior, dead code, and accidental scope expansion. Stop if the design breaks a proven invariant, demands unsafe migration, or cannot be verified; report blockers instead of forcing a change.
6. Provide an updated Sense Card in the final reply. Write documentation into the repo **only when requested** or when documentation is explicitly in implementation scope.

## Review: act as the codebase's memory

For a supplied diff or PR, trace each changed public behavior to its callers, contracts, and tests. Prioritize genuine correctness and maintainability risks over style. Report each finding with severity, path/line evidence, how to reproduce or observe it, and what guarantee is at risk. Include **what remains understandable**, meaningful unknowns, and a concise updated Sense Card. Don't claim full repository coverage from a small diff. Read `references/review-checklist.md`.

## Output / evidence quality gate

Always finish with:

1. A concise Sense Card (or changes to the prior one).
2. `Change`, `Investigate`, or `Keep`, and why.
3. Behavioral guarantees that were actually checked vs. not checked.
4. The next smallest justified action, or "No change recommended."

**Evidence gate:** If you cannot identify a real caller, a real behavior, and at least one concrete risk or invariant, do not confidently propose a refactor. If proposed work increases the number of concepts callers must understand without a clear payback, reject or revise it.

For a machine-checkable optional report, use `references/report-format.md`. Resolve the directory containing this `SKILL.md` before running `python3 <skill_dir>/scripts/validate_report.py REPORT.json [--repo REPO_ROOT]` from a target repository. The validator checks report shape and file references, **not** code correctness or architectural quality. Do not create report files unless asked.
