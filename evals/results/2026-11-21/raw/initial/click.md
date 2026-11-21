# Click command invocation audit

Scope: `Command.main`, `Context`, and callback invocation in this repository copy. Mode: read-only audit using Codebase Sense v0.1.0. No source or tests changed. No AGENTS.md or relevant ADR was found. This copy lacks Git metadata (`git status --short` exited 128); history and pre-existing dirty state are unknown.

**Keep the invocation architecture.** Terminal policy, callback invocation, and context lifetime are meaningful boundaries with real library callers. A local probe did expose a narrow cleanup defect: when a close callback raises, the current context remains on the thread-local stack. Address that with a regression and a bounded lifecycle fix, not a new invocation subsystem.

## Sense Card

- **Promise:** command instances act as CLI entry points; standalone mode converts Click usage/abort signals to terminal output and exits, while embedded callers can obtain callback results and exceptions. Contexts carry invocation state and manage registered resources.
- **Flow:** command `__call__` → inherited `BaseCommand.main` → `make_context` / parse → `Command.invoke` → `Context.invoke` → user callback → context teardown → return or terminal exit policy (`src/click/core.py:1159,1014,910,1432,737`). `Command.main` is inherited in this revision; there is no separate implementation on `Command`.
- **Owner:** `main` owns process-facing error and exit policy; `Command.invoke` owns invoking its configured callback; `Context` owns current-context state, callback defaults/forwarding, and resource lifetime. Group dispatch adds a justified command-selection layer rather than pushing that knowledge onto applications (`src/click/core.py:1663`).
- **Change entry point:** exit/error behavior starts at `BaseCommand.main:1079`; callback/default behavior at `Context.invoke:737`; cleanup at `Context.__exit__:467` and `close:599`.
- **Verified:** 163 existing tests passed across basic commands, command composition, context, and runner behavior. A direct probe checked return, explicit exit, usage error, abort, EOF, and arbitrary application error in both modes, with ordinary cleanup occurring and no active context afterward.
- **Missing, reproduced:** cleanup-exception safety. Raising in `call_on_close` propagates the cleanup error but skips `pop_context`, leaving a stale current context (`src/click/core.py:473–476`).
- **Unknown:** Windows argument expansion, real shell completion, real broken pipes, asynchronous execution, cross-thread sharing, and parse-callback resource failure cases were not executed. This audit does not cover all parser or group behaviors.
- **Decision:** **Keep** architectural seams; **Change** the bounded exception-safety defect after adding a regression.
- **Next action:** capture the cleanup exception reproduction as a behavioral test before changing `Context.__exit__`; no broad architectural refactor is recommended.

## Real invocation and ownership

`make_context` merges context settings, constructs the configurable context class, and parses inside `scope(cleanup=False)` (`src/click/core.py:937–950`). It deliberately does not invoke the command. `main` enters that context before invoking, so normal callback returns and exceptions unwind it before terminal policy runs (`:1081–1100`). A standalone successful callback return is discarded and exits 0; returning an integer does not itself select an exit code (`:1083–1092`).

`Command.invoke` prints a deprecation warning when configured, then delegates to `ctx.invoke(self.callback, **ctx.params)` (`:1432–1443`). `Context.invoke` distinguishes a bare callable from another `Command`: a command gets a same-type child context and missing exposed defaults are resolved and type-cast; keyword arguments are tracked for subsequent forwarding (`:762–788`). It calls that command's callback rather than recursively entering `main`, so it does not reparse a CLI or apply process exit policy. The public docs explain manual `make_context` / `invoke` and command composition (`docs/exceptions.rst`, `docs/advanced.rst:158`, `docs/commands.rst:116`).

Real callers include `CliRunner.invoke`, which invokes `cli.main` and separately captures exceptions for testing (`src/click/testing.py:412–435`), the manual embedded caller in `tests/test_basic.py:46`, and composed commands in `tests/test_commands.py:8,24,235`. A runner `exit_code == 1` can therefore mean an exception captured by the harness; it is not proof that `main` called `sys.exit(1)`.

Context nesting increments depth and pushes the context; ordinary outermost exit closes the ExitStack before popping (`src/click/core.py:462–476`). This lets close callbacks still access the current context and defers cleanup during nested invocation. `with_resource` and `call_on_close` register with ExitStack (`:558–604`); its LIFO semantics are inherited from the standard library. The existing successful cleanup-order tests make the close-before-pop behavior intentional.

## Observable errors and exits

| Callback outcome | Standalone `main` | `standalone_mode=False` |
| --- | --- | --- |
| Return `42` | `SystemExit(0)` | returns `42` |
| `ctx.exit(7)` | `SystemExit(7)` | returns `7` |
| `ctx.fail('bad input')` / `UsageError` | usage and error on stderr, exit 2 | raises `UsageError` without rendering |
| `ctx.abort()` | `Aborted!` on stderr, exit 1 | raises `Abort` |
| `EOFError` | newline, `Aborted!`, exit 1 | newline and raises `Abort`, preserving EOF as cause |
| Application `ValueError` | propagates | propagates |

