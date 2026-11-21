import sqlite3
from app import checkout
from store import initialize

def fresh():
    db = sqlite3.connect(':memory:')
    initialize(db)
    return db

def state(db):
    return {'orders': db.execute('SELECT request_id, customer, cents FROM orders').fetchall(), 'rewards': db.execute('SELECT order_id, points FROM rewards').fetchall()}

db = fresh()
print('retry responses:', checkout(db, 'r1', 'alice', 500), checkout(db, 'r1', 'alice', 500))
print('retry state:', state(db))
db.close()
db = fresh()
checkout(db, 'r1', 'alice', 500)
print('conflict response:', checkout(db, 'r1', 'bob', 900))
print('conflict state:', state(db))
db.close()
db = fresh()
db.execute("CREATE TRIGGER reward_failure BEFORE INSERT ON rewards BEGIN SELECT RAISE(ABORT, 'reward failed'); END")
try:
    checkout(db, 'r1', 'alice', 500)
except sqlite3.IntegrityError as e:
    print('failure:', type(e).__name__, str(e))
print('failure state:', state(db))
db.close()

