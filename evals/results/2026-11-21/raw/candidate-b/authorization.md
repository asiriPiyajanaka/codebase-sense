The change introduces an authorization regression through the export caller. Review scope: `change.diff`, the already-updated source under `current/`, both supplied callers and the existing test. No diff was applied and no source or tests were changed.

**[blocker] `current/service.py:2` — removal of ownership enforcement exposes another owner's invoice through the scheduled export entry point.** `change.diff:5` removes the service's owner comparison and `PermissionError`, relocating them to the HTTP controller (`change.diff:16`, `current/controller.py:5`). `current/export_job.py:4` also calls the exported service, using `requested_by` as the actor, but performs no authorization itself. Consequently `export_invoice({"i1": {"owner": "alice", "amount": 10}}, "bob", "i1")` returns 10. A direct non-owner `invoice_for` call returns the complete invoice. This contradicts `README.md:5`, which says invoices are private to their owner. The actor parameter remains in the service signature but is ignored, so its unchanged interface conceals the weakened guarantee.

The smallest correction is to restore the ownership decision inside `invoice_for`, protecting every caller. The controller's additional check can then be assessed for redundancy; duplicating the policy into the export job would leave future service callers exposed. No new authorization service or broader refactor is justified by this diff. Actual production scheduling and reachability beyond these exported functions were not inspected; the local privacy bypass through a real supplied caller was reproduced.

What remains understandable: both adapters still converge on one small exported invoice service; the HTTP path retains its check and denies the reproduced non-owner request. The lookup and return formats remain simple. The problem is where the policy is enforced, not the number of modules.

Useful behavioral tests should call the real service and both callers without mocking the service:

- The owner receives the invoice through `invoice_for`, HTTP and export; verify actual invoice data and export amount.
- A different actor receives `PermissionError` through each of those three boundaries and receives no invoice data or exported amount. The service and export cases fail against the current source.
- Verify missing-invoice behavior stays compatible with the existing lookup contract (`KeyError` from the supplied mapping), so restoring the check does not accidentally alter error semantics.

Existing check, from `/private/tmp/codebase-sense-qa-91vasxy9/jobs/candidate-b/cases/authorization`:

```sh
PYTHONDONTWRITEBYTECODE=1 /private/tmp/codebase-sense-qa-91vasxy9/venv/bin/python -m unittest discover -s tests -v
```

Exit 0:

```text
test_delegates_authorized_request (test_controller.ControllerTests.test_delegates_authorized_request) ... ok

Ran 1 test in 0.000s
OK
```

This test patches `controller.invoice_for` (`tests/test_controller.py:12`) and asserts only allowed-request delegation. It does not exercise real service authorization, any denial, or the export caller.

Supplemental probe, saved alongside this report:

```sh
PYTHONDONTWRITEBYTECODE=1 /private/tmp/codebase-sense-qa-91vasxy9/venv/bin/python /private/tmp/codebase-sense-qa-91vasxy9/jobs/candidate-b/reports/authorization_probe.py
```

Exit 0; the assertions reproduce the regression rather than verify privacy enforcement:

```text
owner HTTP and export: allowed, amount=10
non-owner HTTP: PermissionError not your invoice
non-owner service: returned {'owner': 'alice', 'amount': 10}
non-owner export: returned amount=10
Observed authorization regression reproduced through real service and export caller.
```

**Sense Card — private invoice access/export**

- **Scope/mode:** Supplied diff and two real entry points sharing one service; review. All supplied files inspected; no repository instruction files or git metadata were present.
- **Promise:** Only an invoice's owner may access its data (`README.md:5`).
- **Flow:** HTTP → owner check → service → invoice; scheduled export → service → amount, bypassing the relocated check.
- **Owner:** Before the diff, `invoice_for` owned the invariant. Current enforcement exists only in `current/controller.py:5`. `current/service.py:1` remains the shared capability and should regain ownership.
- **Change entry point:** `current/service.py:2`, the changed lookup that now ignores `actor_id`.
- **Checked:** Existing allowed delegation test passed. Real local owner HTTP/export paths passed and non-owner HTTP rejected. Real non-owner service and export calls returned private data, disproving the intended privacy guarantee for those paths.
- **Unverified:** Production authentication, scheduling, other unavailable callers, and all storage implementations. The inspected suite has a demonstrated absence of service/export denial coverage; its green result does not establish authorization.
- **Decision:** **Change** — restore the shared service's existing ownership guard; block acceptance of the diff until the bypass is corrected.
- **Next smallest action:** Add real non-owner service/export behavioral tests, observe their failure on this source, then restore the guard within a separately authorized implementation.
