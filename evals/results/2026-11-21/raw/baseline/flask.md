# Flask error-handler dispatch audit

Flask's existing division of registration, handler lookup, request dispatch, and outer exception handling is justified by distinct responsibilities. The inspected source and 30 passing scoped tests do not justify an architectural rewrite. The main opportunities are precise regression tests for interactions between scope precedence, exception classes, trapping, and propagation. No source or tests were changed.

## Registration and lookup ownership

`Scaffold.register_error_handler` normalizes a status code or exception class and stores its callable in `error_handler_spec[scope][code][exception_class]` (`src/flask/sansio/scaffold.py:642–700`). A recognized integer status resolves to its Werkzeug HTTP exception class; registering `500` and `InternalServerError` targets the same entry. Instances, unrecognized integer codes, and classes outside `Exception` are rejected. Registering the same normalized entry again replaces it.

Blueprint registration copies its handler maps into the application's registry under the actual registered blueprint name (`src/flask/sansio/blueprints.py:388–397`). `Blueprint.app_errorhandler` instead records application-wide registration (`sansio/blueprints.py:596–615`); it is not limited to that blueprint's URLs. The active request derives its blueprint ancestry from the matched endpoint, ordered from the current blueprint toward parents (`src/flask/wrappers.py:162–196`). A URL prefix by itself does not select blueprint error handlers when routing fails.

`App._find_error_handler` owns the lookup policy (`src/flask/sansio/app.py:823–846`). It does not invoke or log handlers. Its nested loops define this exact precedence:

| Priority | Search |
| --- | --- |
| First, for exceptions with an HTTP code | Current blueprint, parent blueprints, then application, in that code bucket |
| Then | Current blueprint, parent blueprints, then application, in the generic `None` code bucket |
| Within each scope and bucket | Exception MRO, choosing the first registered class |

For ordinary non-HTTP exceptions only the generic bucket is searched. The closest matching class wins **within** a scope, but class specificity is not compared globally across scopes. Thus an application `403` handler beats a blueprint `HTTPException` handler because the code bucket comes first. A blueprint `Exception` handler beats an application `ValueError` handler for `ValueError`, because blueprint scope precedes application scope within the same generic bucket. Both outcomes were confirmed through the test client.

Nested blueprint handlers fall back outward to parents, then application. An unmatched `/bp/missing` request uses the application's 404 handler, even if the blueprint has its own 404 handler; no endpoint was matched to establish the blueprint. An explicit `abort(404)` inside a matched blueprint view can use its handler.

## Dispatch and exception paths

`wsgi_app` creates and pushes the request context, calls `full_dispatch_request`, and owns the outer failure boundary and final context pop (`src/flask/app.py:1479–1536`). `full_dispatch_request` sends the request-started signal, preprocesses the request, dispatches if preprocessing did not supply a response, catches `Exception` through `handle_user_exception`, then finalizes the result (`app.py:904–920`). `dispatch_request` owns routing errors, automatic OPTIONS handling, and calling the matched view, rather than selecting error handlers (`app.py:879–902`).

`handle_user_exception` (`app.py:779–809`) handles the original exception. For ordinary untrapped `HTTPException`, it delegates to `handle_http_exception`; otherwise it searches for a handler and reraises if none exists. Handlers run through `ensure_sync` and return ordinary response values.

`handle_http_exception` (`app.py:744–777`) returns an unhandled HTTP exception as a response rather than treating it as an unexpected 500. On this normal HTTP path, exceptions with no HTTP code and internal `RoutingException`s bypass user error handlers. Routing redirects therefore continue to function even with broad registered HTTP handlers.

If no user handler handles an ordinary exception, a handler itself raises, or normal response finalization fails, that exception escapes to `wsgi_app`, which calls `handle_exception` (`app.py:811–863`). This outer path:

1. Sends `got_request_exception` with the escaping exception.
2. Resolves propagation: explicit `PROPAGATE_EXCEPTIONS` wins; if it is `None`, testing or debug mode enables propagation.
3. Reraises when propagation is enabled. Otherwise logs the error, wraps it in `InternalServerError(original_exception=e)`, finds a 500-compatible handler using the same blueprint/application lookup, and finalizes the resulting response.

Direct `abort(500)` reaches a handler with an ordinary `InternalServerError` whose `original_exception` is absent/`None`; an unexpected `KeyError` reaches the outer 500 handler wrapped with its original exception. If the `KeyError` handler raises `RuntimeError`, the wrapper contains that new `RuntimeError`, not the original `KeyError`. My probe observed status 500, `InternalServerError:RuntimeError`, and one signal carrying `RuntimeError`.

