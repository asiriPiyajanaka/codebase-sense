# Ledger transfer audit

Scope: `Ledger.transfer` through the SQLite adapter. Mode: read-only audit using Codebase Sense v0.1.0. Source and tests were not modified. No repository-specific AGENTS.md or ADR was found. `git status --short` exited 128 because the copy has no Git metadata; working-tree state and change history are unknown.

**Keep the architecture.** The facade validates domain input while the adapter owns the complete atomic persistence operation. The README explicitly requires this seam because an independently shipped PostgreSQL adapter implements the same contract (`README.md:3–6`). The short forwarding method is not evidence of a useless abstraction.

## Sense Card

- **Promise:** positive integer transfer units; one payload per request ID; matching retry returns the original receipt; conflicting retry is rejected; atomic balance changes, no negative balances, and no receipt on failure (`README.md:3–11`). The SQLite receipt is the request ID string, not a separate receipt object.
- **Flow:** caller → `ledger.py:Ledger.transfer:5` validates identities and amount → `sqlite_adapter.py:SQLiteLedger.transfer:9` starts `BEGIN IMMEDIATE`, checks prior payload, conditionally debits sender, credits receiver, inserts transfer → connection context commits on normal return or rolls back on exception.
- **Owner:** `Ledger` owns public input validation; `SQLiteLedger.transfer` owns SQLite locking, retry lookup, balance checks, and the transaction. The caller does not coordinate postings.
- **Change entry point:** domain input rule changes start at `ledger.py:5`; persistence, insufficient funds, retry, or atomicity issues start at `sqlite_adapter.py:9`.
- **Verified:** success and matching retry leave one receipt and balances 60/40; conflicting amount is rejected; missing receiver rolls back; insufficient funds preserves balances; invalid amount cases reject — all five existing tests passed (`tests/test_ledger.py:19–45`).
- **Verified additionally:** an injected failure on receipt insertion rolled both balance updates back and left no receipt; after removing the fault, retrying the same request for the entire sender balance succeeded once and a further matching retry did not debit again.
- **Inferred from source, not independently verified:** `BEGIN IMMEDIATE` serializes decision-making across independent SQLite writers; the conditional debit and schema check protect nonnegative balances (`sqlite_adapter.py:5,12,19–22`).
- **Unknown:** multi-connection contention, lock timeout/retry behavior, crash durability, external adapter parity, and behavior inside a pre-existing transaction. The README assigns connection lifecycle to production deployments; initialization here is a one-time fixture schema creation, not a reusable migration API.
- **Decision:** **Keep** the facade/adapter division and transaction boundary.
- **Next action:** strengthen the adapter contract tests for fault rollback, payload conflicts, and concurrent connections; no architectural refactor is recommended.

## Ownership and failure semantics

`Ledger.transfer` rejects missing identities, a self-transfer, and amounts whose exact type is not built-in `int` or whose value is nonpositive (`ledger.py:6–9`). It does not coerce booleans or floats. The adapter is intentionally behind this validated facade; calling the adapter directly bypasses those checks.

Within one `with self.db` block (`sqlite_adapter.py:10`), the adapter takes the write reservation before reading prior transfers (`:12–14`). A matching prior payload returns the same request ID without touching balances (`:15–18`). The lookup precedes insufficient-funds checks, so even a previously successful full-balance transfer remains retryable. A changed payload raises `ValueError("request payload conflict")`.

A new transfer debits only a sender with sufficient funds (`:19–22`). Missing sender and insufficient funds intentionally share one `ValueError` message; a missing receiver raises a separate `ValueError` after the debit, and the connection context rolls it back (`:23–24`). Receipt insertion occurs after both updates in the same transaction (`:25`). SQLite failures propagate rather than being converted to domain errors. The transaction context is responsible for rollback, not the facade or caller.

The actual additional probe output was:

```text
receipt failure injected receipt failure
balances [('alice', 100), ('bob', 0)] receipts []
full-balance retry [('alice', 0), ('bob', 100)] receipts [('r1', 'alice', 'bob', 100)]
```

This supports atomic rollback for the injected statement failure and idempotency at the zero-balance boundary. It does not prove process-crash durability or concurrent behavior. There is no authorization policy or external service in this fixture, so none is invented here.

## Architectural assessment

**Candidate: merge the facade and SQLite adapter — Keep the current separation.** The facade is a real public caller of one cohesive adapter method (`ledger.py:10`), while the adapter hides the difficult ordering, locking, and rollback decisions. Its stable contract is already `transfer(request_id, sender, receiver, amount) -> original_receipt`. Merging would entangle validation with SQLite and violate the documented independently shipped adapter seam. The small number of facade lines is not observed coordination leakage.

The remaining uncertainty is behavioral coverage, not a demonstrated architecture defect. A shared contract suite could check SQLite and PostgreSQL without replacing either adapter. Start with additional outcome assertions in that contract; do not introduce a new service layer or generic transaction abstraction absent a concrete caller need.

## Useful behavioral tests

1. Extend payload conflicts to changed sender, receiver, and combinations, and assert the original receipt row and both balances remain unchanged. Existing conflict coverage changes only amount and asserts only balances (`tests/test_ledger.py:25–29`).
2. Preserve the receipt-insertion failure probe as an adapter boundary test: fail after both balance updates, assert all state rolled back, remove the fault, and retry the same request successfully.
3. Test missing sender, missing identity, self-transfer, and every invalid amount; assert no balance or receipt changes. Also assert no receipt after insufficient funds, which the current test does not inspect (`tests/test_ledger.py:37–40`).
4. Test a transfer equal to the whole balance followed by the same retry, and a failed request followed by a successful retry after its prerequisite is repaired. Failed transfers must not reserve request IDs.
5. Race independent connections against the same temporary SQLite database: identical IDs produce one transfer, conflicting payloads select one winner, and two distinct requests competing for limited funds cannot overdraw. Assert total balance conservation and defined lock-error handling. Run the same public behavior matrix against PostgreSQL when that adapter and its authorized environment are available.

The existing tests exercise real SQLite state rather than mocked method calls and already cover the core ownership boundary well. They do not establish concurrency or production adapter equivalence.

## Commands and results

`rg --files`, `cat`, and `nl -ba` inspected README, source, tests, and skill references. No network, installs, services, windows, or external writes were used.

From this case root:

```sh
PYTHONDONTWRITEBYTECODE=1 /private/tmp/codebase-sense-qa-91vasxy9/venv/bin/python -m unittest discover -s tests -v
```

Result: **5 tests passed**, exit 0. A separate heredoc used the same interpreter/environment and an in-memory SQLite database, seeded Alice 100/Bob 0, installed `CREATE TRIGGER fail_receipt BEFORE INSERT ON transfers BEGIN SELECT RAISE(ABORT, 'injected receipt failure'); END`, and asserted rollback after the resulting `sqlite3.IntegrityError`. It then removed the trigger and asserted two full-balance calls produced one transfer. Probe exit 0. No new source or test files were created, and no concurrent or PostgreSQL tests were run.
