# Codebase Sense

**Keep building fast. Never lose the system.**

An open agent skill to help software engineers stay oriented in growing, agent-generated codebases. It traces real feature behavior, identifies architectural friction, proposes *justified* deep-module improvements, and prioritizes meaningful tests over green checkmarks that prove little.

> It is not an autonomous rewrite bot. Default behavior is read-only, and the skill is allowed to recommend **no refactor**.

## What it does

- **Sense**: follow one user-visible workflow from entry point to state change and create a concise **Sense Card** a human can remember.
- **Audit**: find concrete coupling, leaky orchestration, shallow forwarding layers, or hollow tests — with file-based evidence and counterarguments.
- **Plan**: propose the smallest useful module contract and a behavior-driven migration strategy.
- **Implement**: only when explicitly asked, preserve current behavior with tests and make one reversible slice at a time.
- **Review**: evaluate agent-generated PRs based on contracts, invariants, test strength, and architectural drift.
- **Verify**: distinguish genuinely checked behavior from untested assumptions.

No dependency on another skill, language, IDE, or remote service. The optional JSON report validator uses Python's standard library.

## Why this exists

An AI agent can successfully implement a feature while making it harder for the next engineer to understand what owns that behavior. Codebase Sense focuses on **maintaining human comprehension** as well as improving architecture. Deep modules are useful when they absorb meaningful coordination; they aren't a reason to merge everything into enormous classes.

### Example

**Before:** A level-completion controller calls validation, scoring, progress, rewards, and unlocking services and owns the order of the calls.

**After (only if justified):** A `completeLevel` capability owns the full completion guarantee behind a stable contract. A boundary/integration test verifies that retrying a completed request cannot award points twice. The card tells the engineer where to look if the invariant fails.

The recommended change isn't automatically better: if the original responsibilities are properly separated and failure handling is already correct, the result may be **Keep**.

## Install locally

Use the [skills CLI](https://www.skills.sh/) from the folder containing this repository:

```bash
npx skills add ./codebase-sense --skill codebase-sense
```

Or copy the `codebase-sense/` directory to the Codex user skill directory:

```bash
mkdir -p ~/.agents/skills
cp -R ./codebase-sense ~/.agents/skills/codebase-sense
```

> When using the skills CLI from **inside** this repository, use `npx skills add . --skill codebase-sense` instead. Codex can also load a repo-scoped copy under `.agents/skills/codebase-sense/`.

## Public install (after publishing on GitHub)

Replace `YOUR_GITHUB_HANDLE` with your actual GitHub username and push this folder as a public repository named `codebase-sense`:

```bash
npx skills add YOUR_GITHUB_HANDLE/codebase-sense --skill codebase-sense
```

This is a **future command template**, not a live repository URL. Once the public repository exists, share the real command in the article.

## Usage in Codex

Mention `$codebase-sense` and a specific scope in the prompt:

```text
Use $codebase-sense to trace the purchase completion flow.
Show who owns the retries, transaction boundaries, and error states.
Don't modify code.
```

```text
Use $codebase-sense to review this PR. Identify changes to public
contracts, missing behavioral tests, and any new orchestration leakage.
```

```text
Use $codebase-sense to plan a deep-module refactor of the level
completion workflow. Protect existing behavior, but don't implement yet.
```

```text
Use $codebase-sense to implement the approved completion-module plan.
Make a small change, run the repository's relevant tests, then summarize
what is verified and what isn't.
```

## What a Sense Card looks like

```text
SENSE CARD — Complete learning level
Promise: One completion updates progress and awards points once.
Flow: LevelController -> Progress.completeLevel -> transaction -> event
Owner: Progress module
Change entry point: Progress.completeLevel
Guarantees:
  [verified] no duplicate reward on retry — integration test
  [unknown] concurrent submissions cannot both unlock — not tested
Decision: Investigate
Next: add concurrent-submission test before reorganizing services.
```

This is illustrative, not evidence about a real repository.

## Optional evidence report validation

When an agent is asked to output structured JSON, validate the shape and, optionally, its cited paths:

```bash
python3 scripts/validate_report.py examples/learning-progress-report.json
python3 -m unittest discover -s tests -v
```

The validator detects missing report fields and invalid path references; it **does not grade architecture, verify tests, or independently check the truth of a code claim**.

## Benchmark it before calling it better

See `evals/README.md`: run the same repository cases against this skill, an alternative skill, and no skill; compare evidence quality, correctness, legitimate no-change decisions, and engineering comprehension. The initial release has not yet been benchmarked on independent production repositories.

## Attribution and license

The concept of deep modules comes from John Ousterhout's *A Philosophy of Software Design*. This skill is an original workflow, not a fork of Matt Pocock's `improve-codebase-architecture`. His skill is a useful reference point for thinking about architectural friction and effective module boundaries.

MIT licensed. Contributions and test cases are welcome.
