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

