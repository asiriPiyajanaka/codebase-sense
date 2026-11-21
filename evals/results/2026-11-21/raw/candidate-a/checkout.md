Scope: the local `app.checkout` workflow, including its SQLite effects and repeated requests. Mode: **audit**. Source and tests were left unchanged. I inspected all four repository files; no `AGENTS.md`, ADR, or git metadata was present in this copy.

**Change: give one persistence operation responsibility for the order, reward, and retry decision.** Two passing tests cover a first success and one invalid amount, but the actual implementation duplicates rewards on exact retries, accepts conflicting payloads, and leaves a committed order when awarding its reward fails.

**Sense Card — checkout**

- **Promise:** `README.md:3` specifies an order plus `cents // 100` points, returning `{"order_id": int}`. Lines 5–7 establish repeated delivery and one customer/amount per request ID; all effects are local SQLite.
- **Flow:** `app.py:checkout:4` validates input, calls `store.py:record_order:11`, calls `store.py:award_points:18`, and returns the order ID. `record_order` inserts or ignores a request ID, commits, then looks up its ID. `award_points` unconditionally inserts and commits a reward.
- **Current owners:** `app.checkout` coordinates the workflow and validates; `store.record_order` owns order insertion/deduplication; `store.award_points` owns reward insertion. No operation owns the combined invariant. `orders.request_id` is unique, but `rewards.order_id` has no uniqueness constraint (`store.py:3–7`).
- **Change entry point:** start at `app.py:7–8` for the coordination problem and `store.py:11–20` for transaction and retry policy.
- **Checked:** success returns the documented shape and five points for 500 cents; zero amount is rejected before order insertion. Separate probes verified duplicate rewards on an exact retry, conflicting customer/amount acceptance, and a durable order after reward failure followed by caller rollback. See the commands below.
- **Unknown:** concurrent connections, process interruption, schema migration of existing duplicates, and transaction ownership when callers supply a connection with pending unrelated work were not exercised.
- **Decision / next action:** **Change.** First turn the retry/conflict/rollback probes below into behavioral regression tests; then implement one atomic checkout operation behind the existing response shape when implementation is authorized.

The observed retry behavior is consequential even when both calls return the same order ID. Calling `checkout(db, "r1", "alice", 500)` twice creates one order and two five-point rewards. Reusing `r1` with 900 cents returns the old 500-cent order and inserts nine more points. Changing the customer to Bob likewise returns Alice's order and adds another reward. The lookup at `store.py:15` never compares the stored payload with the new one. This violates the documented identity of a request; request-ID uniqueness alone does not establish idempotency.

Failure is also visible across the caller boundary. A SQLite trigger that rejects reward insertion raises `IntegrityError("reward unavailable")`. Even after `db.rollback()`, the order remains, because `record_order` already committed it at `store.py:14`. An exact retry after removing that fault can supply the missing reward; a later duplicate successful retry adds another one. Neither helper catches storage errors, so they propagate to the caller. Validation rejects falsey request/customer values and requires a strictly positive built-in `int`, including rejecting booleans (`app.py:5`); the existing invalid-input test only exercises zero.

The smallest useful proposed contract is an internal `store.checkout(db, request_id, customer, cents) -> order_id`: a first request commits the order and its single reward together; an exact replay returns the stored ID without another effect; a conflicting replay raises `ValueError` without effects; a failure rolls back the new operation. `app.checkout` can retain validation and the response dictionary. Internalize transaction sequencing and payload comparison in that operation, backed by the existing unique request key and a unique reward-per-order constraint. A SQLite transaction can cover both effects because this repository explicitly has no remote payment gateway.

The counterargument is that these are only two short helpers and one caller; a new service hierarchy would add concepts without benefit. Keep the application/persistence distinction and use one cohesive operation, with private helpers if useful. Before changing schema, decide how to handle already duplicated rewards and incomplete orders; blindly adding uniqueness or wrapping the existing committing helpers in `with db` would not repair the invariant. Preserve successful response shape and make transaction ownership explicit so the operation does not commit unrelated caller work.

Useful behavioral tests should call the real `app.checkout` against SQLite and inspect durable state:

| Case | Required observation |
| --- | --- |
| Exact replay, including simulated lost response | Same dictionary/order ID; one order and one reward after any number of deliveries. |
| Same ID, changed customer or changed amount | Defined conflict exception; original payload and reward unchanged. |
| Reward insertion failure | Exception reaches caller; neither new order nor reward survives rollback; retry can then succeed once. |
| Amount boundaries 1, 99, 100, 101 | Correct integer rounding, including one zero-point reward if the documented reward model is retained. |
| Invalid identity, zero/negative/bool/non-integer amount | No rows in either table, extending the current zero-only check. |
| Two independent connections, same or conflicting ID | At most one committed checkout; duplicates share an ID and conflicts never award more points. Define handling of SQLite lock errors rather than assuming automatic retries. |

Existing checks ran from `/private/tmp/codebase-sense-qa-91vasxy9/jobs/candidate-a/cases/checkout` after inspecting their in-memory setup:

```sh
PYTHONDONTWRITEBYTECODE=1 /private/tmp/codebase-sense-qa-91vasxy9/venv/bin/python -m unittest discover -s tests -v
```

Exit **0**, exact output:

```text
test_invalid_input_has_no_effects (test_checkout.CheckoutTests.test_invalid_input_has_no_effects) ... ok
test_success (test_checkout.CheckoutTests.test_success) ... ok

----------------------------------------------------------------------
Ran 2 tests in 0.002s

OK
```

The saved [checkout-probe.py](checkout-probe.py) uses only disposable in-memory SQLite databases and a real SQLite failure trigger. It characterizes the defects; exit zero means those observations reproduced, not that the desired guarantees passed.

```sh
PYTHONDONTWRITEBYTECODE=1 /private/tmp/codebase-sense-qa-91vasxy9/venv/bin/python /private/tmp/codebase-sense-qa-91vasxy9/jobs/candidate-a/reports/checkout-probe.py
```

Exit **0**, exact output:

```text
exact_retry {"orders": [[1, "r1", "alice", 500]], "responses": [{"order_id": 1}, {"order_id": 1}], "rewards": [[1, 5], [1, 5]]}
conflicting_retry {"orders": [[1, "r1", "alice", 500]], "response": {"order_id": 1}, "retry": ["alice", 900], "rewards": [[1, 5], [1, 9]]}
conflicting_retry {"orders": [[1, "r1", "alice", 500]], "response": {"order_id": 1}, "retry": ["bob", 500], "rewards": [[1, 5], [1, 5]]}
reward_failure_after_rollback {"error": "reward unavailable", "orders": [[1, "r1", "alice", 500]], "rewards": []}
retry_after_failure {"orders": [[1, "r1", "alice", 500]], "response": {"order_id": 1}, "rewards": [[1, 5]]}
```
