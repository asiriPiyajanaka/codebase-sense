Scope: one command invocation through public `Command.main`, `Context`, and callback invocation, with representative group and test-runner callers. Mode: **audit**. I inspected the relevant source, exception documentation, pytest configuration, contributing test instructions, and context/invocation tests. No source or tests were changed. No `AGENTS.md`, ADR, or git metadata was present in this copy; this is not a full Click audit.

**Keep the invocation architecture; change one local cleanup failure path.** The public entry points hide useful differences between CLI execution, programmatic invocation, and context lifetime. The inspected tests validate real callbacks and output, and 141 selected cases passed. A separate probe reproduced a context-stack leak when a registered close callback raises. That warrants a regression test and a narrow fix in `Context.__exit__`, not a new invocation service.

**Sense Card — command invocation**

- **Promise:** parse command arguments and invoke the callback with the correct active context and parameters; apply CLI error/exit policy in standalone mode, or return callback results in embedded mode.
- **Flow:** `BaseCommand.__call__` → inherited `Command.main` (`src/click/core.py:1159,1014`) → `make_context` and parsing (`:910,1408`) → `Command.invoke` (`:1432`) → `Context.invoke` (`:737`) → application callback. Context entry/exit surrounds execution and owns cleanup (`:462–476`). `MultiCommand.invoke` supplies nested command contexts and result-callback lifetime (`:1663–1729`).
- **Current owners:** `main`: argv/program name, completion handoff, error presentation, process exit policy. `Command`: parsing and callback selection. `Context`: per-invocation state, parent/default inheritance, callback invocation, resource cleanup. `exceptions.py`: typed error/status and rendering. `globals.py`: thread-local current-context stack. `CliRunner.invoke` is a test harness that calls `main` and captures outcomes; it does not define CLI behavior.
- **Change entry point:** `main` for an exit-code or exception-conversion bug; `Context.invoke` for forwarded defaults/parameters; `Context.__exit__` for resource lifetime or stack restoration.
- **Verified:** selected help, parsing, callback return, invocation/forwarding/default, context inheritance/lifetime, explicit embedded exit, and interrupt-conversion tests passed. The additional probe verified that a raising cleanup callback leaves a stale current context after invocation.
- **Unknown:** Windows expansion, real subprocess/terminal and broken-pipe behavior, shell completion, concurrent invocation, and every parse-failure resource path were not exercised. Passing in-process tests do not certify these boundaries.
- **Decision / next action:** **Keep** the public ownership split; **Change** the demonstrated cleanup path locally. Add an exceptional-cleanup regression in `tests/test_context.py`, then ensure stack restoration while preserving cleanup-before-pop semantics.

`Command.main` is inherited from `BaseCommand` in this snapshot. It copies supplied args or reads `sys.argv`, detects the program name, and checks completion before its main exception-handling block (`core.py:1065–1081`). It then constructs the context, invokes the command inside it, and returns the callback result only when `standalone_mode=False`. Standalone success exits zero rather than interpreting a callback's return value as an exit status; the source explains why integer-looking values and chained command lists are not status codes (`:1082–1092`).

`make_context` merges command context settings, constructs the overridable `context_class`, and parses inside `scope(cleanup=False)` (`:937–950`), keeping resources for the invocation phase. `Command.invoke` delegates the callback and parsed `ctx.params` to the context (`:1442–1443`). `Context.invoke` also accepts another `Command`: it creates a child context, fills and type-casts omitted exposed defaults, tracks kwargs for subsequent forwarding, then invokes the callback with a context active (`:762–788`). That programmatic route does not reparse command-line tokens. `Context.forward` copies the current parameters and reuses that contract (`:790–807`). The `pass_context` decorator retrieves the active context rather than adding another invocation coordinator (`src/click/decorators.py:27–35`).

The error and exit policy is explicit in `core.py:1093–1125`:

| Outcome | Standalone | `standalone_mode=False` |
| --- | --- | --- |
| Callback returns a value | `SystemExit(0)` | Return that value. |
| `ClickException` | Render with `show`, then exit its status; `UsageError` uses 2 (`exceptions.py:55–64`). | Reraise the exception. |
| `ctx.exit(code)` / Click `Exit` | `SystemExit(code)` | Return the code. This can be ambiguous with a callback returning that integer, as the source documents. |
| `Abort` | Print `Aborted!` to stderr and exit 1. | Reraise `Abort`. |
| `EOFError` / `KeyboardInterrupt` | Emit a newline, convert to `Abort` with the original cause, then apply abort policy. | The same conversion occurs; callers receive `Abort`, not the original interrupt. |
| `OSError(EPIPE)` | Wrap streams to pacify flush, then `SystemExit(1)`. | The same special exit still occurs. Other `OSError`s propagate. |
| Other application exceptions | Propagate. | Propagate. |

