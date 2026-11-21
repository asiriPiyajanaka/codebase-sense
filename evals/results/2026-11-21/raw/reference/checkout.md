# Checkout workflow audit

Recommendation: deepen the checkout persistence module. The current successful response is stable across a retry, but the rewards are not. Local SQLite can own the Order, reward, request payload, and transaction decision together without introducing a new adapter seam.

## Scope and evidence

Audited app.py, store.py, README.md, and tests/test_checkout.py. The user named checkout, so the skill's change-history inference was unnecessary. No GLOSSARY.md or docs/adr decisions were present in this copy; README.md supplies the domain terms.

- README.md:3–7 promises an Order plus cents // 100 reward points, the response {"order_id": int}, and repeated delivery after response loss. A request ID identifies one customer and amount.
- app.py:4–9 owns input validation and sequencing, then delegates two separate persistence decisions.
- store.py:11–15 inserts or ignores the Order, commits, and selects by request ID alone.
- store.py:18–20 always inserts a reward and commits.
- store.py:3–7 makes only orders.request_id unique. rewards.order_id is neither unique nor a declared foreign key.

All references concern this local copy. Source and tests were not edited.

## Observable behavior and ownership

1. checkout rejects an empty request ID or customer, and rejects cents unless its exact type is int and it is positive. bool is rejected. Truthy identity values otherwise pass this validation; the code does not promise string normalization.
2. record_order uses INSERT OR IGNORE. A new request creates an Order, then commits. An existing request returns that Order ID without checking the original customer or amount.
3. award_points appends cents // 100 for the caller's current amount and commits independently.
4. Only after both calls finish does checkout return {"order_id": order_id}. No payment gateway, remote dependency, or background worker exists.

The caller supplies the SQLite connection. checkout owns the public domain entry point, while store currently owns commits in two functions. These functions commit caller connection work too; an outer connection context does not restore atomicity after record_order has committed.

## Failure and retry guarantees

| Situation | Current observable result |
| --- | --- |
| Valid new request | One Order and one reward, then its ID |
| Same request and payload again | Same ID, another reward |
| Same request, changed customer or amount | No conflict error; original Order survives, reward uses new cents |
| Failure inserting reward | Order is already durable; exception escapes; no all-or-nothing guarantee |
| Invalid input | ValueError before either persistence call |
| Response lost after successful persistence | Redelivery repeats the reward insertion |

There is no automatic retry. INSERT OR IGNORE protects Order duplication only. A return value therefore establishes success for that invocation, not exactly one reward across deliveries. The local failure probe uses a SQLite trigger to abort the reward insertion; it leaves one committed Order and zero rewards. The duplicate and conflict probes use real in-memory SQLite, not patched persistence functions.

SQLite write failures propagate. The reward helper supplies no explicit rollback path after its own error; pending transaction state then depends on the SQLite operation and caller cleanup. There is no evidence here of connection sharing, lock retry policy, or concurrent request coordination beyond the uniqueness constraint.

## Candidate: deepen checkout persistence

Strength: Strong. Dependency category: local-substitutable.

Files: app.py:4–9; store.py:3–20.

Problem: the checkout interface requires callers to understand partial Order durability and duplicate reward behavior, although the domain describes one checkout.

Solution: put the request-payload decision, Order and reward persistence, and commit or rollback ownership inside one deep module, while preserving checkout's existing response shape. Validate replay payloads before effects, return the original Order on an exact replay, and reject payload changes without effects. Treat one reward per Order as an invariant protected by persistence. This is a behavioral direction, not a proposed new interface.

Before:

    checkout
      -> record_order -> commit Order
      -> award_points -> commit another reward
      -> return Order ID
    retry: same Order -> another reward

After:

    checkout
      -> deep checkout persistence module
           replay/payload decision
           Order + one reward
           one commit or rollback
      -> original response shape

Deletion test: removing the two persistence functions alone would merely move SQL and commit calls into checkout; it would not repair the invariant. They contain real persistence work, so the issue is split ownership, not their size. Deepening pays off only when it concentrates the complete checkout decision and failure handling.

- Locality: one transaction decision owns the invariant.
- Leverage: every caller gains safe redelivery.
- Depth: one interface exercises all outcomes.
- Seam: keep SQLite behind that interface.
- Adapter: no extra adapter is justified.

Only SQLite is present and the README explicitly excludes a payment gateway. A new storage port or payment adapter would be speculative. In-memory SQLite is a suitable local implementation for behavioral tests at the current seam.

