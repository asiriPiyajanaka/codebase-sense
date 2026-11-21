# Approved disposable checkout demonstration

The skill worker established a two-test baseline and wrote behavioral regressions,
then hit the account usage limit before changing source. The primary agent
completed the small implementation and verification. This is not an independent
end-to-end implementation success for the skill.

The original fixture remains under `evals/fixtures/checkout`; the approved copy's
final files are under [after/](after/). [red.txt](red.txt) records the 14-test suite
against original source: failure records cover retries, conflicts, partial commits,
autocommit, concurrency and transaction composition. [green.txt](green.txt)
records 14 passing tests after the change. Failure records include subtests and
must not be interpreted as a count of distinct defects.

`app.checkout` preserves arguments, input validation, reward rounding and the
`{"order_id": int}` success shape. `store.complete_checkout` owns payload comparison,
one local order/reward transaction and retry return. Standalone calls acquire
`BEGIN IMMEDIATE`; matching retries return the original ID without another reward;
changed payloads raise ValueError. A reward failure rolls back the new operation.
Existing store helpers are retained for compatibility but the checkout caller no
longer uses their independently committing path.

The regression suite uses real SQLite state and triggers, separate connections
for durable readback, and two simultaneous connections for identical/conflicting
requests. The prewritten [independent oracle](../../../check_fixtures.py) also
passed against this copy; its command/result is in the parent primary-checks folder.

## Explicit behavior change and limits

For an already-active caller transaction, this demonstration uses a savepoint:
checkout success is provisional until the caller commits; a checkout failure
does not roll back unrelated caller work. The original helpers committed ambient
work. **This is an intentional transaction-contract change**, not characterization
of preserved behavior. A real-project refactor would need explicit agreement on
this contract before applying it. The only supplied application caller does not
establish an ambient transaction. No real target project was modified.

There is no production migration, old-data repair, remote payment, distributed
exactly-once guarantee, crash-durability certification, or concurrent ambient
transaction proof. Existing inconsistent orders/rewards are not repaired by the
new exact-retry lookup. Storage errors and lock timeouts can still propagate.

Reproduce from the repository root:

```bash
python3 evals/check_fixtures.py --implementation evals/results/2026-11-21/implementation/after
cd evals/results/2026-11-21/implementation/after
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
```
