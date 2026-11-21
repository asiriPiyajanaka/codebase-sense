# Keep an intentional ledger boundary

This example uses the bundled, synthetic [ledger fixture](../evals/fixtures/ledger).
It is not a report about a production deployment.

```text
SENSE CARD — Transfer ledger units
Scope: Ledger.transfer -> SQLiteLedger.transfer | Mode: audit
Promise: Transfer positive units atomically; exact retries move units once.
Flow: Ledger input validation -> SQLite transaction -> balances + receipt
Owner: Ledger validates input; SQLiteLedger owns persistence and request identity.
Change entry point: SQLiteLedger.transfer for rollback or receipt defects.
Guarantees:
  [verified] exact retry, changed-amount conflict, missing-receiver rollback,
             insufficient funds, input boundaries — 5 fixture tests passed.
  [unknown] separate-connection concurrency — not in the fixture suite.
Unknown: independently maintained PostgreSQL adapter.
Decision: Keep — the public contract is narrow and the adapter seam is intentional.
Next action: No architectural change recommended for this inspected workflow.
```

Recorded check: `python3 -m unittest discover -s tests -v`, executed from
`evals/fixtures/ledger` on 2026-11-21. The existing tests establish those specific
in-memory SQLite cases; they do not verify every adapter or concurrent execution.
The full structured example is [keep-report.json](keep-report.json).