## Existing tests and useful behavioral tests

The two existing tests cover the first success and cents=0, but not delivery semantics or a failure between writes. The interface is the test surface: invoke checkout and inspect durable Orders/rewards through SQLite. Avoid assertions on helper call order.

Prioritize these tests:

1. Exact replay: call twice with r1/alice/500; both results are the same mapping, with one Order and exactly one five-point reward. This currently fails.
2. Payload conflict: reuse r1 with a changed customer, then a changed amount; expect a clear rejection and unchanged Order and reward data. This currently fails.
3. All-or-nothing failure: a real SQLite trigger rejects reward insertion; expect no Order and no reward after caller cleanup/reconnection. Remove the trigger and retry; expect exactly one complete checkout. The rollback expectation currently fails.
4. Lost response: complete a checkout, discard the response, redeliver, and verify the same ID and no additional effects.
5. Input/no effects: exercise bool, float, zero, negative, and empty identities; assert both tables unchanged, not only orders.
6. Reward rounding: positive amounts 1, 99, 100, and 199 create exactly 0, 0, 1, and 1 points. A zero-point reward remains a recorded reward.
7. If concurrent deliveries are in scope, use separate connections to one temporary SQLite file and verify same-request redelivery and conflicting payloads. This has not been validated by the in-memory probe.

## Top recommendation

Repair checkout persistence ownership and replay semantics first. This has demonstrated correctness impact, and the local dependency supports meaningful tests without adding a new external seam.

## Skill and harness adaptation

Applied improve-codebase-architecture and its codebase-design dependency, including HTML-REPORT.md and DEEPENING.md. The harness overrides the skill's fresh sub-agent, browser opening, temporary report naming, and follow-up grilling requirements: this audit used one agent, wrote checkout.html and checkout.md under the authorized reports directory, did not open them or fetch CDN content, and stops after reporting. No new interface was designed; no glossary, ADR, source, or test was changed. No network, installation, live process, git mutation, or external write was needed.

## Validation

Working directory: /private/tmp/codebase-sense-qa-91vasxy9/jobs/reference/cases/checkout

Exact command:

~~~sh
env PYTHONDONTWRITEBYTECODE=1 /private/tmp/codebase-sense-qa-91vasxy9/venv/bin/python -m unittest discover -s tests -v
~~~

Exit code: 0.

~~~text
test_invalid_input_has_no_effects (test_checkout.CheckoutTests.test_invalid_input_has_no_effects) ... ok
test_success (test_checkout.CheckoutTests.test_success) ... ok

----------------------------------------------------------------------
Ran 2 tests in 0.000s

OK
~~~

Passing existing tests does not establish the missing retry/atomicity guarantees.

## Reproduction commands and exact results

Exact command (same working directory as above):

~~~sh
env PYTHONDONTWRITEBYTECODE=1 /private/tmp/codebase-sense-qa-91vasxy9/venv/bin/python - <<'PY'
import sqlite3
from app import checkout
from store import initialize

def fresh():
    db = sqlite3.connect(':memory:')
    initialize(db)
    return db

def state(db):
    return {'orders': db.execute('SELECT request_id, customer, cents FROM orders').fetchall(), 'rewards': db.execute('SELECT order_id, points FROM rewards').fetchall()}

db = fresh()
print('retry responses:', checkout(db, 'r1', 'alice', 500), checkout(db, 'r1', 'alice', 500))
print('retry state:', state(db))
db.close()
db = fresh()
checkout(db, 'r1', 'alice', 500)
print('conflict response:', checkout(db, 'r1', 'bob', 900))
print('conflict state:', state(db))
db.close()
db = fresh()
db.execute("CREATE TRIGGER reward_failure BEFORE INSERT ON rewards BEGIN SELECT RAISE(ABORT, 'reward failed'); END")
try:
    checkout(db, 'r1', 'alice', 500)
except sqlite3.IntegrityError as e:
    print('failure:', type(e).__name__, str(e))
print('failure state:', state(db))
db.close()
PY
~~~

Exit code: 0.

~~~text
retry responses: {'order_id': 1} {'order_id': 1}
retry state: {'orders': [('r1', 'alice', 500)], 'rewards': [(1, 5), (1, 5)]}
conflict response: {'order_id': 1}
conflict state: {'orders': [('r1', 'alice', 500)], 'rewards': [(1, 5), (1, 9)]}
failure: IntegrityError reward failed
failure state: {'orders': [('r1', 'alice', 500)], 'rewards': []}
~~~


