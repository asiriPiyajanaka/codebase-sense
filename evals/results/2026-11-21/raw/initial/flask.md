# Flask error-handler dispatch audit

Scope: request error dispatch, handler selection, blueprint/application precedence, and propagation. Mode: read-only audit using Codebase Sense v0.1.0. Source and tests were not changed. No AGENTS.md or relevant ADR was found. Git metadata is absent (`git status --short` exited 128), so history and pre-existing dirty state are unknown.

**Keep the current architecture.** Handler selection is already centralized, and the separation between sans-I/O registration/lookup and request-time execution has an explicit reuse constraint (`src/flask/sansio/README.md`: alternative Flask implementations, no I/O or Flask globals). The useful next work is targeted coverage and clearer precedence documentation, not merging dispatch layers.

## Sense Card

- **Promise:** registered handlers produce responses for matching request exceptions; HTTP errors normally retain HTTP response semantics, while unhandled ordinary exceptions become a 500 response or propagate according to configuration. Blueprint scope participates only when routing has identified a blueprint.
- **Flow:** `Flask.wsgi_app` pushes request context → `full_dispatch_request` runs preprocessing/view → `handle_user_exception` distinguishes ordinary and HTTP/trapped errors → centralized `_find_error_handler` → `ensure_sync(handler)(exception)` → `finalize_request`. Unhandled errors or errors from that path reach outer `handle_exception`, which propagates or wraps them in `InternalServerError` (`src/flask/app.py:1506,904,779,811`; `src/flask/sansio/app.py:823`).
- **Owner:** sans-I/O Scaffold/Blueprint own registration; sans-I/O App owns matching policy; request-aware Flask owns execution, trapping, propagation, logging/signaling, and response finalization. Applications own handler response contents and their explicit status codes.
- **Change entry point:** handler selection starts at `src/flask/sansio/app.py:_find_error_handler:823`; propagation/wrapping starts at `src/flask/app.py:handle_exception:811`; scope identity starts at `src/flask/wrappers.py:Request.blueprints:181`.
- **Verified:** 30 selected repository tests passed, covering registration validation, class hierarchy, code handling, blueprint precedence, nested blueprints, redirects, trapping, propagation, and response processing. Additional local client probes checked mixed code/scope precedence, generic blueprint versus specific application class, routing 404 versus explicit abort, and errors raised by handlers.
- **Verified limits:** an error raised by a user handler becomes the wrapped `original_exception` when propagation is disabled and is re-raised when enabled. If the 500 handler itself fails, its exception escapes; Flask does not recursively redispatch it forever.
- **Unknown:** async handler execution, custom subclass overrides/extensions, streaming response failures after dispatch, signal receiver failures, concurrent requests, and all configuration combinations. No live HTTP service was run; tests and probes used in-process clients.
- **Decision:** **Keep** ownership boundaries. Investigate/document surprising precedence combinations and preserve them with tests.
- **Next action:** add a compact cross-scope/code precedence matrix and handler-failure propagation matrix; no architectural refactor is justified by the inspected workflow.

## Registration and exact precedence

`Scaffold.errorhandler` delegates to `register_error_handler`; registration normalizes an HTTP integer code or exception class into an exception class plus optional code and stores it in `error_handler_spec[None][code][class]` (`src/flask/sansio/scaffold.py:635–654,657–698`). Invalid instances, non-exception classes, and unknown HTTP integers are rejected. An HTTP subclass that inherits code 403 belongs in the code-403 bucket even when registered by class.

Blueprint registration copies those maps under the blueprint's registered name, including nested/renamed registrations (`src/flask/sansio/blueprints.py:388–397`). `Blueprint.app_errorhandler` instead defers a registration on the application itself and therefore applies to every request (`:596–608`). It is not a blueprint-local handler with broader URL ownership.

For a matching exception, `_find_error_handler` iterates these dimensions in this order (`src/flask/sansio/app.py:831–845`):

1. The exception's HTTP-code bucket, then the no-code bucket; non-HTTP exceptions have only the latter.
2. Within a bucket, the current blueprint, its parents from inner to outer, then the application (`None`).
3. Within that scope, the exception class MRO from most specific to least specific.

