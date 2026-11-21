# Click command invocation audit

Recommendation: retain Command, Context, and invocation ownership, and repair two demonstrated failure paths inside the existing Context lifecycle module. A broad invocation redesign is not justified.

## Scope and evidence

Audited Command.main (implemented on BaseCommand), context creation/cleanup, Command.invoke, Context.invoke/forward, error classes, the relevant group invocation extension, CliRunner, and targeted tests. The named workflow set the scope; no commit-history inference was needed. No GLOSSARY.md or docs/adr decisions were present in this copy.

Important source references in src/click/core.py:

| Reference | Ownership |
| --- | --- |
| BaseCommand.main:1014–1126 | argument normalization, context lifetime, standalone error/exit policy |
| make_context:910–950 | context settings, context_class, parsing inside scope(cleanup=False) |
| Command.parse_args:1408–1430 | parameter processing, extra argument rejection, remaining args |
| Command.invoke:1432–1444 | deprecation warning and dispatch of callback using ctx.params |
| Context.invoke:737–788 | child context/defaults when given a Command; callback context activation |
| Context.forward:790–810 | copies missing current params, then invokes another Command |
| Context.__enter__/__exit__/scope:462–514 | active-context stack, nesting depth, cleanup scheduling |
| Context.with_resource/call_on_close/close:558–606 | ExitStack-owned resource lifetime |
| Context.fail/abort/exit:685–700 | raises UsageError, Abort, or Exit |
| MultiCommand.invoke:1663–1732 | parent/child lifetime, group callback and result processing |

Other evidence: src/click/exceptions.py:25–90,282–300; src/click/globals.py:20–48; src/click/testing.py:353–442. Source and tests were not edited.

## Observable invocation and ownership

1. main copies explicit args or takes sys.argv; optional Windows expansion applies only to inherited process args. It determines the program name and processes shell completion before the normal exception-handling block.
2. make_context combines context_settings with explicit overrides, constructs context_class, and parses while the Context is current. cleanup=False keeps resources registered during successful parsing alive for invocation.
3. main enters the returned Context and calls self.invoke. Command.invoke delegates the callback and parsed ctx.params to Context.invoke.
4. For a plain callable, Context.invoke activates the same Context. For another Command, it creates a child of the current Context's type, fills missing exposed parameter defaults with type conversion, records kwargs in child.params, and invokes its callback. This programmatic path does not reparse argv or perform the entire Command.main error/exit policy.
5. forward carries current params into kwargs only where absent, then reuses Context.invoke. Existing kwargs win.
6. Nested Context entry increments depth. Cleanup is deferred until the last exit. Registered cleanup is LIFO through ExitStack and runs while the Context is still current.
7. In the normal path, non-standalone main returns the callback result; standalone main explicitly exits with code zero, even if a callback returns a nonzero integer.
8. Groups extend the same lifetime model. Parent Context stays active through result processing, child callbacks have child Contexts, and chain invocation gathers results. These extension points are reason to preserve ownership rather than flatten the workflow.

Context owns parsed state, parent metadata and resource cleanup. Command owns command-specific parsing and dispatch. main owns process-style presentation and exit policy. CliRunner is a testing adapter: it captures SystemExit and, by default, other exceptions; a Result.exit_code does not prove main itself converted an ordinary error.

## Error, exit, and retry behavior

| Outcome | standalone_mode=True | standalone_mode=False |
| --- | --- | --- |
| Callback returns value | SystemExit(0); result is not an exit status | Return value |
| ctx.exit(n) / Exit(n) | SystemExit(n) | Return n |
| ClickException | Display error, SystemExit(e.exit_code) | Re-raise |
| UsageError / ctx.fail | Usage diagnostic, normally SystemExit(2) | Re-raise UsageError |
| Abort / ctx.abort | “Aborted!” on stderr, SystemExit(1) | Re-raise Abort |
| EOFError / KeyboardInterrupt | Newline, translate to Abort, then exit 1 | Newline, raise Abort chained from original |
| OSError with errno.EPIPE | Pacify stdout/stderr flush, SystemExit(1) | Same SystemExit(1) special case |
| Other OSError or ordinary callback error | Propagate | Propagate |

The successful return value and an explicit exit code can be ambiguous in non-standalone mode, as the implementation itself documents. augment_usage_errors at core.py:98–114 attaches a missing Context/parameter to usage errors and re-raises; it does not own terminal policy.

