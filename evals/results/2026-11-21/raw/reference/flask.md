# Flask error-handler dispatch audit

Recommendation: preserve the current dispatch ownership and deepen behavioral coverage of precedence and failure composition. The central lookup already implements the selection policy; the reviewed source does not justify an architectural extraction or replacement.

## Scope and evidence

The named workflow set scope: handler registration, blueprint/application precedence, HTTP and ordinary exception handling, propagation, response finalization and teardown. No change-history inference was needed. No GLOSSARY.md or docs/adr decisions were present.

| Files and lines | Ownership |
| --- | --- |
| src/flask/sansio/scaffold.py:598–698 | registration, class/code normalization |
| src/flask/sansio/blueprints.py:379–397 | copying blueprint registrations into app registry |
| src/flask/sansio/app.py:823–846 | ordered handler selection |
| src/flask/sansio/app.py:848–879 | HTTP trap policy |
| src/flask/wrappers.py:162–195 | matched blueprint and innermost-to-outermost blueprint names |
| src/flask/app.py:744–809 | HTTP/user exception handling and registered-handler invocation |
| src/flask/app.py:811–862 | unhandled exceptions, propagation, logging, wrapped 500 |
| src/flask/app.py:879–951 | request dispatch, catch, and response finalization |
| src/flask/app.py:1479–1535 | outer request ownership and unconditional Context pop |
| src/flask/app.py:1326–1359; src/flask/ctx.py:396–430 | teardown and Context reset |

Domain language comes from the source's request, blueprint, application, error handler and response vocabulary. Source and tests were not edited.

## Registration and selection ownership

errorhandler calls register_error_handler. Registration normalizes an integer HTTP code to its exception class, or accepts an Exception subclass, then stores a handler under scope, code and class. Arbitrary Exception classes use code=None. A blueprint's registrations are copied into the app registry under its registered name, including nesting and renaming.

_find_error_handler is the single policy implementation. Its search order is the nested loop:

1. For an HTTP exception with a code, search that code bucket first; then the code=None bucket. Non-HTTP exceptions search only None.
2. Within each bucket, search request.blueprints in order from innermost to outermost, then application scope (None).
3. Within each scope, search the thrown exception's class MRO from most specific to least specific.
4. Return the first registered handler, otherwise None.

This ordering has consequences that “blueprint always wins” misses:

- An application handler for 404 beats a blueprint's generic HTTPException handler: all code buckets across scopes precede generic buckets.
- Within the same bucket, a blueprint base-class handler can beat a more specific application handler, because scope precedes MRO.
- A nested child handler beats its parent's handler in the same bucket; absent a child match, parents and application remain fallbacks.
- A routing 404 or 405 cannot be assigned to a blueprint merely from its URL prefix. No endpoint has matched, so request.blueprints is empty and application handlers are considered.
- An explicit abort(404) inside a matched blueprint view does have blueprint ownership.
- A handler's returned string does not inherit the error's HTTP status. Return a proper response or status tuple when status preservation is wanted.

The precedence probe confirmed application-code wins over blueprint-generic, including /bp/missing, while an unmatched /bp/unmatched also selected the application 404 handler.

## Request exception flow and propagation

1. wsgi_app creates/pushes the request Context and runs full_dispatch_request.
2. full_dispatch_request catches Exception from request-start signaling, preprocessing or the view and delegates to handle_user_exception. Final response processing happens after this inner catch.
3. An ordinary, untrapped HTTPException goes to handle_http_exception. A code-less HTTPException or RoutingException is returned unchanged; routing redirects are not treated as user-handler failures. Otherwise the shared lookup selects a handler or the HTTP exception is returned as a response.
4. handle_user_exception otherwise uses the shared lookup and invokes a handler through ensure_sync. No match re-raises the original exception.
5. An unmatched ordinary exception, a failing user error handler, or a normal finalization failure escapes to wsgi_app's outer catch and enters handle_exception.
6. handle_exception first sends got_request_exception for that exception. PROPAGATE_EXCEPTIONS=True re-raises it. When unset, TESTING or DEBUG enables propagation; an explicit False overrides that default.
7. Without propagation, Flask logs the exception, constructs InternalServerError(original_exception=e), searches for a 500 handler using the same blueprint scope list, and finalizes the handler/default response.
8. wsgi_app finally pops the Context, supplying the unhandled error for teardown. Normal handled user exceptions need not be reported as unhandled errors to teardown or got_request_exception.

