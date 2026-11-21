# Ledger transfer workflow audit

The transfer workflow has a coherent existing boundary: `Ledger` validates domain input and `SQLiteLedger` owns atomic persistence and replay decisions. The five existing tests pass, and an additional database failure probe confirmed rollback after both balance updates. No architectural replacement is justified; preserve the adapter seam explicitly required for the independently shipped PostgreSQL adapter (`README.md:3–11`). No source or tests were changed.

## Behavior and ownership

`Ledger.transfer` (`ledger.py:5–10`) rejects falsey identities, equal sender and receiver, and amounts whose exact type is not `int` or which are not positive. Booleans are rejected. It delegates once and returns the adapter's receipt unchanged. Identity validation checks truthiness, not a string type. The facade owns these domain rules, not SQL or connection management.

`SQLiteLedger.__init__` (`sqlite_adapter.py:2–7`) creates the schema on the supplied connection; it does not create or close the connection. Accounts have a nonnegative-balance CHECK constraint. Transfers have a primary-key request ID and record the original payload. This fixture stores account balances and transfer receipts, not a separate append-only postings table.

`SQLiteLedger.transfer` (`sqlite_adapter.py:9–26`) owns the entire transaction:

1. Enter the connection transaction context and issue `BEGIN IMMEDIATE` before reading. SQLite serializes the read/write decision across independent connections; lock acquisition may wait or raise a SQLite error according to connection settings.
2. Read any prior transfer by request ID. An identical tuple returns the original request ID, without rechecking current funds or applying balances again. A different tuple raises `ValueError("request payload conflict")`.
3. Debit the named sender only if its balance is sufficient. A row count other than one rejects a missing or underfunded sender.
4. Credit the receiver, rejecting a missing receiver.
5. Insert the transfer receipt and return the request ID. Leaving the context commits on success and rolls back on an exception, including an exception after the debit or credit.

This owner has a real persistence responsibility. Moving its sequencing or transaction management into the facade would expose SQLite details and duplicate the contract across adapters. The caller/deployment owns account setup and connection lifecycle. The method assumes a connection on which it can start a transaction; an already active transaction will make `BEGIN IMMEDIATE` fail. Document this connection contract rather than silently nesting transactions or taking over deployment lifecycle.

## Failure and retry guarantees

A committed identical retry returns the same string receipt and performs no additional balance update. Conflicting retries fail before mutations. Failed new transfers leave neither a receipt nor a committed debit/credit, and the same ID can be reused for a later successful attempt once the underlying cause is resolved. Successful transfers conserve the total balance and cannot overdraw the sender through this path.

There is no internal retry loop. Domain `ValueError`s and database errors propagate. A caller that loses the success response can repeat the same payload safely because the receipt is committed with the balances. The source's serialization and primary key support independent-connection safety, but the supplied tests and my runtime probes use a single in-memory connection; a concurrent delivery guarantee has not been empirically tested here. Durability still depends on SQLite and connection configuration. No external money movement is shown, so this audit does not infer a distributed transaction guarantee.

The injected receipt-insertion failure occurred after both balance updates, raised `IntegrityError`, and left Alice at 100, Bob at 0, and zero transfers. Retrying `r1` after removing the failure yielded Alice 60, Bob 40, and exactly one matching transfer.

## Test assessment and useful additions

Existing tests (`tests/test_ledger.py:19–45`) cover identical retry, amount-conflict retry, missing-receiver rollback, insufficient funds, and several invalid amount types. These are relevant behavioral tests, including the critical post-debit rollback path. Strengthen them with:

1. Sender and receiver conflicts as well as amount conflicts; assert the original receipt payload, balances, and transfer count remain unchanged.
2. Force transfer-receipt insertion to fail after both updates; assert complete rollback and a successful same-ID retry after removing the fault.
3. Fail for missing receiver or insufficient funds, repair the precondition, and retry the same ID successfully. This verifies a failure does not consume the ID.
4. Missing sender, empty identities, same sender/receiver, and all rejected amount types; assert no receipt and no balance changes.
5. Drain the sender after an initial success, then repeat the old successful request. It must return the original receipt despite insufficient current funds.
6. Temporary-file SQLite with two independent connections: simultaneous identical requests must yield one transfer; conflicting same-ID requests must allow only one payload; competing transfers must never create a negative balance or a partial receipt. Test final observable state and bounded lock outcomes, not private SQL call order.
7. A facade test with a small recording adapter: valid input and the returned receipt pass through once; invalid input never reaches the adapter. Apply a shared behavioral contract to each available adapter without replacing the independently shipped implementation.

The best next work is contract coverage and documentation of transaction/connection assumptions. There is no observed need for a new coordinator, generic repository layer, adapter removal, or facade/adapter merger.

## Commands and observed results

All commands below ran from `/private/tmp/codebase-sense-qa-91vasxy9/jobs/baseline/cases/ledger`; no installs or network operations were used. Inspection used `nl -ba README.md`, `nl -ba ledger.py`, `nl -ba sqlite_adapter.py`, and `nl -ba tests/test_ledger.py`.

```sh
PYTHONDONTWRITEBYTECODE=1 /private/tmp/codebase-sense-qa-91vasxy9/venv/bin/python -m unittest discover -s tests -v
```

Result: exit 0, `Ran 5 tests in 0.001s`, `OK`. Passing tests: `test_conflicting_retry`, `test_domain_validation`, `test_insufficient_funds`, `test_missing_receiver_rolls_back`, `test_transfer_and_retry`.

```sh
PYTHONDONTWRITEBYTECODE=1 /private/tmp/codebase-sense-qa-91vasxy9/venv/bin/python - <<'PY'
import sqlite3
from ledger import Ledger
from sqlite_adapter import SQLiteLedger

db=sqlite3.connect(':memory:')
ledger=Ledger(SQLiteLedger(db))
db.executemany('INSERT INTO accounts VALUES (?, ?)', [('alice',100),('bob',0)])
db.commit()
db.executescript("CREATE TRIGGER fail_receipt BEFORE INSERT ON transfers BEGIN SELECT RAISE(ABORT, 'injected receipt failure'); END;")
try:
    ledger.transfer('r1','alice','bob',40)
except sqlite3.IntegrityError as e:
    print(type(e).__name__, str(e))
print('after_failure', db.execute('SELECT * FROM accounts ORDER BY name').fetchall(), db.execute('SELECT * FROM transfers').fetchall())
db.execute('DROP TRIGGER fail_receipt'); db.commit()
print('retry',ledger.transfer('r1','alice','bob',40))
print('after_retry', db.execute('SELECT * FROM accounts ORDER BY name').fetchall(), db.execute('SELECT * FROM transfers').fetchall())
db.close()
PY
```

Result: exit 0.

```text
IntegrityError injected receipt failure
after_failure [('alice', 100), ('bob', 0)] []
retry r1
after_retry [('alice', 60), ('bob', 40)] [('r1', 'alice', 'bob', 40)]
```
