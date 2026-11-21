Scope: a routed request raising an exception, from registration and handler lookup through response finalization or propagation, including blueprint/application precedence. Mode: **audit**. I inspected the scoped source, error-handling documentation, pytest configuration/fixtures, and relevant tests. Source and tests were left unchanged. No `AGENTS.md`, ADR, or git metadata was present in this copy; this is not a full Flask audit.

**Keep the error-dispatch architecture.** Handler registration, lookup order, and request execution have distinct, understandable owners. The relevant 30 existing test cases passed, and additional local test-client probes confirmed the precedence and propagation edge cases below. More useful next work is explicit cross-precedence coverage and documentation clarification; this inspection does not justify a new dispatcher abstraction or changing handler selection.

**Sense Card — error-handler dispatch**

- **Promise:** a request exception reaches the registered handler selected by HTTP-code tier, request blueprint scope, and exception hierarchy; otherwise an HTTP exception becomes its response, or an unhandled exception propagates or becomes a 500 according to configuration. A handler controls the response it returns, including status.
- **Flow:** `Flask.wsgi_app` → `full_dispatch_request` → preprocessor/view → `handle_user_exception` → `handle_http_exception` or shared `_find_error_handler` → handler via `ensure_sync` → `finalize_request`. An uncaught exception or failing handler reaches outer `handle_exception`, which propagates or wraps it for 500 handling (`src/flask/app.py:1506–1527,904–951,744–862`).
- **Current owners:** `sansio.scaffold.Scaffold.register_error_handler` normalizes class/code and stores registrations (`src/flask/sansio/scaffold.py:642–698`). Blueprint registration merges namespaced maps (`sansio/blueprints.py:379–397`). `sansio.app.App._find_error_handler` owns selection (`:823–846`). `Request.blueprints` supplies inner-to-outer scope (`wrappers.py:181–195`, `helpers.py:634–641`). Runtime `Flask` owns invocation, fallback, logging/signals, propagation, and finalization.
- **Change entry point:** precedence: `_find_error_handler` and the supplied `request.blueprints`; unmatched-route ownership: `Request.blueprint`; propagation/wrapped exception: `Flask.handle_exception`; handler registration: `Scaffold.register_error_handler`.
- **Verified:** existing tests passed for class/code aliases, subclass/MRO dispatch, blueprint and parent fallback, routing redirects, trap modes, error finalization, and propagation. Separate probes confirmed application code-specific versus blueprint-generic priority, unmatched blueprint-prefix 404, blueprint generic versus application subclass priority, registered handlers in propagation/trap modes, and wrapped handler failures. Commands/results are below.
- **Unknown:** async handler execution, signals/logging failure, streaming exceptions after a response is returned, all 405 combinations, and every response-conversion failure were not runtime-verified in this audit.
- **Decision / next action:** **Keep.** Add narrowly targeted public test-client cases for cross-tier precedence and handler failure, and clarify the misleading broad wording described below. No architectural change recommended.

The actual selection order is more precise than “blueprints always win.” Registration maps an HTTP status code to its exception class, then stores under `error_handler_spec[None][code][class]`; ordinary exception classes use the `None` code bucket (`scaffold.py:653–698`). When a blueprint is registered, its local map is copied under the blueprint's registered name (`blueprints.py:388–397`). `Blueprint.app_errorhandler` instead registers an application-wide handler during setup (`:596–608`). Blueprint naming is therefore part of dispatch identity, not an inferred URL-prefix policy.

`_find_error_handler` loops in this order (`sansio/app.py:831–845`):

1. For an HTTP exception, search its specific code bucket across all scopes; then search the generic `None` bucket. For an ordinary exception, search only `None`.
2. Within each bucket, search the active blueprint, its parents, then the application (`None`). `Request.blueprints` is derived from the matched endpoint; `_split_blueprint_path` produces inner-to-outer names.
3. Within each scope, follow the raised exception class's Python MRO and return the first registered handler.

Consequently, an application `403` handler beats a blueprint `HTTPException` handler: the application's code bucket is searched before any generic bucket. Within the same bucket, a blueprint `Exception` handler can beat an application's more specific `KeyError` handler, because scope is searched before the MRO of the next scope. Both outcomes were reproduced through real `test_client` requests. Neither is evidence to invert the loops: the current lookup docstring explicitly describes the code-first policy (`sansio/app.py:826–829`), and changing it would alter user-visible handler selection.

A routing 404 or 405 has no matched blueprint, even if its URL begins with that blueprint's prefix. `Request.blueprint` explicitly returns `None` when URL matching failed (`wrappers.py:162–178`), so application handlers apply. In contrast, an explicit `abort(404)` raised inside a blueprint view has a matched endpoint and can use blueprint handlers. This distinction is documented in `docs/errorhandling.rst:390–405`; the probe confirms the unmatched-prefix 404 case. Existing `test_nested_blueprint` checks parent fallback and a grandchild override (`tests/test_blueprints.py:793–839`); `test_blueprint_renaming` exercises registered-name behavior (`:1017–1046`).

Runtime dispatch has two intentional stages. `full_dispatch_request` catches `Exception` from preprocessing or view dispatch and calls `handle_user_exception` (`app.py:913–920`). Normal HTTP exceptions go through `handle_http_exception`; exceptions without a code and internal routing exceptions such as slash redirects are returned unchanged rather than dispatched to user error handlers (`:763–777`). Ordinary exceptions, and HTTP exceptions under trap mode, use shared lookup directly and re-raise if no handler exists (`:801–809`). A found handler is invoked through `ensure_sync` and its result is finalized like a view result. Returning a string alone can produce status 200; Flask does not automatically retain the raised error's status. The probe's blueprint generic handler deliberately demonstrates this.

