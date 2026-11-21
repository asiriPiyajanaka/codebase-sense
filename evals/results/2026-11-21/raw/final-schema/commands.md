# Commands and results

All Python checks use the supplied interpreter with `PYTHONDONTWRITEBYTECODE=1`. Fixture source, tests, dependencies, and configuration remain read-only. Output artifacts and probes are confined to this reports directory.

## checkout working tree

Working directory: `/private/tmp/codebase-sense-qa-91vasxy9/jobs/final-schema/cases/checkout`

```sh
git --no-optional-locks status --short
```

Exit: 128

```text
fatal: not a git repository (or any of the parent directories): .git
```

## checkout existing check

Working directory: `/private/tmp/codebase-sense-qa-91vasxy9/jobs/final-schema/cases/checkout`

```sh
PYTHONDONTWRITEBYTECODE=1 /private/tmp/codebase-sense-qa-91vasxy9/venv/bin/python -m unittest discover -s tests -v
```

Exit: 0

```text
test_invalid_input_has_no_effects (test_checkout.CheckoutTests.test_invalid_input_has_no_effects) ... ok
test_success (test_checkout.CheckoutTests.test_success) ... ok

----------------------------------------------------------------------
Ran 2 tests in 0.001s

OK
```

## ledger working tree

Working directory: `/private/tmp/codebase-sense-qa-91vasxy9/jobs/final-schema/cases/ledger`

```sh
git --no-optional-locks status --short
```

Exit: 128

```text
fatal: not a git repository (or any of the parent directories): .git
```

## ledger existing check

Working directory: `/private/tmp/codebase-sense-qa-91vasxy9/jobs/final-schema/cases/ledger`

```sh
PYTHONDONTWRITEBYTECODE=1 /private/tmp/codebase-sense-qa-91vasxy9/venv/bin/python -m unittest discover -s tests -v
```

Exit: 0

```text
test_conflicting_retry (test_ledger.LedgerTests.test_conflicting_retry) ... ok
test_domain_validation (test_ledger.LedgerTests.test_domain_validation) ... ok
test_insufficient_funds (test_ledger.LedgerTests.test_insufficient_funds) ... ok
test_missing_receiver_rolls_back (test_ledger.LedgerTests.test_missing_receiver_rolls_back) ... ok
test_transfer_and_retry (test_ledger.LedgerTests.test_transfer_and_retry) ... ok

----------------------------------------------------------------------
Ran 5 tests in 0.001s

OK
```

## blocked working tree

Working directory: `/private/tmp/codebase-sense-qa-91vasxy9/jobs/final-schema/cases/blocked`

```sh
git --no-optional-locks status --short
```

Exit: 128

```text
fatal: not a git repository (or any of the parent directories): .git
```

## blocked existing check

Working directory: `/private/tmp/codebase-sense-qa-91vasxy9/jobs/final-schema/cases/blocked`

```sh
PYTHONDONTWRITEBYTECODE=1 /private/tmp/codebase-sense-qa-91vasxy9/venv/bin/python -m unittest discover -s tests -v
```

Exit: 5

```text
setUpClass (test_cancel.CancellationIntegrationTests) ... ERROR

======================================================================
ERROR: setUpClass (test_cancel.CancellationIntegrationTests)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "/private/tmp/codebase-sense-qa-91vasxy9/jobs/final-schema/cases/blocked/tests/test_cancel.py", line 9, in setUpClass
    raise RuntimeError("WAREHOUSE_TEST_DATABASE is not provisioned; integration check blocked")
RuntimeError: WAREHOUSE_TEST_DATABASE is not provisioned; integration check blocked

----------------------------------------------------------------------
Ran 0 tests in 0.000s

FAILED (errors=1)
```

## incomplete working tree

Working directory: `/private/tmp/codebase-sense-qa-91vasxy9/jobs/final-schema/cases/incomplete`

```sh
git --no-optional-locks status --short
```

Exit: 128

```text
fatal: not a git repository (or any of the parent directories): .git
```
