# Ledger transfer workflow audit

Recommendation: preserve the existing Ledger/adapter seam and transfer ownership. The public facade is small, but the persistence implementation already has depth: it owns atomic posting, replay checks, and the receipt. No architectural change is justified by this copy.

## Scope and evidence

Audited README.md, ledger.py, sqlite_adapter.py, and all five tests in tests/test_ledger.py. The user named transfers, so no history inference was needed. No GLOSSARY.md or docs/adr decisions were present; the README supplies the contract and an explicit decision.

- README.md:3–11 requires positive integer transfers, immutable request payloads, replay of the original receipt, atomic postings, nonnegative balances, no failed-transfer receipt, and caller-owned connection lifecycle.
- README.md:5–6 explicitly requires the adapter seam because an independently shipped PostgreSQL adapter uses the same contract. That adapter is not present here and was not inspected or validated.
- ledger.py:5–10 owns domain validation and delegates persistence.
- sqlite_adapter.py:9–26 owns the entire transfer transaction, beginning with BEGIN IMMEDIATE and ending when the connection context exits.
- tests/test_ledger.py:19–45 covers success plus replay, changed amount, missing receiver rollback, insufficient funds, and invalid amounts.

Source and tests were not edited.

## Observable behavior and ownership

1. Ledger.transfer rejects empty identities, identical sender/receiver, and amounts whose exact type is not int or which are nonpositive. bool and float are rejected. Identity string typing is not enforced beyond these conditions.
2. SQLiteLedger enters the connection transaction context and executes BEGIN IMMEDIATE before reading the request receipt.
3. For a matching prior request, it returns request_id without touching balances. It compares sender, receiver, and amount, not only amount; a changed payload raises ValueError.
4. For a new request, one conditional sender update debits only if the account exists and has enough balance.
5. It credits an existing receiver or raises ValueError. It inserts the transfer receipt only after both balance updates.
6. Exiting the connection context commits before the caller receives request_id. Exceptions during the transaction trigger rollback via the connection context.

Ledger owns validation. SQLiteLedger owns persistence, serialization, conditional debit, conflict detection, and commit/rollback. The caller supplies and closes the connection; initialization creates the fixture tables unconditionally. Connection lifecycle, reopening an existing schema, and PostgreSQL behavior are outside the validated fixture behavior.

## Failure and retry guarantees

| Situation | Source-supported guarantee |
| --- | --- |
| Valid new transfer | Both balance updates and one receipt commit together |
| Exact replay | Original request_id; balances and receipt count unchanged |
| Changed sender, receiver, or amount for prior ID | ValueError; no new effects |
| Insufficient funds or missing sender | ValueError; no receiver credit or receipt |
| Missing receiver after debit | ValueError; sender debit rolls back |
| Failure writing receipt | The same transaction rolls back both updates |
| Database lock or commit failure | SQLite error propagates; no automatic application retry |

The replay decision runs before checking current funds or receiver existence, so a matching recorded request does not repeat the posting even if account state later changes. Failed requests record no receipt; they may be retried after the underlying cause is corrected.

BEGIN IMMEDIATE serializes the read/write decision across connections to the same SQLite database. The conditional debit and CHECK(balance >= 0) protect nonnegative balances. These are source-supported mechanisms; the existing tests use one in-memory connection and do not demonstrate contention behavior.

There is no automatic backoff or retry loop. A caller uncertain about commit outcome should reuse the same request ID and payload rather than inventing another ID. The supplied connection must be available for this module's transaction: an already active transaction causes BEGIN IMMEDIATE to fail, and the connection context can roll back pending caller work. Caller transaction composition is not promised.

## Assessment card: preserve the real adapter seam

Strength: Strong retention recommendation; no structural refactor candidate. Dependency category: local-substitutable for the SQLite implementation; the adapter contract also supports an independently shipped implementation.

Files: ledger.py:1–10; sqlite_adapter.py:1–26; README.md:3–11.

Problem under review: Ledger.transfer looks shallow when viewed only as a forwarding method, but its interface owns domain validation and its seam is an explicit compatibility requirement.

Solution: retain the module split and test the transfer interface against each available adapter, without replacing the adapter or moving SQLite details into the facade.

