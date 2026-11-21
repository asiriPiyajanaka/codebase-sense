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

