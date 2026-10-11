from datetime import datetime, timezone

import jwt
from flask import Blueprint, current_app, jsonify, request

from app import db
from app.errors import APIError
from app.models import User
from app.utils.validators import LoginSchema, RefreshSchema, RegisterSchema, load_or_400

auth_bp = Blueprint("auth", __name__)


def _generate_tokens(user):
    now = datetime.now(timezone.utc)
    access_payload = {
        "sub": user.id,
        "type": "access",
        "iat": now,
        "exp": now + current_app.config["JWT_ACCESS_TOKEN_EXPIRES"],
    }
    refresh_payload = {
        "sub": user.id,
        "type": "refresh",
        "iat": now,
        "exp": now + current_app.config["JWT_REFRESH_TOKEN_EXPIRES"],
    }
    secret = current_app.config["JWT_SECRET_KEY"]
    access_token = jwt.encode(access_payload, secret, algorithm="HS256")
    refresh_token = jwt.encode(refresh_payload, secret, algorithm="HS256")
    return access_token, refresh_token


@auth_bp.post("/register")
def register():
    data = load_or_400(RegisterSchema(), request.get_json(silent=True) or {})

    if User.query.filter_by(email=data["email"]).first() is not None:
        raise APIError("A user with this email already exists", 400)
    if User.query.filter_by(username=data["username"]).first() is not None:
        raise APIError("A user with this username already exists", 400)

    user = User(
        email=data["email"],
        username=data["username"],
        full_name=data.get("full_name"),
    )
    user.set_password(data["password"])
    db.session.add(user)
    db.session.commit()

    access_token, refresh_token = _generate_tokens(user)
    return (
        jsonify(
            {
                "user": user.to_dict(),
                "access_token": access_token,
                "refresh_token": refresh_token,
            }
        ),
        201,
    )


@auth_bp.post("/login")
def login():
    data = load_or_400(LoginSchema(), request.get_json(silent=True) or {})

    user = User.query.filter_by(email=data["email"]).first()
    if user is None or not user.check_password(data["password"]):
        raise APIError("Invalid email or password", 401)

    access_token, refresh_token = _generate_tokens(user)
    return jsonify(
        {
            "user": user.to_dict(),
            "access_token": access_token,
            "refresh_token": refresh_token,
        }
    )


@auth_bp.post("/refresh")
def refresh():
    data = load_or_400(RefreshSchema(), request.get_json(silent=True) or {})

    try:
        payload = jwt.decode(
            data["refresh_token"],
            current_app.config["JWT_SECRET_KEY"],
            algorithms=["HS256"],
        )
    except jwt.ExpiredSignatureError:
        raise APIError("Refresh token has expired", 401)
    except jwt.InvalidTokenError:
        raise APIError("Invalid refresh token", 401)

    if payload.get("type") != "refresh":
        raise APIError("Invalid token type, expected refresh token", 401)

    user = db.session.get(User, payload.get("sub"))
    if user is None:
        raise APIError("User not found", 401)

    access_token, refresh_token = _generate_tokens(user)
    return jsonify({"access_token": access_token, "refresh_token": refresh_token})
