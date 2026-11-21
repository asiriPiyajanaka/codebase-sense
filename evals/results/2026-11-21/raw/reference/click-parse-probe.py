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