An explicit abort(500) is already an InternalServerError and goes through normal user handling; it is not automatically wrapped around a different original exception.

TRAP_HTTP_EXCEPTIONS bypasses the special HTTP-response path, not all registered handlers. The next ordinary lookup can still find a matching registered handler. The probe set the trap flag and observed a blueprint generic HTTPException handler return 403. If no handler matches, the trapped exception escapes into propagation/500 policy. TRAP_BAD_REQUEST_ERRORS and debug-sensitive BadRequestKeyError control a related path; BadRequestKeyError may also show its key.

A handler failure is not sent back through the original exception's selection loop repeatedly. The probe made a ValueError handler raise RuntimeError: with propagation off, got_request_exception received RuntimeError, the 500 handler received InternalServerError whose original_exception was RuntimeError, after_request ran, and teardown received RuntimeError. With propagation on, the same RuntimeError escaped and the 500 handler did not run.

## Failure guarantees and limits

- Matched user handlers run before the propagation setting is considered; TESTING/DEBUG does not bypass a matching handler.
- Successful handler results use normal make_response/process_response behavior, including after_request and session handling.
- from_error_handler=True suppresses/logs failures in process_response or request_finished during 500 finalization. It does not cover make_response, which precedes that try.
- A failing 500 handler, response conversion failure there, or failure in got_request_exception can escape. handle_exception is not recursively caught by the same outer catch.
- BaseException subclasses such as KeyboardInterrupt are not converted by the Exception catches; the outer finally still performs Context cleanup.
- Flask does not retry the view/error handler or roll back application side effects. Request cleanup and error dispatch provide no transaction guarantee.
- Streaming iteration and errors after the response iterable is returned are not part of this pre-response dispatch guarantee.

These are source-supported limits, not evidence of a missing generic exception engine.

## Assessment card: retain one dispatch policy module

Strength: Strong retention recommendation; no structural refactor candidate. Dependency category: in-process, with the existing request/testing adapter.

Files: src/flask/sansio/app.py:823–879; src/flask/app.py:744–951,1479–1535.

Problem under review: precedence, trap policy, propagation and cleanup are easy to confuse, but the implementation already gives each a distinct owner.

Solution: preserve the shared selector and request lifetime module; add behavioral coverage at the test-client interface for the surprising compositions. No new interface is proposed.

Before:

    registration -> app registry
    matched request -> HTTP/user handling -> one selector
    unhandled failure -> propagation OR wrapped 500
    response -> finalization -> Context teardown

After:

    same modules, same selector, same ownership
    test-client seam exercises:
      code before scope before MRO
      handler failure -> signal -> propagation/500
      finalization and teardown outcomes

Deletion test: deleting the selector would duplicate code/scope/MRO ordering in HTTP, ordinary and 500 handling. Deleting the separate HTTP or outer-unhandled paths would push routing exceptions, propagation and wrapper decisions into callers. Complexity would move or multiply rather than disappear. Method length or a large app.py is not evidence of shallowness.

- Module depth: selection hides ordered registry lookup.
- Interface leverage: requests share one dispatch policy.
- Locality: precedence stays in one implementation.
- Seam: test client exercises complete request outcomes.
- Adapter: preserve existing request/testing variation.

No extra handler adapter, registry abstraction, extracted policy engine, or whole-app module split has demonstrated value here. The malformed-host test failure described below does not establish that this architecture should change.

## Existing tests and useful behavioral tests

The existing suite already protects much of the contract:

