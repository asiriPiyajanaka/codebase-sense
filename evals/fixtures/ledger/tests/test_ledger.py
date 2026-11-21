import sqlite3
import unittest

from ledger import Ledger
from sqlite_adapter import SQLiteLedger


class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.addCleanup(self.db.close)
        self.ledger = Ledger(SQLiteLedger(self.db))
        self.db.executemany("INSERT INTO accounts VALUES (?, ?)", [("alice", 100), ("bob", 0)])
        self.db.commit()

    def balances(self):
        return self.db.execute("SELECT balance FROM accounts ORDER BY name").fetchall()

    def test_transfer_and_retry(self):
        self.assertEqual(self.ledger.transfer("r1", "alice", "bob", 40), "r1")
        self.assertEqual(self.ledger.transfer("r1", "alice", "bob", 40), "r1")
        self.assertEqual(self.balances(), [(60,), (40,)])
        self.assertEqual(self.db.execute("SELECT count(*) FROM transfers").fetchone()[0], 1)

    def test_conflicting_retry(self):
        self.ledger.transfer("r1", "alice", "bob", 40)
        with self.assertRaisesRegex(ValueError, "conflict"):
            self.ledger.transfer("r1", "alice", "bob", 30)
        self.assertEqual(self.balances(), [(60,), (40,)])

    def test_missing_receiver_rolls_back(self):
        with self.assertRaises(ValueError):
            self.ledger.transfer("r1", "alice", "missing", 40)
        self.assertEqual(self.balances(), [(100,), (0,)])
        self.assertEqual(self.db.execute("SELECT count(*) FROM transfers").fetchone()[0], 0)

    def test_insufficient_funds(self):
        with self.assertRaises(ValueError):
            self.ledger.transfer("r1", "alice", "bob", 101)
        self.assertEqual(self.balances(), [(100,), (0,)])

    def test_domain_validation(self):
        for amount in (0, -1, True, 1.5):
            with self.assertRaises(ValueError):
                self.ledger.transfer("r1", "alice", "bob", amount)
