# Checkout workflow audit

Checkout returns the documented `{"order_id": int}` response on success, but it does not satisfy safe redelivery of a request. Orders are deduplicated; rewards are not. A local transaction and explicit payload checks are justified. A new service framework or distributed workflow is not supported by this repository, whose only state is local SQLite (`README.md:3–7`). No source or tests were changed.

## Behavior and ownership

`app.checkout` (`app.py:4–9`) validates before persistence: request ID and customer must be truthy, and `cents` must have exact type `int` and be positive. This rejects booleans, but does not establish that either identity is a string. It then calls `store.record_order`, calls `store.award_points`, and returns the order ID. It owns sequencing and response shape; storage helpers currently own transaction completion.

`record_order` (`store.py:11–15`) inserts with `INSERT OR IGNORE`, commits, then selects the ID by request ID. The unique order request ID prevents a second order for that ID. It neither checks that the stored customer and amount match nor distinguishes a duplicate request from another ignored insert. `award_points` (`store.py:18–20`) unconditionally inserts `cents // 100` points and commits separately. The rewards schema (`store.py:7`) has no uniqueness constraint on `order_id` and no foreign key.

The supplied connection is caller owned. There is no payment gateway, network retry layer, queue, or other external effect in this workflow. Both helper commits can also commit unrelated pending work on the supplied connection; an outer `with db:` cannot undo an already committed order.

## Failure and retry guarantees

| Situation | Observable outcome |
| --- | --- |
| Valid first call | One order, one reward, response containing its ID. |
| Invalid input | `ValueError("invalid checkout")` before either helper. |
| Same ID and same payload repeated | Same returned ID and one order, but another reward each time. |
| Same ID with changed customer or amount | Original order remains; call is accepted and inserts rewards using the new amount. |
| Reward operation fails after order commit | Exception propagates, committed order remains, reward may be absent. |
| Response lost after success | Retrying duplicates the reward. |

SQLite errors and other exceptions propagate; there is no application rollback or retry policy. A retry after a failure before reward insertion can add the missing reward, but the caller cannot distinguish that case from a lost successful response. There is no all-or-nothing checkout guarantee. Committing before the ID lookup also leaves a possible error window after the order has become durable.

The existing two tests pass. A separate in-memory probe reproduced all three material failures: repeated success produced rewards `[(1, 5), (1, 5)]`; changed payload produced `[(1, 5), (1, 9)]` against the original Alice/500 order; an injected reward failure left the order and no rewards.

## Recommended change

Give one storage operation ownership of the complete checkout transaction. Keep validation and response construction in the public entry point. Inside the transaction, look up the request ID, reject a different stored `(customer, cents)`, and return the existing ID for a completed identical request. Otherwise insert the order and its one reward, committing once. Remove independent commits from any helpers used inside that operation. Ensure a failure rolls back both writes. SQLite `BEGIN IMMEDIATE` is one suitable way to serialize the read/write decision; handle transaction ownership explicitly for caller-supplied connections.

Add `UNIQUE(order_id)` as a storage invariant for rewards and consider an enforced foreign key for referential integrity. Uniqueness alone does not fix acceptance of conflicting payloads or the split commit. Preserve the response shape. Existing partially completed orders need a deliberate repair or compatibility policy if this is applied to populated data. There is no evidence requiring an outbox, payment abstraction, dependency injection framework, or additional architectural layers.

## Useful behavioral tests

1. Repeat a successful request, including after closing and reopening a temporary database: assert the same response, exactly one persisted order and one reward, and unchanged customer and amount.
2. Reuse a request ID with a changed customer, changed amount, and both changed. Expect a payload-conflict error and unchanged rows.
3. Inject failure at reward insertion through a SQLite trigger or storage boundary. Assert no committed order or reward, then remove the failure and retry the same ID successfully exactly once.
4. Exercise two independent connections delivering the same request and a conflicting payload. Assert the final row counts and payload, rather than particular internal call order.
5. Cover validation with empty identities and `0`, negative, boolean, float, and non-integer amounts, checking both tables remain empty.
6. Check reward flooring with amounts `1`, `99`, `100`, and `199`, and check distinct request IDs remain distinct even for the same customer and amount.

The current happy-path test checks the first response and reward points; the validation test covers only a zero amount and only the order count (`tests/test_checkout.py:9–20`). They do not cover the documented redelivery scenario, payload identity, durable state after failure, or transaction ownership.

## Commands and observed results

All commands below ran from `/private/tmp/codebase-sense-qa-91vasxy9/jobs/baseline/cases/checkout`; no installs or network operations were used. Inspection used `nl -ba README.md`, `nl -ba app.py`, `nl -ba store.py`, and `nl -ba tests/test_checkout.py`.

```sh
PYTHONDONTWRITEBYTECODE=1 /private/tmp/codebase-sense-qa-91vasxy9/venv/bin/python -m unittest discover -s tests -v
```

Result: exit 0, `Ran 2 tests in 0.001s`, `OK` (`test_invalid_input_has_no_effects`, `test_success`).

```sh
PYTHONDONTWRITEBYTECODE=1 /private/tmp/codebase-sense-qa-91vasxy9/venv/bin/python - <<'PY'
import sqlite3
from unittest.mock import patch
from app import checkout
from store import initialize
for scenario in ['retry', 'changed_payload', 'reward_failure']:
    db=sqlite3.connect(':memory:'); initialize(db)
    if scenario == 'reward_failure':
        with patch('app.award_points', side_effect=RuntimeError('injected reward failure')):
            try: checkout(db, 'r1', 'alice', 500)
            except RuntimeError as e: print(scenario, type(e).__name__, str(e))
    else:
        print(scenario, 'first', checkout(db, 'r1', 'alice', 500))
        print(scenario, 'second', checkout(db, 'r1', 'bob' if scenario == 'changed_payload' else 'alice', 900 if scenario == 'changed_payload' else 500))
    print('orders', db.execute('SELECT id, request_id, customer, cents FROM orders').fetchall())
    print('rewards', db.execute('SELECT order_id, points FROM rewards').fetchall())
    db.close()
PY
```

Result: exit 0.

```text
retry first {'order_id': 1}
retry second {'order_id': 1}
orders [(1, 'r1', 'alice', 500)]
rewards [(1, 5), (1, 5)]
changed_payload first {'order_id': 1}
changed_payload second {'order_id': 1}
orders [(1, 'r1', 'alice', 500)]
rewards [(1, 5), (1, 9)]
reward_failure RuntimeError injected reward failure
orders [(1, 'r1', 'alice', 500)]
rewards []
```