Exit is control flow, not a rollback mechanism. No invocation is automatically retried and no callback effects are undone by Click. A second invocation is a new execution. Shell completion runs before normal handling, so its early-exit behavior should not be inferred from the main invocation table.

## Demonstrated lifecycle failures

### Cleanup failure leaves the Context current

At core.py:473–476, close() precedes pop_context() without unconditional finalization. If a registered close callback raises, pop_context is skipped. A direct non-standalone main probe with one cleanup raising RuntimeError observed that RuntimeError and then get_current_context(silent=True) still returned a Context. The cleanup ran once.

This is externally observable lifecycle state, not a demand to split a large source file. It can affect later embedded invocations in the same thread.

### Parse failure abandons registered cleanup

make_context parses under scope(cleanup=False). If a parameter callback registers cleanup and a later required argument is missing, make_context never returns a Context to main's with statement. The no-cleanup scope pops the current Context but does not run the registered cleanup.

A direct probe registered “closed” after recording “opened”, then omitted a required argument. It raised MissingParameter, recorded only ["opened"], and left no current Context. Thus this failure differs from the cleanup-error stack leak: registered resource cleanup is abandoned, while stack state is restored.

## Candidate: complete ownership of Context failure cleanup

Strength: Strong for the reproduced fixes. Dependency category: in-process.

Files: src/click/core.py:462–514,558–606,910–950; related tests/test_context.py and tests/test_commands.py.

Problem: callers trust Context lifetime, but a raising cleanup skips stack restoration and a failing parse can bypass cleanup ownership entirely.

Solution: keep lifetime policy in the existing Context module, restore the active-context stack unconditionally after cleanup, and ensure a Context created for failed parsing releases its registered resources before becoming unreachable. Preserve successful parse deferral, nested cleanup timing, custom Context types, and error chaining. This states the desired behavior; no replacement interface is proposed.

Before:

    main -> make_context [no-cleanup parse scope]
             parse fails -> resources not released
          -> invoke callback
          -> close raises -> pop_context skipped

After:

    same main / Context interface
      Context module owns every lifetime outcome
        successful parse -> defer until invocation ends
        failed parse -> release owned resources
        close success or failure -> restore parent/current Context

Deletion test: deleting Context.invoke or make_context would move default filling, custom-context behavior, parsing scope and lifetime decisions into callers. Deleting Context would scatter these decisions even further. These modules already provide depth; flattening them loses leverage. The defect is incomplete failure ownership within their implementation, not the existence of their seams.

- Locality: Context owns lifecycle failure policy.
- Leverage: CLI and embedded callers benefit.
- Depth: existing interface guarantees complete lifetime.
- Seam: Context activation stays in one place.
- Adapter: custom Context tests preserve variation.

The existing context_class and child-context-type seam has concrete custom implementations in tests/test_custom_classes.py:4–44. No new adapter hierarchy or generic invocation engine is justified. Error rendering and callback dispatch have distinct responsibilities; do not merge them merely because they are nearby.

## Existing tests and useful behavioral tests

Existing evidence is substantial:

- tests/test_context.py:103–134 verifies nested entry, cleanup once, and normal global Context restoration.
- :177–201 verifies cleanup=False deferral; this one inspects private depth as well as callback behavior.
- :219–253 verifies cleanup before Context pop and with_resource release.
- :307–320 covers explicit exit values in non-standalone mode.
- tests/test_commands.py:8–64 covers invoke, forward, and forwarded params; :235–253 covers missing defaults; :534–544 covers EOF/interrupt chaining. The one expected failure in the selected run is test_multicommand_chaining at tests/test_chain.py:221–222.
- tests/test_custom_classes.py:4–44 exercises context_class and child Context type.
- tests/test_chain.py covers group chains/result callbacks.
- tests/test_testing.py:163–185 and391–401 distinguish runner exception capture from non-standalone return values.

The interface is the test surface. Prioritize:

1. Failing close callback: invoke main inside a parent Context; cleanup must observe the child as current, raise its original error, run remaining LIFO callbacks once, and restore the parent afterward. After the parent exits, no Context should remain.
2. Failed parse after resource registration: an option callback registers cleanup, then another required input fails; the callback must not run, cleanup must run once, and the current Context must return to its prior value.
3. Preserve successful parsing lifetime: a resource acquired by a parameter callback remains usable during command invocation and is released once afterward.
4. Standalone versus embedded matrix: return 7, ctx.exit(7), UsageError, ClickException, Abort, EOFError, KeyboardInterrupt, and ordinary RuntimeError. Assert returned values or exact exception types/codes, diagnostics, cause, cleanup events and parent restoration.
5. EPIPE: isolate the stdout/stderr replacement in a local subprocess or restore captured streams explicitly; assert SystemExit(1) even in non-standalone mode. No process-level probe was run for this branch.
6. Custom Context plus invoke/forward: preserve the existing custom type, defaults, explicit kwargs, parent relationship and result, while asserting child cleanup precedes parent cleanup.
7. Group result processing: maintain parent resource availability through the result callback and check failed child invocation still releases contexts.

