# Click command invocation audit

Click already separates command definitions, per-invocation context, and the command-line error/exit boundary. Preserve those roles. The scoped suite passed 154 tests with one expected failure. Two small runtime probes exposed concrete cleanup gaps in this checkout: resources registered while parsing are not closed when parsing fails, and a raising close callback can leave the current context on the thread-local stack. Those justify focused lifecycle fixes and regression tests, not a new command execution architecture. No source or tests were changed.

## Invocation path and ownership

The public `Command.main` behavior is implemented by inherited `BaseCommand.main` (`src/click/core.py:1014–1127`). It obtains/copies arguments, determines the program name, and processes shell completion before entering the normal execution/error-handling block. It then constructs a context, enters it, invokes the command once, and either returns the invocation result in embedded mode or requests exit 0 in standalone mode. A callback's return value is deliberately not interpreted as an exit status in standalone mode.

`make_context` (`core.py:910–950`) applies command context settings and constructs the configured context class. Parsing runs under `ctx.scope(cleanup=False)`, making the context current while deferring resource cleanup until invocation. It populates invocation state, rather than running the command callback.

`Command.invoke` (`core.py:1432–1444`) emits any deprecation notice and calls `ctx.invoke(self.callback, **ctx.params)`. A command owns its reusable definition: callback, parameters, parser behavior, and configuration. `Context` owns invocation parameters, parent relationship, inherited object/settings, shared metadata, current-context lifetime, and registered cleanup resources. Current-context access is implemented with a thread-local stack (`src/click/globals.py`), not a single global command object.

`Context.invoke` (`core.py:737–788`) calls a plain callback under the current context. When given another `Command`, it creates a child context, selects that command's callback, fills missing exposed defaults with type conversion, tracks keyword arguments in child `params`, and invokes it. This programmatic path does not rerun command-line parsing or the full `Command.invoke` wrapper. `forward` (`core.py:790–807`) copies current parameters not explicitly supplied, then delegates to `invoke`. The usage-error context manager adds missing parameter/context information without swallowing the error (`core.py:99–113`).

For groups, `MultiCommand.invoke` (`core.py:1663–1729`) owns subcommand resolution and ordering. The group callback runs before its selected command. Non-chain mode keeps parent and child contexts active while running the result callback. Chain mode builds subcommand contexts first, invokes them in sequence, closes each as its block exits, and supplies a list of results to the result callback. Parent resources remain active through result processing. These are different, intentional lifetimes; flattening group and command invocation would risk changing them.

## Errors, exits, and effects

| Outcome from the normal invocation block | Standalone mode | `standalone_mode=False` |
| --- | --- | --- |
| Callback returns a value | Discard it and raise `SystemExit(0)` after cleanup | Return the value after cleanup |
| `ctx.exit(n)` / Click `Exit` | Raise `SystemExit(n)` | Return `n` |
| `ClickException`, including usage errors | Display its formatted error and exit with its `exit_code` | Reraise it |
| `Abort` | Write `Aborted!` to stderr and exit 1 | Reraise it |
| `EOFError` or `KeyboardInterrupt` | Write a newline, convert to `Abort` with the original cause, then abort handling | Still convert to `Abort` with cause and write the newline, then reraise |
| `OSError` with `errno.EPIPE` | Wrap stdout/stderr to suppress flush errors and exit 1 | The same exit behavior; embedded mode does not bypass this branch |
| Other `OSError` or an ordinary application exception | Propagate | Propagate |

`Context.fail`, `abort`, and `exit` raise control/error exceptions (`core.py:685–699`); they do not implement retry or application rollback. Application `SystemExit` is not converted by the shown handlers. Embedded callers should distinguish an ordinary return from a requested exit in their own API if that distinction matters: both can produce the same return value, as the source itself notes.

`CliRunner` catches `SystemExit` and, by default, application exceptions into a result (`src/click/testing.py:400` onward). Thus `result.exit_code == 1` under the runner does not prove `main` itself converted that exception into a process exit. Use direct `main` calls or inspect exception types and causes for embedded-mode tests.

Invocation has no automatic retries, atomicity, or side-effect compensation. A callback or earlier chained command may already have changed application state before a later error. Reinvoking a command repeats its callback unless the application implements idempotency.

## Resource lifetime and concrete gaps

Normal context entry pushes the context and increments nesting depth. At the outermost exit, cleanup runs before the context is popped (`core.py:462–477`). Nested entries defer cleanup. `call_on_close` and `with_resource` register callbacks/managers on an `ExitStack` (`core.py:558–606`), giving reverse registration order; normal `close` resets the stack for context reuse. Cleanup callbacks can still access the current context, which is covered by `test_close_before_pop`.

There are two source-supported failures:

