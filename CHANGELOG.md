# Changelog

## 0.2.0-rc.1 — 2026-11-21

Local release candidate; not pushed or published by the release-preparation work.

### Changed

- Distinguish a justified Keep decision from missing evidence that requires investigation.
- Define verification mode and require actual check results before calling a guarantee verified.
- Report schema 1.1 can label a demonstrated invariant violation; legacy 1.0 reports remain accepted.
- Allow safe existing local checks during audits without authorizing source/configuration changes.
- Preserve existing explicit approval and distinguish current from proposed ownership.
- Permit local fixes, tests and wrapper deletion without requiring a deeper module.
- Clarify retry payload conflicts, transaction ownership and limits of local transactions.
- Remove the default prompt's assumption that an architecture improvement must be found.

### Fixed

- Restore report-validator execution on Python 3.9 with postponed annotations.
- Replace the regex-only package check with YAML-aware metadata, Codex UI and reference validation.
- Make CI checkouts use the skill's required directory name and check Python 3.9, 3.12 and 3.14.
- Pin current GitHub Actions release commits and avoid persisted checkout credentials.

### Added

- Controlled behavioral fixtures and independent business-invariant checks.
- Pinned Click/Flask snapshots, reference-skill provenance, prompts and raw evaluation reports.
- A no-refactor example, a source-backed comparison, and explicit evaluation limitations.
- Deterministic local release packaging with a SHA-256 checksum and an approval checklist.

This candidate does not establish superiority, live-production safety, or improved
human comprehension. See the evaluation record for the observed scope.

## 0.1.0 — Initial package

- Initial skill instructions, supporting references, optional JSON report validator,
  nine validator tests, example, CI configuration and proposed evaluation framework.
- No recorded behavioral comparison or production-repository validation at this point.
