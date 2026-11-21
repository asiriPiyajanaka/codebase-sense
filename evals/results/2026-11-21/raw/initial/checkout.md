# Checkout audit

Scope: checkout only. Mode: read-only audit using Codebase Sense v0.1.0. Source and tests were not modified. No repository-specific AGENTS.md or ADR was found. This copy has no Git metadata, so dirty-file state and history could not be established (`git status --short` exited 128).

**Change is justified:** checkout exposes an order-and-reward promise but splits it across independently committed operations. Its current tests pass while retries duplicate rewards and failures leave partial state.

## Sense Card

- **Promise:** `README.md:3–7` describes `app.checkout(connection, request_id, customer, cents)` returning `{"order_id": int}`, recording an order and `cents // 100` points, with repeated delivery allowed and one payload per request ID.
- **Flow:** `app.py:checkout:4` validates nonempty IDs and a strictly positive built-in integer amount → `store.py:record_order:11` inserts or ignores an order, commits, and selects its ID → `store.py:award_points:18` inserts a reward and commits → response. All effects are local SQLite; there is no payment gateway.
- **Owner:** `checkout` owns sequencing, but the store helpers own separate commits. No component currently owns the invariant that one checkout creates one matching order and reward together.
- **Change entry point:** start at `app.py:checkout:4` and the commits in `store.py:14,20`; these determine retry and failure behavior.
- **Verified:** happy-path response and 500-cent reward; zero-amount rejection without an order — the two existing tests passed (`tests/test_checkout.py:9,15`). Other invalid input branches are visible in source but not comprehensively tested.
- **Missing, reproduced:** same-payload retry returns the original ID but inserts another reward. Changed-payload reuse is accepted and awards points from the new amount against the original order. Reward insertion failure leaves a committed order, even after caller rollback.
- **Unknown:** concurrent independent connections, lock errors, durability settings, caller-owned transaction expectations, and other external callers. No concurrency or disk-failure test was run. Authentication is not part of this fixture's contract.
- **Decision:** **Change**, bounded to checkout consistency and retry policy.
- **Next action:** add behavioral regressions for the three reproduced failures before changing the transaction boundary.

## Observed behavior and failures

`orders.request_id` is unique (`store.py:4`), but `rewards.order_id` has neither uniqueness nor a foreign key (`store.py:7`). `INSERT OR IGNORE` does not compare the existing customer or amount (`store.py:12–15`). The real caller always invokes `award_points`, including when the order already exists (`app.py:7–8`). This makes retry behavior a correctness problem, not merely a thin-wrapper concern.

An in-memory probe produced:

```text
first {'order_id': 1}
retry {'order_id': 1}
orders [(1, 'r1', 'alice', 500)]
rewards [(1, 5), (1, 5)]
conflict {'order_id': 1}
rewards [(1, 5), (1, 5), (1, 9)]
```

The conflict call reused `r1` with customer `bob` and amount `900`. A separate database used a SQLite trigger that raises `ABORT` before a reward insert. `checkout` raised `sqlite3.IntegrityError("injected reward failure")`; the order remained and rewards were empty. Calling `db.rollback()` still left that order because `record_order` already committed it. There is no automatic rollback or exception conversion in `checkout`.

## One architectural candidate

**Candidate: one persistence operation for an idempotent checkout.** Keep the public response and input validation. A possible storage contract is `complete_checkout(db, request_id, customer, cents) -> order_id`: compare a previously stored payload, return its existing result on a matching retry, reject a conflicting payload, and atomically create a new order plus reward. Transaction sequencing and duplicate detection become internal to that capability; the application translates the returned ID to the existing response shape.

The counterargument is that separate order and reward helpers can be useful independent operations. However, this repository exposes only the checkout caller, and both operations are local SQLite. There is no independent reward-service lifecycle to justify partial commits. Preserve unrelated responsibilities and investigate any external helper clients before removing exports. A transaction alone does not stop duplicate rewards; a unique reward-per-order rule and explicit retry lookup must agree.

Compatibility risks include changing helper commit behavior, nesting within an existing transaction, choosing a conflict exception, and adding uniqueness when old duplicate rewards already exist. The smallest reversible slice is to establish regressions, add the cohesive operation alongside existing helpers, route `checkout` through it, and retain compatibility until callers and existing data are checked. No schema migration or implementation was performed here.

## Useful behavioral tests

1. Deliver an identical request twice; assert identical response, exactly one order, exactly one reward, and the original points.
2. Reuse a request ID with a changed customer, changed amount, and both; assert explicit rejection and unchanged rows. Include the 99/100/101-cent boundary and reject `True`, floats, zero, negatives, and missing IDs without any rows in either table.
3. Inject a failure before reward insertion after order creation; assert the exception and no durable order or reward, then remove the fault and retry the same ID successfully once.
4. Inject failure at commit and document what the connection state permits callers to retry; preserve the successful response shape. This needs a reliable fault-injection boundary rather than mocks asserting helper call order.
5. With independent connections to a temporary SQLite database, race identical requests and conflicting payloads; assert one consistent result, no duplicate reward, and defined handling of lock failures.

The existing tests use real SQLite and check outcomes, which is useful, but cover only success and one validation case. They do not establish atomicity, idempotency, payload identity, or concurrency.

## Commands and results

All execution was local. The initial prompt reader used system `python3` only to read the four task strings; repository tests and probes used the supplied interpreter. `rg --files`, `cat`, and `nl -ba` inspected the README, source, tests, and skill references. No network, installs, services, or windows were used.

From this case root:

```sh
PYTHONDONTWRITEBYTECODE=1 /private/tmp/codebase-sense-qa-91vasxy9/venv/bin/python -m unittest discover -s tests -v
```

Result: **2 tests passed**, exit 0. A separate heredoc with the same environment/interpreter imported `checkout` and `initialize`, used two `sqlite3.connect(':memory:')` databases, called identical and conflicting retries, and installed `CREATE TRIGGER fail_reward BEFORE INSERT ON rewards BEGIN SELECT RAISE(ABORT, 'injected reward failure'); END`. The observations above are its actual output; exit 0 indicates the probe completed, not that checkout satisfied the intended guarantees. No new regression tests were written or claimed passing.