- tests/test_user_error_handler.py:10–58: invalid registrations, no matching user handler, wrapped versus direct 500.
- :61–133: ordinary and HTTP exception MRO specificity.
- :136–214: blueprint/application handling, generic HTTP handling and routing redirect exclusion.
- :217–295: generic HTTPException/Exception handlers and class/code 500 equivalence.
- tests/test_blueprints.py:8–100: blueprint-specific handlers, app fallback and app_errorhandler.
- :793–842: nested child/parent/grandchild handler fallback.
- tests/test_basic.py:867–948: status preservation, after_request on errors, BaseException propagation and routing preprocessing.
- :999–1108: inheritance precedence, trap flags, before/after processor failures.
- :1581–1598: TESTING, DEBUG and explicit propagation.
- tests/test_signals.py:95–113: got_request_exception for an unhandled error.
- tests/test_reqctx.py has Context cleanup tests and an autouse leak detector in conftest.py.

The interface is the test surface. Suggested additions concentrate on combinations not explicit in the reviewed tests:

1. Code versus scope: application 404 versus blueprint HTTPException; assert the application code handler wins. Include an explicit blueprint abort and an unmatched prefixed URL.
2. Scope versus specificity: blueprint parent-exception handler versus application child-exception handler in the same bucket; assert the blueprint handler wins. Add nested child/parent/application fallbacks.
3. Trap with a registered handler: TRAP_HTTP_EXCEPTIONS=True and a matching HTTPException handler should still handle; contrast with no handler and propagation enabled.
4. Error-handler failure: ordinary handler raises a different exception. Assert got_request_exception identity, original_exception identity on wrapped 500, after_request result and teardown exception. Repeat with explicit propagation True and False, including testing/debug defaults.
5. Blueprint unhandled 500: an ordinary exception from a matched blueprint selects its 500 handler; a routing error outside a matched endpoint cannot use that blueprint scope.
6. Finalization failure: distinguish a failing after_request during normal processing from one during 500 safe finalization; assert response, logged failure, callback counts and Context cleanup. Separately show that a failing 500 handler escapes without recursive dispatch.
7. Handler returns bare body versus body/status tuple: assert the actual status rather than only response content.

Preserve the existing high-value tests. The recommendations add leverage at the existing request seam; they do not require another architecture.

## Top recommendation

Add a small precedence-and-failure matrix through the existing test-client interface. Keep the shared selector and request/error ownership. The behavior has depth already; the main opportunity is making its less obvious combinations explicit.

## Skill and harness adaptation

Applied improve-codebase-architecture with codebase-design, HTML-REPORT.md and DEEPENING.md. The harness replaces skill-required sub-agents, opening HTML/windows, filename conventions and interactive grilling: one agent wrote flask.md and flask.html in the authorized reports directory and stops after the audit. CDN references were not fetched. No new interface, source/test edit, glossary/ADR edit, network, installation, live server, git mutation or external write was needed.

## Validation and limitations

Working directory: /private/tmp/codebase-sense-qa-91vasxy9/jobs/reference/cases/flask

First exact command:

~~~sh
env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/private/tmp/codebase-sense-qa-91vasxy9/jobs/reference/cases/flask/src /private/tmp/codebase-sense-qa-91vasxy9/venv/bin/python -m pytest -p no:cacheprovider -q tests/test_user_error_handler.py tests/test_blueprints.py tests/test_basic.py tests/test_signals.py tests/test_reqctx.py
~~~

Exit code: 1. Exact output:

~~~text
........................................................................ [ 32%]
........................................................................ [ 65%]
.....................................................................ss. [ 98%]
.F..                                                                     [100%]
=================================== FAILURES ===================================
_____________________ test_bad_environ_raises_bad_request ______________________

    def test_bad_environ_raises_bad_request():
        app = flask.Flask(__name__)
    
        from flask.testing import EnvironBuilder
    
        builder = EnvironBuilder(app)
        environ = builder.get_environ()
    
        # use a non-printable character in the Host - this is key to this test
        environ["HTTP_HOST"] = "\x8a"
    
        with app.request_context(environ):
            response = app.full_dispatch_request()
>       assert response.status_code == 400
E       assert 404 == 400
E        +  where 404 = <Response streamed [404 NOT FOUND]>.status_code

tests/test_reqctx.py:293: AssertionError
=========================== short test summary info ============================
FAILED tests/test_reqctx.py::test_bad_environ_raises_bad_request - assert 404...
1 failed, 217 passed, 2 skipped in 0.39s
~~~

