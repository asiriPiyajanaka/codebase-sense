# PR review: keep the engineer in control

Start with the intended change and the actual diff. Respect the user's requested focus; don't create a new architecture agenda during review.

1. **Behavior:** What user-visible guarantee changed? Is the diff consistent with the request?
2. **Responsibility:** Is there one place accountable for sequencing, validation, and state consistency? Or is responsibility intentionally split?
3. **Public contract:** Do new exports make callers depend on internal decisions? Is the interface smaller to understand than its implementation?
4. **Failures and retries:** Are partial updates, duplicate messages, timeouts, races, and errors preserved or explicitly changed?
5. **Security and data:** Does authorization remain at the correct layer? Are secrets, sensitive data, and migrations treated appropriately?
6. **Tests:** Do tests prove a result/invariant, or only mocked calls? Was the targeted suite actually run? Is an integration check needed?
7. **Explainability:** Can a human follow the changed workflow from entrypoint to effect and name the owner?
8. **Scope:** Did the agent add unrelated abstractions, dependencies, config, or cleanup?

## Findings format

`[severity] path:line — risk → concrete scenario → suggested smallest correction`

Severity: `blocker` (proven serious regression/security/data issue), `high` (credible incorrect behavior), `medium` (important design or test hole), `low` (minor maintainability). Avoid making certainty sound stronger than evidence. End with `Unverified` and a compact Sense Card. If no meaningful findings, say so; don't invent criticism.