The first match wins. `Request.blueprints` supplies inner-to-outer registered names, or an empty list when routing failed (`src/flask/wrappers.py:181–195`; `src/flask/helpers.py:635–639`). “Blueprint wins” is therefore conditional on the bucket; “most specific class wins” is conditional on the scope. This is consistent with the source method's explicit code-before-class ordering, but the broad prose in `docs/errorhandling.rst:169–173` is easy to overgeneralize.

Actual additional in-process client observations:

| Competing registrations / request | Selected response |
| --- | --- |
| Application 403, blueprint generic `HTTPException`; blueprint view aborts 403 | application handler: `403 app-code` |
| Application `ValueError`, blueprint generic `Exception`; blueprint view raises `ValueError` | blueprint handler: `500 bp-generic` |
| Application and blueprint 404; matched blueprint view aborts 404 | blueprint handler: `404 bp-404` |
| Same registrations; unmatched URL under `/bp/` | application handler: `404 app-404` |

An unmatched path prefix does not select a blueprint. Routing 404/405 therefore use application handlers, while an explicitly raised 404/405 in a matched blueprint view can use that blueprint's handler (`docs/errorhandling.rst:394–404`). Routing redirects (`RoutingException`) and HTTP exceptions without a code are returned unchanged by the normal HTTP path (`src/flask/app.py:763–777`); redirects must not become generic error pages. The existing redirect test protects this (`tests/test_user_error_handler.py:213–214`).

## Exception execution and propagation

`full_dispatch_request` catches ordinary `Exception` from request-start, preprocessing, or dispatch and calls `handle_user_exception` (`src/flask/app.py:913–920`). For an untrapped `HTTPException`, `handle_http_exception` finds a handler or returns the exception as a response. A handler is invoked through `ensure_sync`. Trapping bypasses the normal HTTP shortcut but still tries `_find_error_handler`; it does not mean “ignore all registered handlers” (`:801–809`). Without a matching handler it re-raises.

`TRAP_HTTP_EXCEPTIONS` traps all HTTP errors. `TRAP_BAD_REQUEST_ERRORS=True` traps `BadRequest`; when unset, debug mode traps `BadRequestKeyError` specifically, not every 400 (`src/flask/sansio/app.py:865–881`). Debug or the explicit bad-request trap also enables the missing-key exception detail (`src/flask/app.py:796–799`). The selected existing tests verify the important no-handler trap branches (`tests/test_basic.py:1032–1075`).

An exception with a registered ordinary handler is handled before propagation configuration is consulted. An unmatched ordinary exception, a user handler failure, or a normal finalization failure reaches the WSGI boundary's `handle_exception` (`src/flask/app.py:1512–1514`). That method emits `got_request_exception`, then evaluates `PROPAGATE_EXCEPTIONS`; `None` means `testing or debug`, while an explicit boolean overrides them (`:839–852`). When true, the original exception is re-raised. Otherwise it is logged, wrapped as `InternalServerError(original_exception=e)`, matched again using the same blueprint list, and finalized in error mode (`:854–862`). Thus a 500 handler receives the wrapper for an unhandled error; an explicitly raised HTTP 500 reaches the normal HTTP path directly and has no original error to wrap.

A probe used a view raising `KeyError` and a registered `KeyError` handler raising `ValueError('handler failure')`, with testing enabled. Explicit propagation false yielded a 500 handler receiving `(InternalServerError, original_exception=ValueError)` and a 500 response. Explicit propagation true raised that `ValueError` and skipped the 500 handler. A separate 500 handler raising `RuntimeError('500 handler failure')` escaped to the test client even with propagation false. These were actual observations, not inferred guarantees of universal fallback. Probe logging was disabled to keep output readable; logging and signaling behavior are source-backed, not independently verified by this run.

Error-mode finalization catches/logs failures in `process_response` and the request-finished signal, but `make_response` occurs outside that catch (`src/flask/app.py:939–951`). It is not a blanket suppression of every handler or response-conversion failure. The WSGI `finally` pops the request context (`:1519–1527`). `BaseException` subclasses such as `KeyboardInterrupt` are re-raised rather than rendered as 500; the selected existing test verifies this (`tests/test_basic.py:926–934`).

