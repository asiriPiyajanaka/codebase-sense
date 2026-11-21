import sqlite3
import unittest

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
