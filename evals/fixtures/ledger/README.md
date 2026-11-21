# Ledger transfers

Use `Ledger.transfer(request_id, sender, receiver, amount)` to move positive integer
units between accounts. `SQLiteLedger` deliberately owns persistence; the public
facade validates domain input. Keep this adapter seam: an independently shipped
PostgreSQL adapter implements the same contract. No adapter replacement is requested.

A request ID identifies one payload. Repeating it returns the original receipt;
changing its payload is rejected. Postings are atomic, balances cannot become
negative, and failed transfers leave no receipt or postings. This fixture uses
an in-memory SQLite database; production deployments own connection lifecycle.

Run: `python3 -m unittest discover -s tests -v` from this folder.