Handlers must return the intended status as part of their response. A handler named or registered for 500 that returns only a string can produce status 200; registration does not automatically impose the error code on a replacement response. An unhandled HTTP exception retains its own HTTP response behavior.

## Propagation, traps, and limits

`PROPAGATE_EXCEPTIONS=True`, debug, or testing does not skip a handler that matched in the user-exception path. Propagation is consulted after an exception escapes to the outer boundary. Similarly, trapping HTTP exceptions means bypassing the normal HTTP-special-case path, not disabling all registered handlers: `handle_user_exception` still calls `_find_error_handler`. A specific 403 handler ran successfully in a probe with both `TRAP_HTTP_EXCEPTIONS=True` and `PROPAGATE_EXCEPTIONS=True`.

`trap_http_exception` (`sansio/app.py:848–881`) traps all HTTP exceptions when configured, all `BadRequest` subclasses when `TRAP_BAD_REQUEST_ERRORS` is true, and implicitly only `BadRequestKeyError` when debug is true and that setting is unset. Debug alone does not trap every 400 response. The user-exception path also enables detailed bad-key descriptions in the relevant debug/trap cases.

The outer handler is not an endless recovery loop. If the selected 500 handler itself raises, it escapes; it is not redispatched repeatedly. `finalize_request(from_error_handler=True)` logs and suppresses failures in response postprocessing or `request_finished` signaling, but its initial `make_response` call is outside that suppression block (`app.py:922–951`). An invalid 500-handler return can therefore still escape. `BaseException` such as `KeyboardInterrupt` is reraised by `wsgi_app` while its `finally` still pops the context. Errors while later iterating a streaming response are outside the completed request-dispatch lookup sequence.

A matched user handler does not automatically emit `got_request_exception`; the outer unexpected-error path does. There are no automatic handler retries, business-state rollback, or guarantees that prior request side effects are undone. Cleanup and teardown ownership is separate from recovery into an HTTP response.

## Existing tests and recommendations

`tests/test_user_error_handler.py` covers unmatched exceptions, invalid registrations, class/MRO fallback, HTTP subclasses, application versus blueprint 500 handlers, generic HTTP/Exception handlers, direct versus wrapped 500 exceptions, and preservation of routing redirects. `tests/test_blueprints.py` covers blueprint-specific error handlers, `app_errorhandler`, parent fallback, and grandchild overrides. The inspected `tests/test_basic.py` cases cover status responses, before/after processing errors, propagation, `BaseException`, traps, and MRO precedence. `test_request_exception_signal` verifies the unexpected-error signal. These tests support the existing ownership boundaries rather than indicating a need to merge them.

Useful additional behavioral tests are:

1. A small precedence matrix through actual requests: application code handler versus blueprint generic HTTP handler; blueprint broad class versus application exact class; child generic handler versus parent code handler; and same-bucket exact class versus base class. Assert body and status, with distinguishable handler responses.
2. Contrast unmatched routing 404 and 405 under a blueprint URL prefix with `abort(404)` and `abort(405)` inside matched blueprint views. Verify application fallback, blueprint participation only for matched views, and unchanged redirect behavior.
3. Cross matched/unmatched handlers with explicit propagation true/false, testing/debug defaults, and HTTP trapping. Verify a matched handler still runs, while an unhandled trapped HTTP exception propagates or becomes a 500 according to configuration.
4. Make a user handler raise a different exception. Assert the chosen blueprint/application 500 handler receives `InternalServerError` with that new original exception, one unexpected-error signal is sent, and teardown runs. Also test a raising 500 handler without recursive dispatch.
5. For ordinary handled errors, unhandled wrapped errors, and errors during after-request processing, assert signal counts, response status, finalization, and context cleanup. Test response-conversion failure separately from suppressed postprocessing failure in the 500 path.
6. Re-register the same class/code and use blueprint `app_errorhandler` to confirm replacement and application-wide scope, including a renamed or nested blueprint.

Retain the existing structure. Clarifying trap and propagation behavior in documentation and expanding public-behavior coverage are justified. A new handler registry abstraction, dependency injection layer, generalized error router, or merged dispatch/lookup subsystem would add risk without a source-demonstrated benefit.

## Commands and observed results

