# Checkout

`app.checkout(connection, request_id, customer, cents)` records an order and a
reward of `cents // 100` points. A successful call returns `{"order_id": int}`.
The same request may be delivered repeatedly after a response is lost. A request
ID identifies one customer's checkout with one amount. Preserve the response
shape. All state in this exercise is local SQLite; there is no payment gateway.

Run: `python3 -m unittest discover -s tests -v` from this folder.
