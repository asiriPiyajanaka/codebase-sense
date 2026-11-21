#!/usr/bin/env python3
"""Read-only audit probe; only creates disposable in-memory SQLite state."""
import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "cases" / "checkout"))
from app import checkout
from store import initialize


def snapshot(db):
    return {
        "orders": db.execute("SELECT id, request_id, customer, cents FROM orders ORDER BY id").fetchall(),
        "rewards": db.execute("SELECT order_id, points FROM rewards ORDER BY rowid").fetchall(),
    }


with sqlite3.connect(":memory:") as db:
    initialize(db)
    receipts = [checkout(db, "r1", "alice", 500), checkout(db, "r1", "alice", 500)]
    state = snapshot(db)
    assert receipts == [{"order_id": 1}, {"order_id": 1}]
    assert state["rewards"] == [(1, 5), (1, 5)]
    print("exact_retry", json.dumps({"responses": receipts, **state}, sort_keys=True))

for customer, cents in (("alice", 900), ("bob", 500)):
    with sqlite3.connect(":memory:") as db:
        initialize(db)
        checkout(db, "r1", "alice", 500)
        receipt = checkout(db, "r1", customer, cents)
        state = snapshot(db)
        assert receipt == {"order_id": 1}
        assert state["orders"] == [(1, "r1", "alice", 500)]
        assert state["rewards"] == [(1, 5), (1, cents // 100)]
        print("conflicting_retry", json.dumps({"retry": [customer, cents], "response": receipt, **state}, sort_keys=True))

with sqlite3.connect(":memory:") as db:
    initialize(db)
    db.execute("CREATE TRIGGER reject_reward BEFORE INSERT ON rewards BEGIN SELECT RAISE(ABORT, 'reward unavailable'); END")
    db.commit()
    try:
        checkout(db, "r1", "alice", 500)
    except sqlite3.IntegrityError as error:
        failure = str(error)
    else:
        raise AssertionError("expected injected SQLite failure")
    db.rollback()
    state = snapshot(db)
    assert state["orders"] == [(1, "r1", "alice", 500)]
    assert state["rewards"] == []
    print("reward_failure_after_rollback", json.dumps({"error": failure, **state}, sort_keys=True))
    db.execute("DROP TRIGGER reject_reward")
    receipt = checkout(db, "r1", "alice", 500)
    print("retry_after_failure", json.dumps({"response": receipt, **snapshot(db)}, sort_keys=True))