Add the lifecycle cases to existing behavioral coverage. Rewriting all tests around private Context state would reduce leverage and make implementation changes expensive.

## Top recommendation

Fix and test Context failure cleanup inside its current module. Keep the mature Command/Context/invocation structure; the measured defects do not warrant a new runtime architecture.

## Skill and harness adaptation

Applied improve-codebase-architecture, codebase-design, HTML-REPORT.md and DEEPENING.md. The harness supersedes fresh sub-agent exploration, browser/window opening, report filename conventions and grilling. One agent produced click.md and click.html in the authorized reports directory without fetching CDN scripts. No source/test edit, proposed new interface, glossary/ADR edit, network, installation, live process, git mutation or external write was needed.

## Validation

Working directory: /private/tmp/codebase-sense-qa-91vasxy9/jobs/reference/cases/click

Exact command:

~~~sh
env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/private/tmp/codebase-sense-qa-91vasxy9/jobs/reference/cases/click/src /private/tmp/codebase-sense-qa-91vasxy9/venv/bin/python -m pytest -p no:cacheprovider -q tests/test_context.py tests/test_commands.py tests/test_basic.py tests/test_custom_classes.py tests/test_chain.py
~~~

Exit code: 0.

~~~text
........................................................................ [ 44%]
........................................................................ [ 89%]
................x                                                        [100%]
160 passed, 1 xfailed in 0.16s
~~~

Additional exact command:

~~~sh
env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/private/tmp/codebase-sense-qa-91vasxy9/jobs/reference/cases/click/src /private/tmp/codebase-sense-qa-91vasxy9/venv/bin/python -m pytest -p no:cacheprovider -q tests/test_testing.py -k 'catch_exceptions or command_standalone_mode_returns_value or exit_code_and_output_from_sys_exit'
~~~

Exit code: 0.

~~~text
...                                                                      [100%]
3 passed, 21 deselected in 0.02s
~~~

The lifecycle defects above were reproduced separately despite the existing selected tests passing.

## Reproduction commands and exact results

Exact command (same working directory as above):

~~~sh
env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/private/tmp/codebase-sense-qa-91vasxy9/jobs/reference/cases/click/src /private/tmp/codebase-sense-qa-91vasxy9/venv/bin/python - <<'PY'
import click
print('module:', click.__file__)
events = []
@click.command()
@click.pass_context
def cli(ctx):
    @ctx.call_on_close
    def cleanup():
        events.append('cleanup')
        raise RuntimeError('cleanup failed')
    return 7
try:
    cli.main([], prog_name='audit', standalone_mode=False)
except RuntimeError as e:
    print('cleanup error:', str(e))
print('cleanup events:', events)
print('context leaked:', click.get_current_context(silent=True) is not None)
PY
~~~

Exit code: 0.

~~~text
module: /private/tmp/codebase-sense-qa-91vasxy9/jobs/reference/cases/click/src/click/__init__.py
cleanup error: cleanup failed
cleanup events: ['cleanup']
context leaked: True
~~~

Exact command (same working directory as above):

~~~sh
env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/private/tmp/codebase-sense-qa-91vasxy9/jobs/reference/cases/click/src /private/tmp/codebase-sense-qa-91vasxy9/venv/bin/python - <<'PY'
import click
events = []
def register(ctx, param, value):
    if value:
        events.append('opened')
        ctx.call_on_close(lambda: events.append('closed'))
    return value
@click.command()
@click.option('--start', is_flag=True, callback=register)
@click.argument('name')
def cli(start, name):
    pass
try:
    cli.main(['--start'], prog_name='audit', standalone_mode=False)
except click.MissingParameter as e:
    print('parse error:', type(e).__name__)
print('resource events:', events)
print('context leaked:', click.get_current_context(silent=True) is not None)
PY
~~~

Exit code: 0.

~~~text
parse error: MissingParameter
resource events: ['opened']
context leaked: False
~~~


