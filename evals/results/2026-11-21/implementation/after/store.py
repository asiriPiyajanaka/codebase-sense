def initialize(db):
    db.executescript("""
        CREATE TABLE orders (
            id INTEGER PRIMARY KEY, request_id TEXT UNIQUE,
            customer TEXT NOT NULL, cents INTEGER NOT NULL
        );
        CREATE TABLE rewards (order_id INTEGER, points INTEGER NOT NULL);
    """)


def record_order(db, request_id, customer, cents):
    db.execute("INSERT OR IGNORE INTO orders(request_id, customer, cents) VALUES (?, ?, ?)",
               (request_id, customer, cents))
    db.commit()
    return db.execute("SELECT id FROM orders WHERE request_id = ?", (request_id,)).fetchone()[0]


def award_points(db, order_id, cents):
    db.execute("INSERT INTO rewards(order_id, points) VALUES (?, ?)", (order_id, cents // 100))
    db.commit()


def complete_checkout(db, request_id, customer, cents):
    owns_transaction = not db.in_transaction
    if owns_transaction:
        db.execute("BEGIN IMMEDIATE")
    else:
        db.execute("SAVEPOINT checkout_operation")
    try:
        previous = db.execute(
            "SELECT id, customer, cents FROM orders WHERE request_id = ?", (request_id,)
        ).fetchone()
        if previous is not None:
            order_id, old_customer, old_cents = previous
            if (old_customer, old_cents) != (customer, cents):
                raise ValueError("request payload conflict")
        else:
            order_id = db.execute(
                "INSERT INTO orders(request_id, customer, cents) VALUES (?, ?, ?)",
                (request_id, customer, cents),
            ).lastrowid
            db.execute("INSERT INTO rewards(order_id, points) VALUES (?, ?)", (order_id, cents // 100))
        if owns_transaction:
            db.commit()
        else:
            db.execute("RELEASE SAVEPOINT checkout_operation")
        return order_id
    except BaseException:
        if owns_transaction:
            db.rollback()
        else:
            db.execute("ROLLBACK TO SAVEPOINT checkout_operation")
            db.execute("RELEASE SAVEPOINT checkout_operation")
        raise
