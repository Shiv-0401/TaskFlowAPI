from flask import Blueprint, g, jsonify, request

from app import db
from app.errors import APIError
from app.middleware.auth_middleware import token_required
from app.models import User
from app.utils.validators import UserUpdateSchema, load_or_400

users_bp = Blueprint("users", __name__)


@users_bp.get("/me")
@token_required
def get_me():
    return jsonify(g.current_user.to_dict())


@users_bp.put("/me")
@token_required
def update_me():
    data = load_or_400(UserUpdateSchema(), request.get_json(silent=True) or {})

    if "username" in data and data["username"] != g.current_user.username:
        if User.query.filter_by(username=data["username"]).first() is not None:
            raise APIError("A user with this username already exists", 400)
        g.current_user.username = data["username"]

    if "full_name" in data:
        g.current_user.full_name = data["full_name"]

    db.session.commit()
    return jsonify(g.current_user.to_dict())
