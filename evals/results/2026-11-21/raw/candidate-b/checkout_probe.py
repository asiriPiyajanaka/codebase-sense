"""Read-only code probe; all application state lives in fresh in-memory SQLite DBs."""
import json
import sqlite3
import sys
from contextlib import closing
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "cases" / "checkout"))
from app import checkout
from store import initialize


def snapshot(db):
    return {
        "orders": db.execute("SELECT id, request_id, customer, cents FROM orders").fetchall(),
        "rewards": db.execute("SELECT order_id, points FROM rewards").fetchall(),
    }


with closing(sqlite3.connect(":memory:")) as db:
    initialize(db)
    first = checkout(db, "r1", "alice", 500)
    retry = checkout(db, "r1", "alice", 500)
    observed = snapshot(db)
    assert first == retry == {"order_id": 1}
    assert len(observed["orders"]) == 1 and observed["rewards"] == [(1, 5), (1, 5)]
    print("exact retry:", json.dumps({"responses": [first, retry], **observed}, sort_keys=True))

for customer, cents in [("alice", 900), ("bob", 500)]:
    with closing(sqlite3.connect(":memory:")) as db:
        initialize(db)
        checkout(db, "r1", "alice", 500)
        response = checkout(db, "r1", customer, cents)
        observed = snapshot(db)
        assert response == {"order_id": 1}
        assert observed["orders"] == [(1, "r1", "alice", 500)]
        assert len(observed["rewards"]) == 2
        print("conflicting retry:", json.dumps({"retry_payload": [customer, cents], "response": response, **observed}, sort_keys=True))

with closing(sqlite3.connect(":memory:")) as db:
    initialize(db)
    db.execute("CREATE TRIGGER fail_reward BEFORE INSERT ON rewards BEGIN SELECT RAISE(ABORT, 'reward unavailable'); END")
    try:
        checkout(db, "r1", "alice", 500)
    except sqlite3.IntegrityError as exc:
        error = str(exc)
    else:
        raise AssertionError("expected reward insertion to fail")
    db.rollback()
    observed = snapshot(db)
    assert observed == {"orders": [(1, "r1", "alice", 500)], "rewards": []}
    print("reward failure after rollback:", json.dumps({"error": error, **observed}, sort_keys=True))

print("All observation assertions passed: retries duplicate rewards and reward failure leaves a committed partial checkout.")
