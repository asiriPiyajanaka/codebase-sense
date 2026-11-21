class SQLiteLedger:
    def __init__(self, db):
        self.db = db
        db.executescript("""
            CREATE TABLE accounts (name TEXT PRIMARY KEY, balance INTEGER CHECK(balance >= 0));
            CREATE TABLE transfers (request_id TEXT PRIMARY KEY, sender TEXT, receiver TEXT, amount INTEGER);
        """)

    def transfer(self, request_id, sender, receiver, amount):
        with self.db:
            # Serialize the read/write decision across independent connections.
            self.db.execute("BEGIN IMMEDIATE")
            previous = self.db.execute("SELECT sender, receiver, amount FROM transfers WHERE request_id=?",
                                       (request_id,)).fetchone()
            if previous:
                if previous != (sender, receiver, amount):
                    raise ValueError("request payload conflict")
                return request_id
            changed = self.db.execute("UPDATE accounts SET balance=balance-? WHERE name=? AND balance>=?",
                                      (amount, sender, amount)).rowcount
            if changed != 1:
                raise ValueError("insufficient funds or missing sender")
            if self.db.execute("UPDATE accounts SET balance=balance+? WHERE name=?", (amount, receiver)).rowcount != 1:
                raise ValueError("missing receiver")
            self.db.execute("INSERT INTO transfers VALUES (?, ?, ?, ?)", (request_id, sender, receiver, amount))
            return request_id