Commands ran from `/private/tmp/codebase-sense-qa-91vasxy9/jobs/baseline/cases/flask`. Inspection used `rg -n`, `sed -n`, and `cat` on the cited application/sans-I/O/wrapper sections, the relevant tests, `pyproject.toml`, and `tests/conftest.py`. All request probes used Flask's in-process test client; no server was started. No installs or network operations were used.

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/private/tmp/codebase-sense-qa-91vasxy9/jobs/baseline/cases/flask/src /private/tmp/codebase-sense-qa-91vasxy9/venv/bin/python -m pytest -p no:cacheprovider tests/test_user_error_handler.py tests/test_blueprints.py::test_blueprint_specific_error_handling tests/test_blueprints.py::test_blueprint_specific_user_error_handling tests/test_blueprints.py::test_blueprint_app_error_handling tests/test_blueprints.py::test_nested_blueprint tests/test_basic.py::test_error_handling tests/test_basic.py::test_error_handling_processing tests/test_basic.py::test_baseexception_error_handling tests/test_basic.py::test_before_request_and_routing_errors tests/test_basic.py::test_user_error_handling tests/test_basic.py::test_http_error_subclass_handling tests/test_basic.py::test_errorhandler_precedence tests/test_basic.py::test_trap_bad_request_key_error tests/test_basic.py::test_trapping_of_all_http_exceptions tests/test_basic.py::test_error_handler_after_processor_error tests/test_basic.py::test_exception_propagation tests/test_signals.py::test_request_exception_signal -q
```

Result: exit 0, `30 passed in 0.16s`.

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/private/tmp/codebase-sense-qa-91vasxy9/jobs/baseline/cases/flask/src /private/tmp/codebase-sense-qa-91vasxy9/venv/bin/python - <<'PY'
from flask import Flask, Blueprint, abort, got_request_exception
from werkzeug.exceptions import HTTPException

def new_app():
    app=Flask(__name__)
    app.logger.disabled=True
    return app

app=new_app(); bp=Blueprint('bp',__name__)
bp.register_error_handler(HTTPException,lambda e: ('bp-http',e.code))
app.register_error_handler(403,lambda e: ('app-403',403))
bp.add_url_rule('/deny',view_func=lambda: abort(403))
app.register_blueprint(bp,url_prefix='/bp')
print('app_code_vs_bp_generic',app.test_client().get('/bp/deny').data.decode())

app=new_app(); bp=Blueprint('bp',__name__)
def raise_value(): raise ValueError('view')
bp.register_error_handler(Exception,lambda e: 'bp-exception')
app.register_error_handler(ValueError,lambda e:'app-value')
bp.add_url_rule('/error',view_func=raise_value)
app.register_blueprint(bp,url_prefix='/bp')
print('bp_generic_vs_app_specific_class',app.test_client().get('/bp/error').data.decode())

app=new_app(); bp=Blueprint('bp',__name__)
bp.register_error_handler(404,lambda e: ('bp-404',404))
app.register_error_handler(404,lambda e: ('app-404',404))
bp.add_url_rule('/exists',view_func=lambda: 'ok')
app.register_blueprint(bp,url_prefix='/bp')
print('routing_404_under_bp_prefix',app.test_client().get('/bp/missing').data.decode())

app=new_app(); app.config.update(PROPAGATE_EXCEPTIONS=True,TRAP_HTTP_EXCEPTIONS=True)
app.register_error_handler(403,lambda e: ('handled-403',403))
app.add_url_rule('/deny',view_func=lambda: abort(403))
print('trap_and_propagate_with_handler',app.test_client().get('/deny').data.decode())

app=new_app(); app.config['PROPAGATE_EXCEPTIONS']=False
signals=[]
def record(sender,exception): signals.append(type(exception).__name__)
got_request_exception.connect(record,app,weak=False)
def raise_key(): raise KeyError('view')
def broken_handler(e): raise RuntimeError('handler failed')
app.add_url_rule('/error',view_func=raise_key)
app.register_error_handler(KeyError,broken_handler)
app.register_error_handler(500,lambda e: (type(e).__name__+':'+type(e.original_exception).__name__,500))
r=app.test_client().get('/error')
print('handler_failure',r.status_code,r.data.decode(),'signals',signals)
got_request_exception.disconnect(record,app)
PY
```

Result: exit 0.

```text
app_code_vs_bp_generic app-403
bp_generic_vs_app_specific_class bp-exception
routing_404_under_bp_prefix app-404
trap_and_propagate_with_handler handled-403
handler_failure 500 InternalServerError:RuntimeError signals ['RuntimeError']
```
