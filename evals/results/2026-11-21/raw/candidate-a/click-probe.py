#!/usr/bin/env python3
"""Exercise the local Click callback/cleanup boundary without external I/O."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "cases" / "click" / "src"))
import click
from click.globals import pop_context
from click.testing import CliRunner

events = []
contexts = []


@click.command()
@click.pass_context
def cli(ctx):
    contexts.append(ctx)

    @ctx.call_on_close
    def cleanup():
        events.append("cleanup")
        raise RuntimeError("cleanup failed")

    events.append("callback")
    return "callback result"


assert click.get_current_context(silent=True) is None
result = CliRunner().invoke(cli, standalone_mode=False)
leaked = click.get_current_context(silent=True) is contexts[0]
try:
    assert isinstance(result.exception, RuntimeError)
    assert str(result.exception) == "cleanup failed"
    assert events == ["callback", "cleanup"]
    assert leaked
    print(json.dumps({
        "events": events,
        "exception": type(result.exception).__name__,
        "message": str(result.exception),
        "exit_code": result.exit_code,
        "return_value": result.return_value,
        "current_context_leaked": leaked,
    }, sort_keys=True))
finally:
    # Clean only this probe process's thread-local stack after observing it.
    if leaked:
        pop_context()
assert click.get_current_context(silent=True) is None
