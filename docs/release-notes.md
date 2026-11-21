# Codebase Sense v0.2.0-rc.1

**Keep building fast. Never lose the system.**

Codebase Sense helps engineers trace behavior, find ownership, assess architecture
and protect business guarantees while coding agents implement changes.

This candidate clarifies no-change decisions, adds explicit verification guidance,
fixes Python 3.9 report validation, and introduces controlled fixtures plus audits
of pinned Click and Flask source snapshots. Package validation checks actual YAML,
Codex metadata and linked resources.

Read-only analysis is the default. Implementation needs explicit approval, and a
test addition or local correction can be the right outcome without a refactor.

See the evaluation record for raw reports, commands, failures and limitations.
The study does not demonstrate superiority over Matt Pocock's reference skill or
a no-skill baseline, and it does not measure human comprehension or live production.
Account usage limits interrupted two independent passes; their primary-agent
follow-up checks are labeled separately in the evaluation record.

Install from the reviewed release archive into a directory named `codebase-sense`
under your project's `.agents/skills/`, or use the repository installation command
after the approved source is public. Python 3.9+ is needed only for the optional
report validator; the instructions themselves need no remote service.

This is a pre-release for feedback on real workflows. Include a bounded prompt,
source commit, actual output and expected behavior when reporting a problem.
