"""Exercise real current service and both real callers without changing repository files."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "cases" / "authorization" / "current"))
from controller import get_invoice
from export_job import export_invoice
from service import invoice_for

db = {"i1": {"owner": "alice", "amount": 10}}
assert get_invoice(db, "alice", "i1") == db["i1"]
assert export_invoice(db, "alice", "i1") == 10
print("owner HTTP and export: allowed, amount=10")
try:
    get_invoice(db, "bob", "i1")
except PermissionError as exc:
    print("non-owner HTTP:", type(exc).__name__, str(exc))
else:
    raise AssertionError("expected HTTP controller to reject non-owner")
assert invoice_for(db, "bob", "i1") == db["i1"]
print("non-owner service: returned", invoice_for(db, "bob", "i1"))
assert export_invoice(db, "bob", "i1") == 10
print("non-owner export: returned amount=10")
print("Observed authorization regression reproduced through real service and export caller.")
