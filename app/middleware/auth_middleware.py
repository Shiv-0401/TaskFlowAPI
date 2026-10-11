from functools import wraps

import jwt
from flask import current_app, g, request

from app.errors import APIError


def _decode_token(token, secret_key):
    try:
        return jwt.decode(token, secret_key, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise APIError("Token has expired", 401)
    except jwt.InvalidTokenError:
        raise APIError("Invalid token", 401)


def token_required(f):
    """Verifies a Bearer JWT access token and attaches the user to flask.g.current_user."""

    @wraps(f)
    def decorated(*args, **kwargs):
        from app import db
        from app.models import User

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            raise APIError("Missing or malformed Authorization header", 401)

        token = auth_header.split(" ", 1)[1].strip()
        payload = _decode_token(token, current_app.config["JWT_SECRET_KEY"])

        if payload.get("type") != "access":
            raise APIError("Invalid token type, expected access token", 401)

        user = db.session.get(User, payload.get("sub"))
        if user is None:
            raise APIError("User not found", 401)

        g.current_user = user
        return f(*args, **kwargs)

    return decorated