`PROPAGATE_EXCEPTIONS` takes effect only if an exception escapes this first stage. A registered handler still handles its error with propagation set true, as reproduced. Outer `wsgi_app` sends uncaught `Exception`s to `handle_exception`; `BaseException` subclasses propagate while context teardown still runs (`app.py:1512–1527`). `handle_exception` emits `got_request_exception`, uses explicit propagation configuration or defaults to `testing or debug`, and re-raises when enabled (`:839–852`). Otherwise it logs, wraps the failure in `InternalServerError(original_exception=e)`, looks up a handler for that wrapper, and finalizes with error-safe processing (`:854–862`). A 500 handler receives the wrapper rather than the original exception. If the original failure happened inside a user handler, `original_exception` is that handler's failure; the probe verifies `RuntimeError` rather than the first view `ValueError`.

The fallback is not an unlimited recovery loop. A failing 500 handler or invalid return can still escape; `finalize_request(..., from_error_handler=True)` only catches failures inside its postprocessing block, while `make_response` is before that block (`app.py:939–950`). This is source inspection, not a claim that these failure cases ran. Callback side effects are application-owned: error dispatch does not roll back arbitrary work or provide request retry/idempotency guarantees.

The inspected tests already provide useful behavior coverage: `test_user_error_handler.py` covers invalid registrations, exact/class fallback, HTTP subclasses, blueprint versus application handling, generic handlers, wrapped originals, and redirect preservation. The selected basic tests cover custom response status, error postprocessing, MRO multiple inheritance, bad-request trap modes, `BaseException`, before/after-processing failures, and propagation defaults (`tests/test_basic.py:867–1104,1581–1595`). Blueprint tests cover local, application-wide, nested, and renamed registration. These are in-process requests against real routing and handler code, not mock-call assertions.

The source and tests support keeping the present boundaries. Runtime handling and Sans-I/O registration/selection evolve for different reasons; moving lookup into a new service or duplicating it per blueprint would add policy owners. The maintainability friction is wording and uncovered combinations. `docs/errorhandling.rst:169–173` broadly says blueprint handlers take precedence; qualify that within the code/class tiers. `trap_http_exception`'s docstring (`sansio/app.py:854–857`) suggests a trapped exception's handler is not called, but `handle_user_exception` still performs lookup and the probe confirms a registered 404 handler runs under `TRAP_HTTP_EXCEPTIONS=True`. Record this source/documentation contradiction rather than changing dispatch to match an overbroad sentence.

The smallest useful additional tests are parameterized test-client cases asserting selected body, status, and handler argument:

- Application `403` versus blueprint `HTTPException`, then blueprint `Exception` versus application `KeyError`, to pin bucket/scope/MRO ordering.
- Explicit blueprint 404/405 versus unmatched URL/wrong-method routing errors, including a nested or renamed blueprint where appropriate.
- A handler raising a second exception: production-style propagation false should pass a wrapper containing the second error to the selected 500 handler; propagation true should re-raise it.
- Registered handler with propagation true, and a registered HTTP handler with trap mode true, to distinguish lookup from unhandled fallback.

The saved probes characterize these combinations without editing the suite. Promote the relevant cases before touching dispatch; retain the existing tests and public registration API.

Checks ran from `/private/tmp/codebase-sense-qa-91vasxy9/jobs/candidate-a/cases/flask` after inspecting configuration and fixtures. The selected tests use local test clients; no socket, server, installation, or browser was used.

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/private/tmp/codebase-sense-qa-91vasxy9/jobs/candidate-a/cases/flask/src /private/tmp/codebase-sense-qa-91vasxy9/venv/bin/python -m pytest -p no:cacheprovider -q tests/test_user_error_handler.py tests/test_blueprints.py::test_blueprint_specific_error_handling tests/test_blueprints.py::test_blueprint_specific_user_error_handling tests/test_blueprints.py::test_blueprint_app_error_handling tests/test_blueprints.py::test_nested_blueprint tests/test_blueprints.py::test_blueprint_renaming tests/test_basic.py::test_error_handling tests/test_basic.py::test_error_handling_processing tests/test_basic.py::test_baseexception_error_handling tests/test_basic.py::test_before_request_and_routing_errors tests/test_basic.py::test_user_error_handling tests/test_basic.py::test_http_error_subclass_handling tests/test_basic.py::test_errorhandler_precedence tests/test_basic.py::test_trap_bad_request_key_error tests/test_basic.py::test_trapping_of_all_http_exceptions tests/test_basic.py::test_error_handler_after_processor_error tests/test_basic.py::test_exception_propagation
```

Exit **0**, exact output:

```text
..............................                                           [100%]
30 passed in 0.16s
```

The saved [flask-probe.py](flask-probe.py) performs additional assertions through the local package's test client. It suppresses only its own application's expected fallback logging; it does not replace infrastructure or handlers with mocks.

```sh
PYTHONDONTWRITEBYTECODE=1 /private/tmp/codebase-sense-qa-91vasxy9/venv/bin/python /private/tmp/codebase-sense-qa-91vasxy9/jobs/candidate-a/reports/flask-probe.py
```

Exit **0**, exact output:

```text
app_code_before_blueprint_generic {"body": "application-code", "status": 403}
unmatched_blueprint_prefix {"body": "application-routing-404", "status": 404}
blueprint_scope_before_application_mro_even_when_propagating {"body": "blueprint-generic-exception", "status": 200}
trapped_http_with_registered_handler {"body": "registered-handler-still-applies", "status": 404}
unhandled_wrapped_for_500_handler {"body": "wrapped:LookupError", "status": 500}
handler_failure_wrapped_for_500_handler {"body": "wrapped:RuntimeError", "status": 500}
unhandled_propagation {"exception": "LookupError", "message": "original"}
```