All six rows were executed directly in both modes; registered ordinary cleanup ran once each and `get_current_context(silent=True)` was `None` afterward. `KeyboardInterrupt` shares the EOF conversion branch, and the existing parameterized test checks both causes (`tests/test_commands.py:534–543`). Other `ClickException` subclasses render their own `exit_code`, which is not universally 2 (`src/click/core.py:1096–1100`).

Two compatibility details matter. Embedded mode still converts EOF/interrupt to `Abort`, and explicit `Exit` returns its code rather than being re-raised (`:1093–1095,1108–1123`). Also, the EPIPE branch wraps stdout/stderr and calls `sys.exit(1)` even in embedded mode; other `OSError`s propagate (`:1101–1107`). This latter behavior was inspected, not executed. Shell completion runs before the shown error-handling block and can exit early (`:1076–1079,1157`). Do not simplify the contract to “embedded mode never exits” or “all exceptions are caught.”

There is no framework promise of rollback or idempotency for user callbacks. Retrying a command can repeat arbitrary application effects; callers own that policy.

## Assessment and smallest justified change

**Candidate 1: collapse `main`, `Command.invoke`, and `Context.invoke` — Keep.** The apparent forwarding layers expose different stable capabilities. Embedding and command composition use invocation without terminal policy, and configurable command/context subclasses are extension points. Combining them would broaden what callers must understand and risk defaults, return values, and extension compatibility. The existing public contracts are already narrow enough; no repeated caller-side orchestration defect justifies a redesign.

**Candidate 2: make context teardown exception-safe — Change, narrowly.** `Context.__exit__` calls `self.close()` before `pop_context()` without `finally` (`src/click/core.py:473–476`). A command registering a cleanup callback that raises `RuntimeError('cleanup failure')` and then returning caused `main(..., standalone_mode=False)` to propagate that error while `get_current_context(silent=True)` remained non-None. The probe explicitly popped the stale context only to restore its own process-local state afterward.

The guarantee at risk is current-context lifetime after failed cleanup, already established for normal completion by `test_global_context_object` and for callback ordering by `test_close_before_pop`. Preserve close-before-pop so callbacks still see their context. The smallest public contract remains unchanged: leaving a scope removes that scope even if cleanup fails, while cleanup errors retain a deliberate propagation policy. A regression followed by exception-safe popping is a local correctness fix; moving policy into `main` would leave direct Context users exposed. Test nested child/parent contexts and multiple cleanup callbacks before changing exception precedence or ExitStack reuse. No implementation was performed.

## Existing and useful additional tests

The existing tests check meaningful observable results rather than merely mocked calls: manual callback returns (`tests/test_basic.py:46`), invoke/forward output and typed defaults (`tests/test_commands.py:8,24,235`), cleanup once after nested entry (`tests/test_context.py:103`), no current context after ordinary invocation (`:123`), callbacks seeing the context during close (`:219`), resource cleanup (`:240`), and explicit embedded exit codes (`:308`). `tests/test_testing.py:391` checks callback return values in the runner. These are valuable integration seams.

Add tests for cleanup callbacks raising during success, usage failure, explicit exit, and arbitrary callback failure. Assert which exception propagates, every required cleanup runs, and the previous parent context or `None` is restored. Add a combined direct-`main` matrix asserting stderr, return values, exit codes, and cleanup in both modes; current scattered tests do not fully protect those combinations. Characterize resources registered during parsing when a later parsing callback fails, because `make_context` suppresses cleanup until it returns. Test EPIPE separately with controlled/restored streams, and distinguish its embedded behavior from ordinary `OSError` propagation. These are recommendations, not tests claimed to exist or pass.

## Commands and results

`cat`, `rg`, and line-numbered source reads inspected only the scoped implementation, docs, tests, and configuration. An exploratory search included nonexistent `tests/test_exceptions.py`; `rg` returned exit 2 for that path, and the subsequent search used actual `tests/test_*.py`. No missing test file was treated as executed.

From this case root:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/private/tmp/codebase-sense-qa-91vasxy9/jobs/initial/cases/click/src /private/tmp/codebase-sense-qa-91vasxy9/venv/bin/python -m pytest -p no:cacheprovider -q tests/test_basic.py tests/test_commands.py tests/test_context.py tests/test_testing.py
```

Result: **163 passed in 0.14s**, exit 0. A separate heredoc using the same interpreter/environment printed `click.__file__` under this copy's `src`, ran the 12 direct `main` cases summarized in the table with captured stderr, and reproduced the close-callback context leak. Probe exit 0; this is successful execution of an observation script, not a passing regression for the leak. No network, installs, live services, windows, source edits, or test edits were used.