The failed test concerns malformed Host handling, not handler precedence. Werkzeug in this environment is 3.1.9. The root cause was not established; it is not silently counted as passing or assumed to be a dependency defect. Two greenlet-related tests were skipped. No dependencies or source were changed.

The narrower four-file workflow set was then run to isolate reviewed handler behavior:

~~~sh
env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/private/tmp/codebase-sense-qa-91vasxy9/jobs/reference/cases/flask/src /private/tmp/codebase-sense-qa-91vasxy9/venv/bin/python -m pytest -p no:cacheprovider -q tests/test_user_error_handler.py tests/test_blueprints.py tests/test_basic.py tests/test_signals.py
~~~

Exit code: 0.

~~~text
........................................................................ [ 34%]
........................................................................ [ 69%]
..............................................................           [100%]
206 passed in 0.33s
~~~

This second run does not erase the first failure. The local probes below validate only their stated compositions, not every configuration, async adapter or supported dependency version.

## Reproduction commands and exact results

Exact command (same working directory as above):

~~~sh
env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/private/tmp/codebase-sense-qa-91vasxy9/jobs/reference/cases/flask/src /private/tmp/codebase-sense-qa-91vasxy9/venv/bin/python - <<'PY'
from importlib.metadata import version
from flask import Flask, Blueprint, abort, got_request_exception
from werkzeug.exceptions import HTTPException
import flask
print('module:', flask.__file__)
print('Werkzeug:', version('werkzeug'))
app = Flask('precedence')
app.testing = True
bp = Blueprint('bp', __name__)
@bp.errorhandler(HTTPException)
def bp_http(e):
    return 'blueprint-generic', e.code
@app.errorhandler(404)
def app_404(e):
    return 'application-code', 404
@bp.route('/missing')
def missing():
    abort(404)
@bp.route('/forbidden')
def forbidden():
    abort(403)
app.register_blueprint(bp, url_prefix='/bp')
client = app.test_client()
for path in ['/bp/missing', '/bp/unmatched']:
    response = client.get(path)
    print(path, response.status_code, response.get_data(as_text=True))
app.config['TRAP_HTTP_EXCEPTIONS'] = True
response = client.get('/bp/forbidden')
print('trapped with handler:', response.status_code, response.get_data(as_text=True))
app2 = Flask('handler_failure')
app2.config.update(TESTING=True, PROPAGATE_EXCEPTIONS=False)
app2.logger.disabled = True
events = []
@app2.route('/')
def fail():
    raise ValueError('view failed')
@app2.errorhandler(ValueError)
def broken_handler(e):
    raise RuntimeError('handler failed')
@app2.errorhandler(500)
def error_500(e):
    events.append(('500', type(e).__name__, type(e.original_exception).__name__))
    return 'handled-500', 500
@app2.after_request
def after(response):
    events.append(('after', response.status_code))
    return response
@app2.teardown_request
def teardown(e):
    events.append(('teardown', type(e).__name__))
def on_exception(sender, exception):
    events.append(('signal', type(exception).__name__))
got_request_exception.connect(on_exception, app2, weak=False)
response = app2.test_client().get('/')
print('handler failure:', response.status_code, response.get_data(as_text=True))
print('events:', events)
app2.config['PROPAGATE_EXCEPTIONS'] = True
events.clear()
try:
    app2.test_client().get('/')
except RuntimeError as e:
    print('propagated:', type(e).__name__, str(e))
print('propagation events:', events)
PY
~~~

Exit code: 0.

~~~text
module: /private/tmp/codebase-sense-qa-91vasxy9/jobs/reference/cases/flask/src/flask/__init__.py
Werkzeug: 3.1.9
/bp/missing 404 application-code
/bp/unmatched 404 application-code
trapped with handler: 403 blueprint-generic
handler failure: 500 handled-500
events: [('signal', 'RuntimeError'), ('500', 'InternalServerError', 'RuntimeError'), ('after', 500), ('teardown', 'RuntimeError')]
propagated: RuntimeError handler failed
propagation events: [('signal', 'RuntimeError'), ('teardown', 'RuntimeError')]
~~~


