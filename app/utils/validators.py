from marshmallow import Schema, ValidationError, fields, validate

from app.errors import APIError
from app.models import Task


class RegisterSchema(Schema):
    email = fields.Email(required=True)
    username = fields.String(required=True, validate=validate.Length(min=3, max=80))
    password = fields.String(required=True, validate=validate.Length(min=8, max=128))
    full_name = fields.String(required=False, allow_none=True, validate=validate.Length(max=120))


class LoginSchema(Schema):
    email = fields.Email(required=True)
    password = fields.String(required=True)


class RefreshSchema(Schema):
    refresh_token = fields.String(required=True)


class UserUpdateSchema(Schema):
    full_name = fields.String(required=False, allow_none=True, validate=validate.Length(max=120))
    username = fields.String(required=False, validate=validate.Length(min=3, max=80))


class TaskCreateSchema(Schema):
    title = fields.String(required=True, validate=validate.Length(min=1, max=200))
    description = fields.String(required=False, allow_none=True)
    status = fields.String(required=False, validate=validate.OneOf(Task.STATUSES))
    priority = fields.String(required=False, validate=validate.OneOf(Task.PRIORITIES))


class TaskUpdateSchema(Schema):
    title = fields.String(required=False, validate=validate.Length(min=1, max=200))
    description = fields.String(required=False, allow_none=True)
    status = fields.String(required=False, validate=validate.OneOf(Task.STATUSES))
    priority = fields.String(required=False, validate=validate.OneOf(Task.PRIORITIES))


class TaskQuerySchema(Schema):
    page = fields.Integer(required=False, validate=validate.Range(min=1))
    per_page = fields.Integer(required=False, validate=validate.Range(min=1, max=100))
    status = fields.String(required=False, validate=validate.OneOf(Task.STATUSES))
    priority = fields.String(required=False, validate=validate.OneOf(Task.PRIORITIES))


def load_or_400(schema, data):
    """Validates `data` against `schema`, raising an APIError(400) with field errors on failure."""
    try:
        return schema.load(data)
    except ValidationError as err:
        raise APIError("Invalid input", 400, payload={"details": err.messages})