No retry, database rollback, or idempotency promise belongs to dispatch. Handler/view side effects remain application responsibilities.

## Architecture and test assessment

**Candidate: unify lookup, HTTP handling, user errors, and fatal errors into one dispatcher — Keep the current design.** The three request-time entry points reuse one matcher, rather than duplicating precedence policy. Their distinct treatment of routing control flow, registered user handlers, and unhandled errors is observable and covered by real clients. Combining them risks changing propagation timing, which exception 500 handlers receive, and when finalization/logging occur. Moving request globals or handler execution into sans-I/O lookup would violate its documented reuse boundary. The already-small matching contract is `_find_error_handler(exception, blueprint_names) -> handler | None`; no caller needs a new routing/error manager abstraction.

The tests are behavioral integration tests, not hollow mocks. `tests/test_user_error_handler.py` exercises registration rejection, inheritance, code/class aliases, generic handlers, blueprint handlers, and `original_exception`. `tests/test_blueprints.py:793` protects parent fallback and grandchild override, and `:1017` protects renamed registrations. `tests/test_basic.py:867,905,999,1032,1078,1581` protects status/body, response processors, MRO, trap policy, finalization failure, and propagation. Some handler tests assert body only; they do not establish that registering an HTTP-code handler automatically sets the response status.

Useful additions are:

1. A matrix crossing code bucket, blueprint/parent/application scope, and class MRO, including the first two probe cases. Assert selected handler, status, and headers. Existing default-handler tests register a blueprint-specific Forbidden handler, so they do not isolate application-code versus blueprint-generic competition.
2. Pair unmatched 404/405 routing with explicit aborts from matched blueprint views, including nested and renamed blueprints; assert no inference from URL prefix.
3. A handler that raises: explicit true/false/default propagation with debug/testing combinations, correct `original_exception`, a blueprint 500 handler versus application fallback, and deliberate behavior when that 500 handler itself fails.
4. Trapped HTTP errors with a registered matching handler, alongside no-handler propagation; this protects the distinction between bypassing the HTTP shortcut and skipping matching entirely.
5. Preserve default HTTP status and relevant headers when returning an HTTP exception; test ordinary handler response conversion and the boundary between finalization errors that are logged and response-conversion errors that escape. Async and signal failure branches warrant separate targeted coverage when their dependencies and intended scope are available.

The smallest justified action is coverage and a precedence documentation clarification. No source reorganization is recommended.

## Commands and results

`cat`, `rg`, and line-numbered source reads inspected the scoped source, docs, tests, and project configuration. Tests used the supplied virtual environment, disabled bytecode and pytest cache, and imported this copy via `PYTHONPATH`.

From this case root, the exact targeted invocation was:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/private/tmp/codebase-sense-qa-91vasxy9/jobs/initial/cases/flask/src /private/tmp/codebase-sense-qa-91vasxy9/venv/bin/python -m pytest -p no:cacheprovider -q tests/test_user_error_handler.py tests/test_basic.py::test_error_handling tests/test_basic.py::test_error_handling_processing tests/test_basic.py::test_baseexception_error_handling tests/test_basic.py::test_before_request_and_routing_errors tests/test_basic.py::test_user_error_handling tests/test_basic.py::test_http_error_subclass_handling tests/test_basic.py::test_errorhandler_precedence tests/test_basic.py::test_trap_bad_request_key_error tests/test_basic.py::test_trapping_of_all_http_exceptions tests/test_basic.py::test_error_handler_after_processor_error tests/test_basic.py::test_exception_propagation tests/test_blueprints.py::test_blueprint_specific_error_handling tests/test_blueprints.py::test_blueprint_specific_user_error_handling tests/test_blueprints.py::test_blueprint_app_error_handling tests/test_blueprints.py::test_nested_blueprint tests/test_blueprints.py::test_blueprint_renaming
```

Result: **30 passed in 0.16s**, exit 0. A separate heredoc with the same environment/interpreter printed `flask.__file__` under this copy's `src`, constructed fresh applications and blueprints, and exercised the mixed precedence and handler-failure cases described above using `test_client()`; exit 0. Expected failures were caught and printed by the observation script. No full-suite, async, live-server, network, install, window, or external-mutation operation was performed. No recommended new tests were written or claimed passing.
