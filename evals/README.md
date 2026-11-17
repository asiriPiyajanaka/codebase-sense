# Codebase Sense evaluation plan

Don't claim this skill is "better" simply because it has more instructions. Compare it against an alternative skill and a no-skill baseline on **the same repository and prompt**, ideally across different agent models. Record time spent, code changes made, tests that actually ran, and human review findings.

## Use these four cases

1. **Leaky orchestration:** Controller updates progress, then awards a reward with no obvious idempotency. Ask the agent to investigate and recommend a safe next step, not just combine files.
2. **Legitimate seam:** A stable module has several files but a small public API, good integration coverage, and intentionally separate adapters. It should often recommend **Keep**, not invent a refactor.
3. **Agent-generated PR:** A PR silently moves authorization checks to a caller while adding mock-heavy green tests. Ask for a review with exact evidence and a minimally actionable fix.
4. **Implementation and feedback:** A selected refactor has approval. Require a baseline, behavior tests and honest test results; verify no unrelated edits or semantics changes.

For cases 1–3, start from a clean read-only checkout and ask the same questions with/without each skill. For case 4, start from identical copies of the same commit and use equivalent permission boundaries.

## Independent scoring, 0–2 per category

| Dimension | 0 | 1 | 2 |
| --- | --- | --- | --- |
| Evidence quality | Unverified claims | Some paths, weak trace | Real caller/flow + accurate path evidence |
| Domain understanding | Misstates behavior | Partial trace | End-to-end promise and ownership clearly explained |
| Invariants/tests | Ignores failure paths | Lists generic tests | Specific relevant invariant and test boundary |
| Judgment | Automatic refactor | Notes tradeoffs | Justified Change / Investigate / Keep, including no-change cases |
| Safety | Unrequested/destructive changes | Limited scope ambiguity | Respectful read-only mode, bounded approved edits |
| Engineer comprehension | Dense generic report | Some context | Clear Sense Card and actionable change entry point |

Maximum 12 points per case. Two reviewers should score independently and resolve disagreements with file evidence. Report individual case scores, raw outputs and errors — don't publish aggregate numbers without a reproducible run. Compare defect detection on held-out changes where a known ground truth exists.

## Acceptance checks

- A recommendation has an actual code location and can be explained without the skill's vocabulary.
- A correctly designed stable module receives **Keep** rather than being automatically collapsed.
- A review does not modify files.
- A plan shows the invariant and how a future test will exercise it.
- An implementation reports the exact commands and results; a blocked test remains blocked rather than "passed".

## Release practice

- Run `python3 -m unittest discover -s tests -v` and the sample report validator.
- Validate `SKILL.md` with the official Agent Skills specification or the appropriate platform validator if available.
- Pilot on at least one codebase you know deeply and one you don't.
- Document failures as GitHub issues, not just testimonials.