1. **Parse failure loses registered cleanup.** `make_context` deliberately suppresses cleanup during parsing but has no failure path that closes the context. A callback on `--first` registered a close event; a later invalid integer on `--second` produced exit 2, invoked no command, and recorded no close event. This can leak resources acquired by option callbacks. Successful parsing still needs deferred ownership, so changing every parse scope to unconditional cleanup would close resources too early.
2. **Cleanup failure can leak the current context.** `Context.__exit__` calls `self.close()` before `pop_context()` without `finally`. A raising close callback skipped the pop; a direct probe observed `get_current_context(silent=True) is ctx` after the block had failed. `close` also resets its stack only after successful stack closure. Exception handling at `main` does not repair this stack leak.

`Context.__exit__` calls `ExitStack.close()` rather than forwarding the active exception to its `__exit__`. Resource managers therefore receive no original callback exception through this path. Context-managed resources should not be assumed to implement application transaction rollback or exception suppression merely because they are registered with `with_resource`.

Keep the present architecture and address lifecycle safety locally: ensure context popping in `finally` while preserving cleanup-before-pop, close resources when context construction/parsing fails while retaining deferred cleanup on successful parsing, and make reuse behavior after cleanup errors explicit. For chained invocation, also test that already constructed but never invoked child contexts are cleaned if later parsing or an earlier callback fails; eager child-context construction makes this an adjacent ownership risk, not a demonstrated result of the two probes above.

## Existing tests and useful additions

The inspected tests exercise meaningful public behavior: help does not invoke callbacks, parsed values reach callbacks, command returns can be retrieved, invocation/forwarding fill defaults, objects and metadata propagate, nested context cleanup is delayed, resources close, cleanup sees the current context, explicit exits return codes in embedded mode, and interrupt conversion preserves the cause. `tests/test_chain.py` covers chain ordering and result callbacks. Its `test_multicommand_chaining` is explicitly marked xfail; that expected limitation is not evidence requiring a general rewrite.

Add focused behavioral cases:

1. Option callback acquires a resource, then a later parse failure occurs: assert the command was not called, the resource closed once, and the prior current context was restored.
2. A close callback raises: assert other registered cleanup callbacks still run in reverse order, the exception is observable, and the context stack restores its previous value. Repeat under a parent context and through `main`.
3. Parameterize ordinary return, explicit exit, usage error, abort, interrupt, and callback error across standalone and embedded modes. Assert output channel, exit/exception type, cause, return value, and cleanup exactly once. Do not infer `main` behavior solely from runner exit codes.
4. Chain failure after contexts have been parsed, and failure during a later child's parsing: assert no later callback runs and all acquired child and parent resources close in the intended order.
5. Record resource lifetime during parent callback, child callback, and result callback in both regular and chained groups. Assert the user-visible ordering rather than private depth counters.
6. Exercise broken-pipe handling in an isolated process or with safely restored streams, covering the embedded-mode exception to normal propagation.

## Commands and observed results

Commands ran from `/private/tmp/codebase-sense-qa-91vasxy9/jobs/baseline/cases/click`. Inspection used `rg -n` and `sed -n` on the cited sections of `src/click/core.py`, `src/click/globals.py`, `src/click/testing.py`, and relevant test files, plus `cat` on `pyproject.toml` and `tests/conftest.py`. An exploratory lookup of `tests/test_exceptions.py` reported that the file does not exist; the audit used the actual command/context/basic/chain tests instead. No installs, network, terminal windows, or external applications were used.

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/private/tmp/codebase-sense-qa-91vasxy9/jobs/baseline/cases/click/src /private/tmp/codebase-sense-qa-91vasxy9/venv/bin/python -m pytest -p no:cacheprovider tests/test_basic.py tests/test_context.py tests/test_commands.py tests/test_chain.py -q
```

Result: exit 0, `154 passed, 1 xfailed in 0.14s`.

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/private/tmp/codebase-sense-qa-91vasxy9/jobs/baseline/cases/click/src /private/tmp/codebase-sense-qa-91vasxy9/venv/bin/python - <<'PY'
import click
from click.globals import pop_context
from click.testing import CliRunner

events=[]
def resource_option(ctx, param, value):
    ctx.call_on_close(lambda: events.append('closed'))
    return value
@click.command()
@click.option('--first', is_flag=True, callback=resource_option)
@click.option('--second', type=int)
def cli(first, second):
    events.append('invoked')
result=CliRunner().invoke(cli, ['--first', '--second', 'bad'])
print('parse_failure', 'exit_code',result.exit_code,'events',events,'current',click.get_current_context(silent=True))
ctx=click.Context(click.Command('cleanup'))
def fail_close():
    raise RuntimeError('injected close failure')
ctx.call_on_close(fail_close)
try:
    with ctx:
        pass
except RuntimeError as e:
    print('cleanup_failure',str(e),'current_is_closed_context',click.get_current_context(silent=True) is ctx)
finally:
    if click.get_current_context(silent=True) is ctx:
        pop_context()
PY
```

Result: exit 0. The probe manually restored its own process-local stack after observing the leak.

```text
parse_failure exit_code 2 events [] current None
cleanup_failure injected close failure current_is_closed_context True
```
