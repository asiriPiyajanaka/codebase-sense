Scope: `Ledger.transfer` through the supplied SQLite adapter. Mode: **audit**. I inspected all four repository files and ran their local SQLite tests. Source and tests were left unchanged; no `AGENTS.md`, ADR, or git metadata was present in this copy.

**Keep the facade/adapter boundary.** The facade owns domain validation, while the adapter already hides the transaction, balance checks, idempotency, and conflict policy behind one operation. `README.md:4–6` explicitly requires this seam because a separately shipped PostgreSQL adapter shares the contract. The facade's short body is not evidence that it should be collapsed into SQLite code.

**Sense Card — transfer**

- **Promise:** a positive integer transfer returns its request ID as a receipt. Replaying the same payload returns that receipt without another transfer; changing that payload is rejected. Balance movements and the receipt are atomic, and balances must remain nonnegative (`README.md:3–11`).
- **Flow:** `ledger.py:Ledger.transfer:5` validates identities and amount, then delegates once to `sqlite_adapter.py:SQLiteLedger.transfer:9`. The adapter starts `BEGIN IMMEDIATE`, looks up the request, compares the entire stored payload, conditionally debits the sender, credits the receiver, and inserts the receipt inside the connection context manager.
- **Current owners:** facade: truthy/distinct identities and strict positive built-in `int` validation (`ledger.py:6–9`). Adapter: serialization, payload binding, conditional debit, missing-account checks, and commit/rollback (`sqlite_adapter.py:10–26`). Schema: nonnegative-balance check and unique request ID (`sqlite_adapter.py:5–6`). Production connection lifecycle belongs to deployments (`README.md:11`).
- **Change entry point:** open `Ledger.transfer` for changes to domain input rules; open `SQLiteLedger.transfer` for persistence, rollback, or retry failures. A shared behavioral change must retain the external PostgreSQL adapter contract.
- **Verified in this run:** an exact replay moves 40 units once and leaves one receipt; a changed-amount retry raises and preserves balances; missing receiver rolls back the debit and leaves no receipt; insufficient funds preserves balances; zero, negative, boolean, and float amounts are rejected. These are direct in-memory SQLite tests, not mocked collaboration assertions.
- **Unknown:** independent-connection races, lock timeout policy, receipt-insert/commit failures, PostgreSQL behavior, and production connection lifecycle were not run. Concurrent safety is supported by source, not runtime-verified here.
- **Decision / next action:** **Keep.** No architectural change recommended. Add shared contract tests for the untested failure and concurrency boundaries before changing this seam.

The adapter is already a deep capability: its caller does not sequence separate debit, credit, and receipt operations. An existing request is checked before touching balances, and a tuple comparison binds it to sender, receiver, and amount (`sqlite_adapter.py:13–18`). New transfers debit only if `balance >= amount`; zero affected rows produces the deliberate combined “insufficient funds or missing sender” error (`:19–22`). A missing receiver raises after the debit, but the exception leaves the `with self.db` block and rolls the transaction back (`:10,23–24`). Normal completion returns the request ID only after the context manager has successfully exited and committed. There is no separate postings table in this copy: the durable movement consists of the two balance updates plus the `transfers` row.

`BEGIN IMMEDIATE` occurs before the request lookup (`:12`). **Inferred from source:** separate SQLite writers must acquire the write transaction before making their read/write decision, so a contender that successfully proceeds can observe the first committed receipt or remaining balance. There is no application retry loop or translation of SQLite lock errors; do not promise that every concurrent request succeeds. The tests commit account setup first (`tests/test_ledger.py:13–14`), so they also do not establish behavior when a caller provides a connection with an already active transaction. The README assigns lifecycle to deployments; that is an integration constraint to establish, not evidence to replace the adapter.

The five existing tests are meaningful boundary coverage (`tests/test_ledger.py:19–45`). Their limits are specific: the conflict test changes only amount and checks balances, the insufficient-funds test checks balances but not receipt count, identity validation branches are absent, and all operations use one in-memory connection. The independent PostgreSQL implementation is unavailable. A passing SQLite suite cannot certify it.

Useful next tests should exercise the unchanged public facade with real adapters and assert both balances and receipt rows:

| Case | Required observation |
| --- | --- |
| Retry changes sender, receiver, or amount independently | Conflict; original receipt payload and both balances unchanged. |
| Missing sender, insufficient funds, or missing receiver | Defined error; neither partial movement nor receipt; same ID can succeed after correcting the failing condition. |
| Failure inserting the receipt after both updates | A SQLite trigger can force the real failure; both updates roll back, no receipt survives, and a later retry succeeds once. |
| Exact remaining balance; one unit; invalid/matching/empty identities | Correct zero-balance boundary and no mutation for rejected inputs. |
| Two connections: same ID, conflicting ID payload, or different IDs spending the last funds | One durable replay effect, conflicting payload rejected, no overspend; include the specified lock/retry policy in assertions. |
| Shared adapter contract suite | Run success, retry, conflict, and failure cases against both SQLite and the separately owned PostgreSQL adapter in its authorized environment. |

Keep SQL locking and schema details inside each adapter. A new coordinator service or a rewritten persistence layer would add responsibility without resolving an observed defect in this scope. If a contract test later fails, make the smallest change in the owner identified above and preserve `transfer(request_id, sender, receiver, amount) -> receipt`.

The safe local command ran from `/private/tmp/codebase-sense-qa-91vasxy9/jobs/candidate-a/cases/ledger` after inspecting the setup:

```sh
PYTHONDONTWRITEBYTECODE=1 /private/tmp/codebase-sense-qa-91vasxy9/venv/bin/python -m unittest discover -s tests -v
```

Exit **0**, exact output:

```text
test_conflicting_retry (test_ledger.LedgerTests.test_conflicting_retry) ... ok
test_domain_validation (test_ledger.LedgerTests.test_domain_validation) ... ok
test_insufficient_funds (test_ledger.LedgerTests.test_insufficient_funds) ... ok
test_missing_receiver_rolls_back (test_ledger.LedgerTests.test_missing_receiver_rolls_back) ... ok
test_transfer_and_retry (test_ledger.LedgerTests.test_transfer_and_retry) ... ok

----------------------------------------------------------------------
Ran 5 tests in 0.002s

OK
```

No additional runtime probes were used for this case. There was no test-harness blocker; the unrun boundaries above remain unverified.
