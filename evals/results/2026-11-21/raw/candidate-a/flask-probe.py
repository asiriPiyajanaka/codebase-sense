#!/usr/bin/env python3
"""Local Flask test-client probes; no sockets, services, or persistent state."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "cases" / "flask" / "src"))
from flask import Blueprint, Flask, abort, request
from werkzeug.exceptions import HTTPException, InternalServerError


def show(label, response):
    print(label, json.dumps({"status": response.status_code, "body": response.get_data(as_text=True)}, sort_keys=True))


app = Flask(__name__)
bp = Blueprint("bp", __name__)


@bp.route("/forbidden")
def forbidden():
    abort(403)


@bp.errorhandler(HTTPException)
def bp_http(error):
    return "blueprint-generic", error.code


@app.errorhandler(403)
def app_forbidden(error):
    assert request.blueprints == ["bp"]
    return "application-code", 403


@app.errorhandler(404)
def app_missing(error):
    assert request.blueprints == []
    return "application-routing-404", 404


app.register_blueprint(bp, url_prefix="/bp")
with app.test_client() as client:
    response = client.get("/bp/forbidden")
    assert response.data == b"application-code"
    show("app_code_before_blueprint_generic", response)
    response = client.get("/bp/missing")
    assert response.data == b"application-routing-404"
    show("unmatched_blueprint_prefix", response)

app = Flask(__name__)
bp = Blueprint("bp", __name__)


@bp.route("/key")
def key():
    raise KeyError("failure")


@bp.errorhandler(Exception)
def bp_exception(error):
    return "blueprint-generic-exception"


@app.errorhandler(KeyError)
def app_key(error):
    return "application-specific-exception"


app.config["PROPAGATE_EXCEPTIONS"] = True
app.register_blueprint(bp)
with app.test_client() as client:
    response = client.get("/key")
    assert response.data == b"blueprint-generic-exception"
    show("blueprint_scope_before_application_mro_even_when_propagating", response)

app = Flask(__name__)
app.config["TRAP_HTTP_EXCEPTIONS"] = True


@app.route("/trapped")
def trapped():
    abort(404)


@app.errorhandler(404)
def trapped_handler(error):
    return "registered-handler-still-applies", 404


with app.test_client() as client:
    response = client.get("/trapped")
    assert response.data == b"registered-handler-still-applies"
    show("trapped_http_with_registered_handler", response)

app = Flask(__name__)
app.logger.disabled = True
app.config["PROPAGATE_EXCEPTIONS"] = False


@app.route("/unhandled")
def unhandled():
    raise LookupError("original")


@app.route("/broken-handler")
def broken_handler_view():
    raise ValueError("first")


@app.errorhandler(ValueError)
def broken_handler(error):
    raise RuntimeError("handler failed")


@app.errorhandler(500)
def fallback(error):
    assert isinstance(error, InternalServerError)
    return "wrapped:" + type(error.original_exception).__name__, 500


with app.test_client() as client:
    response = client.get("/unhandled")
    assert response.data == b"wrapped:LookupError"
    show("unhandled_wrapped_for_500_handler", response)
    response = client.get("/broken-handler")
    assert response.data == b"wrapped:RuntimeError"
    show("handler_failure_wrapped_for_500_handler", response)

app.config["PROPAGATE_EXCEPTIONS"] = True
with app.test_client() as client:
    try:
        client.get("/unhandled")
    except LookupError as error:
        print("unhandled_propagation", json.dumps({"exception": type(error).__name__, "message": str(error)}, sort_keys=True))
    else:
        raise AssertionError("unhandled exception should propagate")
