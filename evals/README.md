# Codebase Sense evaluation plan

The recorded [2026-11-21 evaluation](results/2026-11-21/README.md) includes raw
outputs and limitations. It is exploratory; it is not a statistically powered
benchmark or a human comprehension study.

## Reproduce the inputs

Read [PROTOCOL.md](PROTOCOL.md) before evaluating. [cases.json](cases.json)
contains the exact case prompts; keep the protocol's oracle out of agents' context.
The synthetic repositories are under `fixtures/`. Each case is a separate working
directory, not a test package to merge into one Python import path.

```bash
python3 evals/check_fixtures.py
# Network access and Python 3.12+; creates a new directory and executes no source:
python3.12 evals/prepare.py /tmp/codebase-sense-inputs
```

`sources.json` pins archive URLs, commits and SHA-256 hashes for the reference,
Click 8.1.8 and Flask 3.1.2. The download script checks hashes before extracting.
Do not replace a pin with a moving branch when reproducing the comparison.

For real-repository runtime checks, provision a separate virtual environment with
`pytest==8.4.2`, `click==8.1.8`, and `Flask==3.1.2`; use `PYTHONPATH=SNAPSHOT/src`
so the inspected source is imported. Record transitive dependencies as well.
Disable bytecode and pytest's cache (`PYTHONDONTWRITEBYTECODE=1`,
`-p no:cacheprovider`), inspect the selected tests for side effects, and keep all
reports outside the target checkout. Full commands and observed environment
failures are preserved with each raw report. The source pins do not pin every
dependency unless a complete environment lock accompanies the run.

Use independent fresh contexts for each condition, the same prompts and allowed
tools, and unchanged case copies. The recorded series uses one agent per arm for
several cases; disclose that carryover and do not treat cases as independent
samples. Compare v0.1.0 using commit `bfccbc2`, the reference at its pinned commit,
and a no-skill baseline. Then evaluate the candidate independently. Do not count
Codebase Sense's additional modes as reference-skill failures.

Implementation is allowed only in an explicitly approved disposable fixture copy:

```bash
python3 evals/check_fixtures.py --implementation /tmp/approved-checkout-copy
```

The check asserts response compatibility, exact retries, payload conflicts, rollback
and same-ID recovery. The shipped broken fixture is expected to fail these checks;
that expected failure is not hidden by the ordinary success-path suite.

## Judge outcomes, not instruction count

For controlled cases, check the protocol's known defects and acceptable no-change
outcomes against each report. For real snapshots, reproduce concrete findings and
review architectural recommendations individually; there is no complete defect
oracle. Distinguish relevant test proposals from tests actually executed.

The primary agent adjudicates the recorded case series. This is not independent
human scoring. Do not publish a composite architecture score or claim better
comprehension from the presence of a Sense Card. A future human study should ask
engineers to locate the owner of a guarantee and predict the effects of a rule
change, using comparable tasks without revealing the preferred condition.

Preserve failures and raw outputs. Record issues locally unless the user authorizes
creating GitHub issues. Repeat evaluations on holdout repositories and other
models before making broad claims. Never modify a real target project without
explicit approval, even when an audit identifies a convincing correction.