Before:

    caller
      -> Ledger [domain validation]
           -- adapter seam --
           -> SQLiteLedger
                replay decision
                atomic debit + credit + receipt

After:

    same Ledger interface and adapter seam
      -> SQLiteLedger [same transaction ownership]
      -> expanded behavioral contract coverage
    independently shipped PostgreSQL adapter remains supported

Deletion test: deleting Ledger removes shared validation or makes callers/adapters repeat it; deleting the SQLite adapter moves persistence and lock details into the facade. Neither deletion makes transfer complexity disappear. Combining them would violate the stated decision and reduce locality for persistence changes.

- Module depth already exists behind Ledger.
- Interface hides the transfer transaction decision.
- Seam has two declared adapter implementations.
- Leverage comes from one transfer contract.
- Locality keeps persistence in its adapter.

The PostgreSQL adapter is README evidence of real variation, not a fabricated hypothetical seam. Its mere absence from this fixture does not authorize removing the seam. No ADR is contradicted; the README decision is preserved. Creating another port, a transaction coordinator, or extracted debit/credit modules would add knowledge to the interface without demonstrated benefit.

## Existing tests and useful behavioral tests

All five tests pass. They assert observable receipts and stored balances through Ledger with the real SQLite implementation, giving useful leverage. Missing receiver is particularly valuable because it verifies rollback after the debit.

The interface is the test surface. Extend behavior coverage without testing SQL statements or collaborator call order:

1. Payload conflict matrix: change sender and receiver as well as amount, and assert both balances and receipt contents/count remain unchanged.
2. Late persistence failure: a local SQLite trigger rejects the transfers insertion after both updates; expect original balances and no receipt. Remove it, retry the same ID, and expect one posting.
3. Failure then corrected retry: create/fund the missing account or replenish funds after a failed transfer; the same request ID should now succeed once.
4. Exhaustion: transfer the exact sender balance, then attempt a distinct one-unit transfer; expect zero remaining balance and no second receipt.
5. Identity validation: empty ID/sender/receiver and equal accounts must leave all balances and receipts unchanged.
6. Replay after account changes: spend more funds using a distinct request, then repeat the original request; expect its original receipt and no new movement.
7. Local concurrency contract: separate connections to one temporary SQLite file, competing transfer IDs, and duplicate IDs. Assert nonnegative final balances, conserved total, one receipt per successful ID, and bounded/reported lock failure. Existing tests have not verified this.
8. Run the same behavioral contract against the independently shipped PostgreSQL adapter in its own authorized environment; no such adapter was available here.

## Top recommendation

Keep the architecture and strengthen late-failure and multi-connection evidence. The complete transfer decision already sits in the adapter implementation; more indirection has no demonstrated leverage.

## Skill and harness adaptation

Applied improve-codebase-architecture with codebase-design, HTML-REPORT.md, and DEEPENING.md. The named workflow provided scope. The harness overrides sub-agent exploration, opening HTML/windows, temporary filename conventions, and interactive grilling: this report was produced by one agent as ledger.md and ledger.html in the authorized reports directory and stops after reporting. CDN references in the HTML were not fetched. No interface design, source/test edit, adapter replacement, network, installation, live process, git mutation, or external write occurred.

## Validation

Working directory: /private/tmp/codebase-sense-qa-91vasxy9/jobs/reference/cases/ledger

Exact command:

~~~sh
env PYTHONDONTWRITEBYTECODE=1 /private/tmp/codebase-sense-qa-91vasxy9/venv/bin/python -m unittest discover -s tests -v
~~~

Exit code: 0.

~~~text
test_conflicting_retry (test_ledger.LedgerTests.test_conflicting_retry) ... ok
test_domain_validation (test_ledger.LedgerTests.test_domain_validation) ... ok
test_insufficient_funds (test_ledger.LedgerTests.test_insufficient_funds) ... ok
test_missing_receiver_rolls_back (test_ledger.LedgerTests.test_missing_receiver_rolls_back) ... ok
test_transfer_and_retry (test_ledger.LedgerTests.test_transfer_and_retry) ... ok

----------------------------------------------------------------------
Ran 5 tests in 0.001s

OK
~~~

This run contained five tests, not a concurrency or PostgreSQL validation.

