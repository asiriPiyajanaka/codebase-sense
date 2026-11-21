# Contract-driven refactor and feedback protocol

## Behavior first

Capture the existing behavior from code, documentation, and observation. Separate *actual current behavior* from *desired new behavior*. A characterization test may intentionally preserve surprising behavior until a deliberate change is approved.

## Useful test layers

- Pure unit tests: calculations, transformations, deterministic rules.
- **Module boundary tests**: the public promise and business invariants across internal collaborators.
- Integration tests: real persistence / queue / adapter interaction where state consistency matters.
- End-to-end tests: critical user paths, wiring and UI/API integration.

Avoid asserting only that dependencies were called. Where feasible, check durable state, outward result, emitted side effect, or explicit error outcome. Mock genuine external services when necessary but don't mock away the specific coordination bug under examination.

## Test matrix prompts (choose relevant rows)

| Situation | Example promise |
| --- | --- |
| Happy path | completion persists and returns the expected result |
| Input boundary | malformed input is rejected without state changes |
| Retry | duplicate request does not double-charge / double-reward |
| Partial failure | transaction rolls back or compensates as defined |
| Authorization | caller cannot change another user's resource |
| Concurrent action | two requests cannot violate a uniqueness or balance invariant |
| Compatibility | existing clients keep their documented contract |
| Observability | failure can be diagnosed with logs/events without leaking secrets |

## Verification checkpoints

1. **Before**: record targeted tests and actual status (`passed`, `failed`, `blocked`, `not_run`); don't assume existing tests pass.
2. **Test design**: write at least one strong assertion for the invariant at risk, where feasible. A new behavior test can first fail (`red`); an existing-behavior characterization test should start passing (`green`).
3. **Smallest change**: implement only the approved correction. This may be a test, local behavior fix, wrapper removal, or a small caller migration behind a clearer contract. Do not move code merely to deepen a module.
4. **After**: rerun relevant tests and typecheck/lint; run broader tests when available and warranted.
5. **Inspect**: compare semantic diff, external API compatibility, data migration, concurrency and failure behavior. If blocked, don't claim success.
6. **Explain**: update the Sense Card; say what changed, how it was verified, what remains uncertain.

## Stop conditions

Stop and request a decision rather than improvising if the change requires destructive migrations, alters security/authorization guarantees, cannot preserve a confirmed contract, contradicts an ADR, or cannot be verified safely. Never silently edit an unrelated area just to get green tests.

Before proposing transaction ownership, establish whether the caller already owns a transaction. Preserve that contract and test the actual database semantics. A local transaction does not cover a remote charge or message publication; use the project's existing delivery/compensation guarantees rather than promising universal exactly-once effects. Where request identity exists, check that a retry with a different payload is rejected rather than silently returning an unrelated result.

## Measuring improvement without fake precision

Compare the same scenario before and after:

- How many decisions must a caller now make? (show code / signatures)
- Which files must change for one specified business-rule modification? (demonstrate, don't guess)
- Which important invariants have boundary/integration tests? (cite the tests)
- Do unchanged consumers still compile and behave correctly? (run checks)
- Did the refactor add a new unowned dependency or hidden I/O? (inspect)

Fewer files is not a quality metric. A favorable result on one scenario is evidence for that scenario, not proof that the entire codebase improved.
