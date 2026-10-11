from flask import jsonify
from werkzeug.exceptions import HTTPException


class APIError(Exception):
    """Raised by application code to produce a consistent JSON error response."""

    def __init__(self, message, status_code=400, payload=None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.payload = payload or {}

    def to_dict(self):
        body = {"error": self.message, "status_code": self.status_code}
        body.update(self.payload)
        return body


def register_error_handlers(app):
    @app.errorhandler(APIError)
    def handle_api_error(err):
        return jsonify(err.to_dict()), err.status_code

    @app.errorhandler(HTTPException)
    def handle_http_exception(err):
        return (
            jsonify({"error": err.description, "status_code": err.code}),
            err.code,
        )

    @app.errorhandler(Exception)
    def handle_unexpected_error(err):
        app.logger.exception("Unhandled exception")
        return jsonify({"error": "Internal server error", "status_code": 500}), 500
