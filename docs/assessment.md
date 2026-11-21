# Repository assessment and resolution

Initial review covered all 16 tracked files at `bfccbc2` before edits. The nine
original tests checked report validation, not architectural judgment. They and the
sample passed on Python 3.12, but the documented command failed on Python 3.9.

| Priority | Finding | Resolution / evidence |
| --- | --- | --- |
| P0 | Keep could mean either sound design or failed evidence gate | Keep now requires inspected support; material missing evidence means Investigate; incomplete-adapter trial follows this distinction |
| P0 | Verify mode was named without an execution workflow | Added safe command discovery, exact result reporting, blocked-environment handling and tested-boundary limits; blocked trial reports zero executed tests |
| P0 | A cited test could be mistaken for verified behavior | Defined actual passed-check evidence; schema 1.1 adds violated for counterexamples; report validator explicitly does not prove claim truth |
| P0 | Evaluation framework had no executable cases or recorded reports | Added controlled repositories/oracles, source pins, prompts, raw reports and candid adjudication |
| P1 | Refactor protocol prescribed moving coordinated behavior | Allows tests, local fixes and wrapper deletion; preserves appropriate modules and remote-effect limits |
| P1 | Default prompt assumed an improvement must exist | Prompt now asks whether a change is justified; all controlled ledger audits retain the seam |
| P1 | Regex-only check could accept invalid YAML and reject valid quoted/block values | YAML-aware package checker plus rejection and portability tests; UI metadata and skill references checked |
| P1 | Python 3.9 failed on evaluated union annotations | Postponed annotations; local compatibility checks and CI matrix cover 3.9/3.12/3.14 |
| P1 | CI depended on the repository's checkout directory name | Checkout now explicitly uses codebase-sense, matching the specification |
| P1 | CI used older action runtimes and mutable major tags | Pins checkout v7.0.1 and setup-python v7.1.0 to verified release commits; credentials are not persisted |
| P1 | Public install instructions retained a username placeholder | Uses the configured origin owner, explicit publication status and isolated tested local installation |
| P1 | Outputs repeated the same trace across long templates | Added guidance to use one card and avoid repetition; no claim of measured comprehension improvement |
| P2 | No changelog, release notes or clean versioned artifact | Prepared rc.1 changelog, draft notes, deterministic packager and publication approval boundary |

The package uses the current [Agent Skills fields](https://agentskills.io/specification)
and [Codex local skill layout](https://learn.chatgpt.com/docs/build-skills).
`agents/openai.yaml` remains optional product metadata; implicit invocation stays
enabled by default. No dependency on another skill or a particular agent-only tool
was introduced. A minimal MIT skill can be distributed as a folder; a separate
plugin bundle is not required for this repository's scoped release preparation.

Action pins were checked against the official
[checkout release](https://github.com/actions/checkout/releases/tag/v7.0.1) and
[setup-python release](https://github.com/actions/setup-python/releases/tag/v7.1.0)
and their Node 24 action manifests. The workflow targets GitHub-hosted
`ubuntu-latest`; it has not yet been executed on GitHub by this work.

The [comparison](comparison.md) separates instruction differences from observed
results. Primary adjudication and usage-limit interruptions are disclosed in the
[evaluation record](../evals/results/2026-11-21/README.md). No superiority or
live-production validation claim is made.
