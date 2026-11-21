Checkout needs a change to its persistence and retry boundary. The current API returns the documented response, but repeating a successful request grants another reward. A conflicting retry also returns the old order while using the new amount for another reward. Audit scope: `app.checkout` through local SQLite storage and its existing callers/tests. No source or tests were changed.

`README.md:3` promises an order and `cents // 100` points, a stable `{"order_id": int}` response, and repeated delivery of a request ID identifying one customer and amount. `app.py:4` validates input, then calls `record_order` and `award_points` separately. `store.py:11` inserts or ignores an order by request ID and commits it; `store.py:18` always inserts another reward and commits it. The rewards schema at `store.py:7` has no uniqueness constraint on `order_id`. Neither the existing order's customer nor its amount is checked on reuse.

One candidate warrants change: make completion of one checkout an accountable local storage operation behind the existing API. The observed cost is correctness: the caller coordinates independently committed writes, and replay handling protects only the order. The counterargument is that two small table helpers are easy to read; file count and thinness alone would not justify a refactor. Here both effects use the same SQLite connection and belong to the same documented checkout; no remote transaction problem or independent reward lifecycle is evidenced.

A possible internal contract is `store.complete_checkout(db, request_id, customer, cents) -> order_id`: bind a request ID to its payload, reject conflicts, and atomically record one order plus one reward or return the original completed result. Keep `app.checkout`'s public signature, validation and response shape. This is a proposed contract, not an implementation. A new service hierarchy is unnecessary. Before changing storage, decide how existing duplicate rewards or incomplete orders would be reconciled and establish ownership of the supplied connection's transaction; blindly adding a unique index or nesting transactions could break existing data or callers.

Useful behavioral tests, through the real public function and SQLite boundary:

- Deliver an identical request twice; assert the same response, one order and exactly one reward worth `cents // 100`.
- Reuse a key with a changed customer and separately with a changed amount; assert an explicit conflict and unchanged orders/rewards.
- Inject a reward INSERT failure with a SQLite trigger; assert no newly committed order or reward remains, then remove the fault and retry once successfully.
- Exercise independent connections with the same request and with conflicting payloads; assert at most one completed checkout and no duplicate reward. Specify busy/timeout handling rather than assuming every contender succeeds.
- Cover positive amounts below and at 100, invalid identities, bool/non-integer/non-positive amounts, and unchanged response shape. Assert both tables remain untouched for rejected input.

The first three cases expose current problems; the atomic rollback assertion expresses the proposed stronger completion contract. The README does not explicitly specify every failure state's atomicity today.

Existing check, from `/private/tmp/codebase-sense-qa-91vasxy9/jobs/candidate-b/cases/checkout`:

```sh
PYTHONDONTWRITEBYTECODE=1 /private/tmp/codebase-sense-qa-91vasxy9/venv/bin/python -m unittest discover -s tests -v
```

Exit 0:

```text
test_invalid_input_has_no_effects (test_checkout.CheckoutTests.test_invalid_input_has_no_effects) ... ok
test_success (test_checkout.CheckoutTests.test_success) ... ok

Ran 2 tests in 0.002s
OK
```

These verify the single successful example and rejection of zero cents before any order is recorded (`tests/test_checkout.py:9`, `:15`). They do not exercise retries or storage failure. The reward table is not asserted in the invalid-input test.

Supplemental local probe (saved alongside this report; fresh in-memory databases, no source modifications):

```sh
PYTHONDONTWRITEBYTECODE=1 /private/tmp/codebase-sense-qa-91vasxy9/venv/bin/python /private/tmp/codebase-sense-qa-91vasxy9/jobs/candidate-b/reports/checkout_probe.py
```

Exit 0; its assertions confirm observed defects, not successful enforcement of the desired invariants:

```text
exact retry: {"orders": [[1, "r1", "alice", 500]], "responses": [{"order_id": 1}, {"order_id": 1}], "rewards": [[1, 5], [1, 5]]}
conflicting retry: {"orders": [[1, "r1", "alice", 500]], "response": {"order_id": 1}, "retry_payload": ["alice", 900], "rewards": [[1, 5], [1, 9]]}
conflicting retry: {"orders": [[1, "r1", "alice", 500]], "response": {"order_id": 1}, "retry_payload": ["bob", 500], "rewards": [[1, 5], [1, 5]]}
reward failure after rollback: {"error": "reward unavailable", "orders": [[1, "r1", "alice", 500]], "rewards": []}
All observation assertions passed: retries duplicate rewards and reward failure leaves a committed partial checkout.
```

An earlier execution of the same probe produced identical data with the final diagnostic sentence, `All observed-defect assertions passed; retry and atomicity guarantees are violated.` Only that sentence was corrected to distinguish observed partial state from a documented atomicity promise; the probe was rerun as shown above.

**Sense Card — checkout**

- **Scope/mode:** One local checkout; audit. Inspected every file supplied in this case. No repository instruction files or git metadata were present; no history or production callers were available.
- **Promise/flow:** Valid request → `app.checkout` validation → order insert/reuse and commit → reward insert and commit → `{"order_id": id}`.
- **Current owner:** `app.py:4` owns sequencing/validation; `store.py:11` owns order deduplication; `store.py:18` owns reward persistence. No operation owns atomic completion or payload binding today. Proposed owner: one storage completion boundary.
- **Change entry point:** `app.py:7`, then `store.py:11`, where reuse and independent commits produce the observed behavior.
- **Checked:** Single success and zero-input example passed. Exact retries duplicate rewards, changed customer/amount are accepted, and injected reward failure leaves a committed order after rollback, reproduced locally above. These observations refute reward idempotency and establish partial-failure behavior.
- **Unknown:** Multi-connection concurrency, all database error modes, existing persisted-data repair needs, and connection lifecycle outside this fixture. Existing tests have demonstrated gaps for retries and storage failure.
- **Decision:** **Change** — give the existing checkout capability responsibility for one payload-bound completion; retain the public response.
- **Next smallest action:** Add the public-boundary retry/conflict and reward-failure tests before changing storage. Implementation remains outside this audit's authorization.
