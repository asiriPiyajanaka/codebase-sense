#!/usr/bin/env python3
"""Check fixture oracles independently of any agent's report (standard library).

Use --implementation PATH to check an approved disposable checkout implementation.
The shipped checkout fixture deliberately fails those business guarantees.
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path

FIXTURES = Path(__file__).with_name("fixtures").resolve()

CHECKOUT_ORACLE = r'''
import sqlite3
from app import checkout
from store import initialize

def fresh():
    db = sqlite3.connect(":memory:")
    initialize(db)
    return db

db = fresh()
result = checkout(db, "r1", "alice", 500)
assert result == {"order_id": 1}, result
assert checkout(db, "r1", "alice", 500) == result
assert db.execute("SELECT count(*) FROM orders").fetchone()[0] == 1
assert db.execute("SELECT sum(points) FROM rewards").fetchone()[0] == 5
for customer, cents in [("bob", 500), ("alice", 600)]:
    try:
        checkout(db, "r1", customer, cents)
    except ValueError:
        pass
    else:
        raise AssertionError("changed payload was accepted")
assert db.execute("SELECT sum(points) FROM rewards").fetchone()[0] == 5
db.close()
db = fresh()
db.execute("CREATE TRIGGER reject_reward BEFORE INSERT ON rewards BEGIN SELECT RAISE(ABORT, 'reward failure'); END")
try:
    checkout(db, "r2", "alice", 500)
except sqlite3.DatabaseError:
    pass
else:
    raise AssertionError("injected failure did not propagate")
assert db.execute("SELECT count(*) FROM orders").fetchone()[0] == 0
assert db.execute("SELECT count(*) FROM rewards").fetchone()[0] == 0
db.execute("DROP TRIGGER reject_reward")
assert checkout(db, "r2", "alice", 500) == {"order_id": 1}
assert db.execute("SELECT sum(points) FROM rewards").fetchone()[0] == 5
db.close()
print("checkout independent retry/conflict/rollback assertions passed")
'''


def run(directory, arguments, expect_success=True):
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    result = subprocess.run([sys.executable, *arguments], cwd=directory, env=env,
                            text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    label = "-c <independent oracle>" if arguments[0] == "-c" else " ".join(arguments)
    print(f"{Path(directory).name}: python {label}\n{result.stdout}", flush=True)
    if (result.returncode == 0) != expect_success:
        raise SystemExit(f"Unexpected oracle result: {directory} (exit {result.returncode})")
    return result.stdout


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--implementation", type=Path)
    args = parser.parse_args()
    if args.implementation:
        run(args.implementation.resolve(), ["-c", CHECKOUT_ORACLE])
        return
    for case in ("checkout", "ledger", "authorization"):
        run(FIXTURES / case, ["-m", "unittest", "discover", "-s", "tests", "-v"])
    run(FIXTURES / "checkout", ["-c", CHECKOUT_ORACLE], expect_success=False)
    blocked = run(FIXTURES / "blocked", ["-m", "unittest", "discover", "-s", "tests", "-v"],
                  expect_success=False)
    if "integration check blocked" not in blocked:
        raise SystemExit("Blocked fixture failed for an unexpected reason")
    run(FIXTURES / "authorization" / "current", ["-c", (
        "from export_job import export_invoice; "
        "db={'i1': {'owner': 'alice', 'amount': 50}}; "
        "assert export_invoice(db, 'bob', 'i1') == 50; "
        "print('oracle: unauthorized export is currently possible')")])
    print("Fixture oracle checks passed; expected broken cases remain demonstrably broken.")


if __name__ == "__main__":
    main()