Thus “embedded mode disables all exception handling” is too broad. Direct `command.invoke(ctx)` bypasses `main`'s conversion/presentation policy, as documented in `docs/exceptions.rst`. A caller still owns entering and closing that context. No atomicity, rollback, or retry guarantee exists for arbitrary application callback effects; Click handles invocation lifetime and reporting, while the application owns those effects.

The current split is justified by callers. `tests/test_basic.py:test_return_values:46` invokes a command with an explicitly managed context. `tests/test_commands.py:test_other_command_invoke_with_defaults:235` verifies type-cast defaults and the child command name. `test_forwarded_params_consistency:44` covers kwargs forwarding. Context tests verify that nested entry does not close early (`tests/test_context.py:103`), cleanup can inspect the current context before it is popped (`:219`), and `with_resource` closes a real context manager (`:240`). Group invocation intentionally keeps its parent context active while the subcommand and result processor run (`core.py:1688–1697`). Combining these APIs would obscure distinct contracts and risk custom contexts or command subclasses without an observed benefit.

The concrete defect is in `Context.__exit__` (`core.py:473–476`): it decrements depth, calls `close()`, and only then calls `pop_context()`, with no `finally`. `close()` invokes user cleanup callbacks via `ExitStack` (`:587–606`). A callback that raises `RuntimeError("cleanup failed")` skips the pop. The probe calls a real decorated command through `CliRunner` with embedded mode, gets the cleanup exception, and observes `get_current_context(silent=True)` still returning the finished context. In a long-lived caller, later helpers can read stale context and retain references after the command has ended. The probe removes only its own leaked thread-local entry after recording the observation.

The counterargument is that standalone processes usually exit immediately after invocation. However, embedded mode and `CliRunner` are actual supported callers, so lifecycle restoration matters independently of process exit. Preserve the useful ordering tested by `test_close_before_pop`; put stack restoration in an unconditional cleanup path rather than moving the pop before registered callbacks. Keep the cleanup exception visible. Before implementation, decide and test exception precedence when both callback execution and cleanup raise.

The existing tests are behavioral rather than mock-only, but all `call_on_close`/`with_resource` occurrences in the inspected test tree cover nonraising cleanup. Add a test for the reproduced case that asserts both the escaping error and restoration of the prior current context, then a nested-context variant. A compact parameterized test around normal return, `UsageError`, `Exit`, `Abort`, and ordinary callback failure should assert cleanup runs once and current context is restored. A separate focused test should characterize the intentional EPIPE exception to embedded mode without changing actual process streams outside the fixture. Parse-time resource cleanup deserves investigation before any lifetime refactor; it was not demonstrated here as a defect.

Checks ran from `/private/tmp/codebase-sense-qa-91vasxy9/jobs/candidate-a/cases/click`. The pytest configuration sets warnings to errors; selected fixtures use `CliRunner`, and filesystem tests use disposable isolated directories. No subprocess or live service was started.

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/private/tmp/codebase-sense-qa-91vasxy9/jobs/candidate-a/cases/click/src /private/tmp/codebase-sense-qa-91vasxy9/venv/bin/python -m pytest -p no:cacheprovider -q tests/test_context.py tests/test_commands.py tests/test_basic.py tests/test_testing.py::test_catch_exceptions tests/test_testing.py::test_command_standalone_mode_returns_value
```

Exit **0**, exact output:

```text
........................................................................ [ 51%]
.....................................................................    [100%]
141 passed in 0.13s
```

`CliRunner` catches ordinary exceptions by default and captures `SystemExit` separately (`src/click/testing.py:411–435`). Its successful capture must not be confused with `main` suppressing an application exception. The selected `test_catch_exceptions` also checks `catch_exceptions=False`.

The saved [click-probe.py](click-probe.py) reproduces the cleanup defect using only in-process callbacks:

```sh
PYTHONDONTWRITEBYTECODE=1 /private/tmp/codebase-sense-qa-91vasxy9/venv/bin/python /private/tmp/codebase-sense-qa-91vasxy9/jobs/candidate-a/reports/click-probe.py
```

Exit **0**, exact output (zero means the defect reproduced):

```text
{"current_context_leaked": true, "events": ["callback", "cleanup"], "exception": "RuntimeError", "exit_code": 1, "message": "cleanup failed", "return_value": null}
```
