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
