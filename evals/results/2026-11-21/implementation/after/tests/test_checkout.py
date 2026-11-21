from concurrent.futures import ThreadPoolExecutor
import sqlite3
import tempfile
from threading import Barrier
import unittest
from pathlib import Path

from app import checkout
from store import initialize


class CheckoutTests(unittest.TestCase):
    def test_success(self):
        with sqlite3.connect(":memory:") as db:
            initialize(db)
            self.assertEqual(checkout(db, "r1", "alice", 500), {"order_id": 1})
            self.assertEqual(db.execute("SELECT points FROM rewards").fetchall(), [(5,)])

    def test_invalid_input_has_no_effects(self):
        with sqlite3.connect(":memory:") as db:
            initialize(db)
            with self.assertRaises(ValueError):
                checkout(db, "r1", "alice", 0)
            self.assertEqual(db.execute("SELECT count(*) FROM orders").fetchone()[0], 0)


class CheckoutContractTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.addCleanup(self.db.close)
        initialize(self.db)

    def snapshot(self):
        return (
            self.db.execute("SELECT * FROM orders ORDER BY id").fetchall(),
            self.db.execute("SELECT * FROM rewards ORDER BY rowid").fetchall(),
        )

    def test_existing_validation_rejects_invalid_input_without_effects(self):
        invalid_inputs = [
            ("", "alice", 500),
            (None, "alice", 500),
            ("r1", "", 500),
            ("r1", None, 500),
            ("r1", "alice", 0),
            ("r1", "alice", -1),
            ("r1", "alice", True),
            ("r1", "alice", False),
            ("r1", "alice", 500.0),
            ("r1", "alice", "500"),
            ("r1", "alice", None),
        ]
        for request_id, customer, cents in invalid_inputs:
            with self.subTest(request_id=request_id, customer=customer, cents=cents):
                with self.assertRaisesRegex(ValueError, "invalid checkout"):
                    checkout(self.db, request_id, customer, cents)
                self.assertEqual(self.snapshot(), ([], []))

    def test_response_shape_order_ids_and_reward_rounding(self):
        for order_id, cents in enumerate((1, 99, 100, 199, 500), start=1):
            with self.subTest(cents=cents):
                response = checkout(self.db, f"r{order_id}", "alice", cents)
                self.assertEqual(response, {"order_id": order_id})
                self.assertIs(type(response["order_id"]), int)
        self.assertEqual(
            self.db.execute("SELECT order_id, points FROM rewards ORDER BY order_id").fetchall(),
            [(1, 0), (2, 0), (3, 1), (4, 1), (5, 5)],
        )

    def test_success_is_durable_without_a_caller_transaction(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "checkout.sqlite3"
            db = sqlite3.connect(path)
            try:
                initialize(db)
                response = checkout(db, "r1", "alice", 500)
                self.assertFalse(db.in_transaction)
                with sqlite3.connect(path) as observer:
                    self.assertEqual(
                        observer.execute("SELECT id, request_id, customer, cents FROM orders").fetchall(),
                        [(response["order_id"], "r1", "alice", 500)],
                    )
                    self.assertEqual(
                        observer.execute("SELECT order_id, points FROM rewards").fetchall(),
                        [(response["order_id"], 5)],
                    )
            finally:
                db.close()

    def test_exact_retry_returns_original_response_without_extra_rewards(self):
        response = checkout(self.db, "r1", "alice", 500)
        checkout(self.db, "other", "bob", 700)
        original_state = self.snapshot()
        for _ in range(3):
            self.assertEqual(checkout(self.db, "r1", "alice", 500), response)
            self.assertEqual(self.snapshot(), original_state)

    def test_changed_payload_is_rejected_without_state_changes(self):
        response = checkout(self.db, "r1", "alice", 500)
        original_state = self.snapshot()
        for customer, cents in (("bob", 500), ("alice", 600), ("bob", 600)):
            with self.subTest(customer=customer, cents=cents):
                with self.assertRaises(ValueError):
                    checkout(self.db, "r1", customer, cents)
                self.assertEqual(self.snapshot(), original_state)
        self.assertEqual(checkout(self.db, "r1", "alice", 500), response)
        self.assertEqual(self.snapshot(), original_state)

    def test_reward_failure_rolls_back_and_allows_same_id_recovery(self):
        self.db.execute("""
            CREATE TRIGGER fail_reward BEFORE INSERT ON rewards
            BEGIN
                SELECT RAISE(ABORT, 'reward unavailable');
            END
        """)
        with self.assertRaisesRegex(sqlite3.IntegrityError, "reward unavailable"):
            checkout(self.db, "r1", "alice", 500)
        self.assertEqual(self.snapshot(), ([], []))
        self.assertFalse(self.db.in_transaction)
        self.db.execute("DROP TRIGGER fail_reward")
        response = checkout(self.db, "r1", "alice", 500)
        self.assertEqual(response, {"order_id": 1})
        self.assertEqual(self.snapshot(), ([(1, "r1", "alice", 500)], [(1, 5)]))
        self.assertEqual(checkout(self.db, "r1", "alice", 500), response)
        self.assertEqual(self.snapshot(), ([(1, "r1", "alice", 500)], [(1, 5)]))

    def test_checkout_respects_an_existing_caller_transaction(self):
        self.db.execute("BEGIN")
        response = checkout(self.db, "r1", "alice", 500)
        self.assertEqual(response, {"order_id": 1})
        self.assertTrue(self.db.in_transaction)
        self.assertEqual(self.snapshot(), ([(1, "r1", "alice", 500)], [(1, 5)]))
        self.db.rollback()
        self.assertEqual(self.snapshot(), ([], []))

    def test_conflict_preserves_uncommitted_caller_work(self):
        checkout(self.db, "r1", "alice", 500)
        self.db.execute("INSERT INTO orders(request_id, customer, cents) VALUES ('pending', 'bob', 300)")
        original_state = self.snapshot()
        with self.assertRaises(ValueError):
            checkout(self.db, "r1", "carol", 500)
        self.assertTrue(self.db.in_transaction)
        self.assertEqual(self.snapshot(), original_state)
        self.db.rollback()
        self.assertEqual(self.snapshot(), ([(1, "r1", "alice", 500)], [(1, 5)]))

    def test_reward_failure_preserves_uncommitted_caller_work(self):
        self.db.execute("""
            CREATE TRIGGER fail_reward BEFORE INSERT ON rewards
            BEGIN
                SELECT RAISE(ABORT, 'reward unavailable');
            END
        """)
        self.db.execute("INSERT INTO orders(request_id, customer, cents) VALUES ('pending', 'bob', 300)")
        original_state = self.snapshot()
        with self.assertRaisesRegex(sqlite3.IntegrityError, "reward unavailable"):
            checkout(self.db, "r1", "alice", 500)
        self.assertTrue(self.db.in_transaction)
        self.assertEqual(self.snapshot(), original_state)
        self.db.rollback()
        self.assertEqual(self.snapshot(), ([], []))

    def test_atomicity_on_an_autocommit_connection(self):
        db = sqlite3.connect(":memory:", isolation_level=None)
        self.addCleanup(db.close)
        initialize(db)
        db.execute("""
            CREATE TRIGGER fail_reward BEFORE INSERT ON rewards
            BEGIN
                SELECT RAISE(ABORT, 'reward unavailable');
            END
        """)
        with self.assertRaisesRegex(sqlite3.IntegrityError, "reward unavailable"):
            checkout(db, "r1", "alice", 500)
        self.assertEqual(db.execute("SELECT * FROM orders").fetchall(), [])
        self.assertEqual(db.execute("SELECT * FROM rewards").fetchall(), [])
        self.assertFalse(db.in_transaction)
        db.execute("DROP TRIGGER fail_reward")
        response = checkout(db, "r1", "alice", 500)
        self.assertEqual(checkout(db, "r1", "alice", 500), response)
        self.assertEqual(db.execute("SELECT * FROM rewards").fetchall(), [(response["order_id"], 5)])

    def concurrent_checkouts(self, customers):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "checkout.sqlite3"
            db = sqlite3.connect(path)
            try:
                initialize(db)
            finally:
                db.close()
            barrier = Barrier(2)

            def submit(customer):
                connection = sqlite3.connect(path, timeout=5)
                try:
                    barrier.wait(timeout=5)
                    try:
                        return checkout(connection, "r1", customer, 500)
                    except ValueError as error:
                        return error
                finally:
                    connection.close()

            with ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(submit, customers))
            observer = sqlite3.connect(path)
            try:
                state = (
                    observer.execute("SELECT * FROM orders").fetchall(),
                    observer.execute("SELECT * FROM rewards").fetchall(),
                )
            finally:
                observer.close()
            return results, state

    def test_concurrent_exact_retries_share_one_order_and_reward(self):
        results, state = self.concurrent_checkouts(("alice", "alice"))
        self.assertEqual(results, [{"order_id": 1}, {"order_id": 1}])
        self.assertEqual(state, ([(1, "r1", "alice", 500)], [(1, 5)]))

    def test_concurrent_conflicting_requests_have_one_winner(self):
        results, state = self.concurrent_checkouts(("alice", "bob"))
        successes = [result for result in results if isinstance(result, dict)]
        failures = [result for result in results if isinstance(result, ValueError)]
        self.assertEqual(successes, [{"order_id": 1}])
        self.assertEqual(len(failures), 1)
        winner = ("alice", "bob")[next(index for index, result in enumerate(results) if isinstance(result, dict))]
        self.assertEqual(state, ([(1, "r1", winner, 500)], [(1, 5)]))
