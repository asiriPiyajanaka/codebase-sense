# Sense Card — compact output template

Use inline by default, not a repository document. One meaningful workflow per card. Limit the normal card to about a screenful; expand only when needed.

```text
SENSE CARD — <capability>
Scope: <bounded area> | Mode: <audit / plan / implement / review / verify>
Promise: <observable result>
Flow: <entrypoint> -> <domain decision> -> <stateful/external effects>
Owner: <current module; label proposed ownership separately> | Evidence: <path:symbol / line>
Change entry point: <what to open first if X goes wrong, and why>
Guarantees:
  [verified / violated / missing / unknown] <invariant> — <evidence; command/result if executed>
  ...
Unknown: <what the inspection did not prove>
Decision: Change / Investigate / Keep — <reason>
Next action: <smallest justified action, or no change>
```

## Example, illustrative only

```text
SENSE CARD — Complete learning level
Promise: One successful completion records progress and awards points once.
Flow: LevelController.complete -> Progress.completeLevel -> DB transaction -> reward event
Owner: Progress module
Change entry point: Progress.completeLevel, where completion idempotency is enforced.
Guarantees:
  [unknown] retry does not duplicate points — progress.integration.spec.ts exists; not run
  [unknown] DB error cannot leave partial progress — transaction boundary not inspected
Unknown: multi-device concurrent submissions
Decision: Investigate — need concurrent-submission test before proposing a refactor.
Next action: inspect transaction behavior and run an idempotency integration test.
```

This is a **template**, not a claim about any real project. Replace every identifier with observed evidence, or state `unknown`. A Sense Card is not an exhaustive dependency diagram: its purpose is for a human to recover orientation quickly.
