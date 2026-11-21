# Release candidate handoff

Candidate: **v0.2.0-rc.1**, prepared 2026-11-21.

The pre-release version reflects a changed workflow and a small exploratory
evaluation. It is not a production-readiness certification. Human comprehension
and independent multi-model replication remain open research questions. Account
usage limits interrupted the independent implementation and final-schema passes;
primary-agent checks completed the demonstration, and the evaluation record
separates those results from independent trials.

## Review before approval

- Read [the changelog](../CHANGELOG.md), [comparison](comparison.md) and
  [evaluation results](../evals/results/2026-11-21/README.md).
- Review the complete working-tree diff and deterministic check results.
- Confirm the intended public repository and installation command.
- Inspect the clean release zip, extracted checks and SHA-256 checksum.

## Local artifact

Run `python3 scripts/package_release.py /tmp/codebase-sense-release` from the
repository. The script refuses to overwrite an existing versioned archive.
The archive has a `codebase-sense/` root to preserve the Agent Skills directory
name requirement. It excludes git internals and virtual environments.

## Publication boundary

No commit, tag, remote push, GitHub release, issue, or external message is created
by the preparation scripts. Obtain the owner's approval of the final diff and
release notes before creating or pushing the release.

After approval, commit the reviewed files, tag the approved commit, push the
branch and tag, and create a GitHub **pre-release** with the zip and checksum.
Use [release-notes.md](release-notes.md) as the draft body. Keep the version in
SKILL.md, changelog, tag, archive and release title consistent.
