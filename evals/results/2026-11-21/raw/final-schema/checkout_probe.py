"""Read-only checkout probes: all state is private, in-memory SQLite."""
import sqlite3

from app import checkout
from store import initialize


def new_db():
    db = sqlite3.connect(":memory:")
    initialize(db)
    return db


with new_db() as db:
    first = checkout(db, "retry", "alice", 500)
    second = checkout(db, "retry", "alice", 500)
    orders = db.execute("SELECT customer, cents FROM orders").fetchall()
    rewards = db.execute("SELECT points FROM rewards").fetchall()
    assert first == second == {"order_id": 1}
    assert orders == [("alice", 500)] and rewards == [(5,), (5,)]
    print(f"EXACT RETRY: responses={first}, {second}; orders={orders}; rewards={rewards}")

for customer, cents in (("alice", 1500), ("bob", 500)):
    with new_db() as db:
        first = checkout(db, "conflict", "alice", 500)
        second = checkout(db, "conflict", customer, cents)
        orders = db.execute("SELECT customer, cents FROM orders").fetchall()
        rewards = db.execute("SELECT points FROM rewards").fetchall()
        assert first == second == {"order_id": 1}
        assert orders == [("alice", 500)]
        assert rewards == [(5,), (cents // 100,)]
        print(f"CONFLICT ACCEPTED: retry_payload={(customer, cents)}; response={second}; orders={orders}; rewards={rewards}")

with new_db() as db:
    db.execute("CREATE TRIGGER reject_reward BEFORE INSERT ON rewards BEGIN SELECT RAISE(ABORT, 'reward rejected'); END")
    db.commit()
    try:
        checkout(db, "failure", "alice", 500)
    except sqlite3.IntegrityError as error:
        message = str(error)
    else:
        raise AssertionError("expected reward insert failure")
    db.rollback()
    orders = db.execute("SELECT customer, cents FROM orders").fetchall()
    rewards = db.execute("SELECT points FROM rewards").fetchall()
    assert orders == [("alice", 500)] and rewards == []
    print(f"PARTIAL COMMIT: error={message!r}; orders_after_rollback={orders}; rewards={rewards}")
print("PASS: counterexamples reproduced; intended retry and atomicity guarantees are violated.")
