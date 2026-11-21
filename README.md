# Codebase Sense

**Keep building fast. Never lose the system.**

An open agent skill to help software engineers stay oriented in growing, agent-generated codebases. It traces real feature behavior, identifies architectural friction, proposes *justified* deep-module improvements, and prioritizes meaningful tests over green checkmarks that prove little.

> “I'm happy to write less code. I don't want to understand less software.”

Release candidate: **v0.2.0-rc.1**. See [CHANGELOG.md](CHANGELOG.md) and the
[evaluation results](evals/results/2026-11-21/README.md) for evidence and limits.

> It is not an autonomous rewrite bot. Default behavior is read-only, and the skill is allowed to recommend **no refactor**.

## What it does

- **Sense**: follow one user-visible workflow from entry point to state change and create a concise **Sense Card** a human can remember.
- **Audit**: find concrete coupling, leaky orchestration, shallow forwarding layers, or hollow tests — with file-based evidence and counterarguments.
- **Plan**: propose the smallest useful module contract and a behavior-driven migration strategy.
- **Implement**: only when explicitly asked, preserve current behavior with tests and make one reversible slice at a time.
- **Review**: evaluate agent-generated PRs based on contracts, invariants, test strength, and architectural drift.
- **Verify**: distinguish genuinely checked behavior from untested assumptions.

The instructions have no runtime dependency on another skill or remote service.
The optional report validator requires **Python 3.9+** and its standard library.
Development/package validation additionally uses PyYAML; evaluation snapshot
downloads use Python 3.12+. Target-project checks use that project's own tools.

## Why this exists

An AI agent can successfully implement a feature while making it harder for the next engineer to understand what owns that behavior. Codebase Sense focuses on **maintaining human comprehension** as well as improving architecture. Deep modules are useful when they absorb meaningful coordination; they aren't a reason to merge everything into enormous classes.

### Example

**Before:** A level-completion controller calls validation, scoring, progress, rewards, and unlocking services and owns the order of the calls.

**After (only if justified):** A `completeLevel` capability owns the full completion guarantee behind a stable contract. A boundary/integration test verifies that retrying a completed request cannot award points twice. The card tells the engineer where to look if the invariant fails.

The recommended change isn't automatically better: if the original responsibilities are properly separated and failure handling is already correct, the result may be **Keep**.

## Install locally

From inside this repository, use the [skills CLI](https://github.com/vercel-labs/skills)
to install a project-scoped copy for Codex:

```bash
npx skills add . --skill codebase-sense --agent codex
```

For an isolated project install without the CLI, copy the package from its parent
directory. The destination must not already exist:

```bash
mkdir -p /path/to/project/.agents/skills
python3 -c 'import shutil; shutil.copytree("codebase-sense", "/path/to/project/.agents/skills/codebase-sense", ignore=shutil.ignore_patterns(".git", "__pycache__", ".venv"))'
```

Replace `/path/to/project` with your project path. For a user-wide install, use
`~/.agents/skills/codebase-sense` instead (expand `~` when using Python).
Codex discovers `SKILL.md` inside `.agents/skills/codebase-sense/`; simply opening
this repository's root `SKILL.md` does not install it. Avoid installing duplicate
copies. See [Codex's skill documentation](https://learn.chatgpt.com/docs/build-skills).

## Public install (after publishing on GitHub)

After this candidate is approved and published, the intended command is:

```bash
npx skills add asiriPiyajanaka/codebase-sense --skill codebase-sense --agent codex
```

This command does not establish that the release candidate is already available
remotely. For reproducibility, use a reviewed release archive or an approved commit.

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
  [unknown] no duplicate reward on retry — integration test exists; not run
  [unknown] concurrent submissions cannot both unlock — not tested
Decision: Investigate
Next: add concurrent-submission test before reorganizing services.
```

This is illustrative, not evidence about a real repository.

## Optional evidence report validation

When an agent is asked to output structured JSON, validate the shape and, optionally, its cited paths:

```bash
python3 scripts/validate_report.py examples/learning-progress-report.json
```

The validator detects missing report fields and invalid path references; it **does not grade architecture, verify tests, or independently check the truth of a code claim**.

## Benchmark it before calling it better

See [evals/README.md](evals/README.md) for prompts, immutable source pins,
controlled fixtures, raw reports and limitations. Evaluations cover repository
snapshots, not live production deployments. They do not establish superiority
or improved human comprehension.

## Development checks

Use a virtual environment with Python 3.9+:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python scripts/check_skill.py
.venv/bin/python scripts/validate_report.py examples/learning-progress-report.json
.venv/bin/python scripts/validate_report.py examples/keep-report.json --repo .
.venv/bin/python evals/check_fixtures.py
```

CI repeats deterministic checks on Python 3.9, 3.12, and 3.14. Agent evaluations
are explicit, separate runs; a green CI badge does not grade architecture.

## Prepare a release locally

```bash
python3 scripts/package_release.py /tmp/codebase-sense-release
```

This creates a versioned zip and SHA-256 checksum with a `codebase-sense/` root.
It does not commit, tag, push, or publish. See the [release checklist](docs/release.md).

## Attribution and license

The concept of deep modules comes from John Ousterhout's *A Philosophy of Software Design*.
Codebase Sense was inspired by [Matt Pocock's `improve-codebase-architecture`](https://github.com/mattpocock/skills).
See the [comparison](docs/comparison.md) for the pinned reference and differences
in scope. This package does not bundle his skill or claim to outperform it.

MIT licensed. Contributions and test cases are welcome.
