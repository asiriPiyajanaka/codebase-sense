Keep the ledger's facade/adapter separation. The inspected SQLite workflow has a clear owner for transactional transfers and passes its five existing behavioral tests. `README.md:4` explicitly requires this seam because an independently shipped PostgreSQL adapter implements the same contract. The facade being short is not evidence that merging it with SQLite would help. Audit scope: `Ledger.transfer`, the supplied SQLite adapter, and its direct test callers. No source or tests were changed.

`ledger.py:5` rejects absent identities, self-transfer, and non-positive/non-integer amounts, including bool. It delegates the validated request to `SQLiteLedger.transfer`. That operation owns persistence: `sqlite_adapter.py:10` opens a connection transaction context, takes `BEGIN IMMEDIATE` before reading (`:12`), compares a reused key's complete payload (`:13`), debits only if sufficient balance exists (`:19`), credits an existing receiver (`:23`), and records the receipt (`:25`). Returning through the context commits; exceptions roll back the changes. The balance CHECK at `:5` is an additional storage guard. The supplied schema represents postings as balance updates, with a transfers receipt table; no separate posting journal is present.

The success result is the request ID. An exact retry returns the original ID without moving units again; changing sender, receiver or amount is rejected by tuple comparison. A missing sender/insufficient balance raises `ValueError`; a missing receiver raises after the debit, relying on transaction rollback. These ownership and failure boundaries are understandable without a new orchestration service. The supplied public caller is the test fixture at `tests/test_ledger.py:12`; production connection lifecycle and the other adapter are outside this checkout.

Candidate considered: collapse the facade into its adapter because it forwards transfers. **Keep.** The facade already owns domain input rules while the adapter owns storage-specific concurrency, balance changes and receipt persistence. Its public contract, `Ledger.transfer(request_id, sender, receiver, amount) -> request_id`, hides SQLite decisions from callers. Collapsing it would couple callers and independently released adapters to a storage implementation without an evidenced benefit. No migration is justified. The smallest useful improvement is coverage of remaining contract boundaries.

Useful additional behavioral tests:

- Table-drive changed sender and receiver as well as amount under the same request ID; assert the original receipt and balances remain intact.
- Assert receipt count remains zero after insufficient funds, missing sender and invalid input; existing insufficient-funds coverage asserts only balances.
- Exercise empty identities and self-transfer, asserting unchanged balances and no receipt. Amount validation is already covered.
- Use independent connections to a disposable local SQLite database for simultaneous same-key requests and two competing debits. Assert at most one receipt for a key, conserved total balance and no negative balance; define acceptable lock/busy results. Single-connection tests do not establish this behavior.
- Add the same adapter contract suite for PostgreSQL when that adapter and a safe provisioned environment are available; no external adapter execution occurred here.

Existing check, from `/private/tmp/codebase-sense-qa-91vasxy9/jobs/candidate-b/cases/ledger`:

```sh
PYTHONDONTWRITEBYTECODE=1 /private/tmp/codebase-sense-qa-91vasxy9/venv/bin/python -m unittest discover -s tests -v
```

Exit 0:

```text
test_conflicting_retry (test_ledger.LedgerTests.test_conflicting_retry) ... ok
test_domain_validation (test_ledger.LedgerTests.test_domain_validation) ... ok
test_insufficient_funds (test_ledger.LedgerTests.test_insufficient_funds) ... ok
test_missing_receiver_rolls_back (test_ledger.LedgerTests.test_missing_receiver_rolls_back) ... ok
test_transfer_and_retry (test_ledger.LedgerTests.test_transfer_and_retry) ... ok

Ran 5 tests in 0.002s
OK
```

**Sense Card — ledger transfer**

- **Scope/mode:** Public facade → SQLite adapter → balances/receipt; audit. All supplied files inspected; no repository instruction files or git metadata were present.
- **Promise:** Move positive integer units once per payload-bound request, return its receipt, reject conflicting reuse and leave no partial failed transfer (`README.md:3`).
- **Flow/owner:** `Ledger.transfer` validates domain input; `SQLiteLedger.transfer` owns lock → replay decision → debit → credit → receipt within one local transaction. The adapter seam is intentional.
- **Change entry point:** `ledger.py:5` for input rules; `sqlite_adapter.py:9` for retry, balance or persistence bugs.
- **Verified in this run:** A 40-unit transfer and exact retry leave balances 60/40 and one receipt (`tests/test_ledger.py:19`); amount conflict leaves balances unchanged (`:25`); missing receiver rolls back the debit and leaves zero receipts (`:31`); insufficient funds leaves balances unchanged (`:37`); zero/negative/bool/float amounts are rejected (`:42`).
- **Unknown/missing coverage:** No concurrent independent-connection test exists in the inspected suite; concurrency correctness remains unverified despite the visible locking mechanism. Sender/receiver conflict variants and invalid identities were not executed. PostgreSQL parity, process crashes and production connection lifecycle were not checked.
- **Decision:** **Keep** — current ownership, caller contract, documented constraints and tested examples support the design; no architectural change recommended within this scope.
- **Next smallest action:** Extend behavioral coverage with independent-connection contention and the untested identity/conflict boundaries while preserving the adapter seam.
