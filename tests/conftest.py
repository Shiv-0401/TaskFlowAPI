import pytest

from app import create_app, db as _db
from app.config import TestingConfig
from app.models import Task, User


@pytest.fixture()
def app():
    application = create_app(TestingConfig)

    with application.app_context():
        _db.create_all()
        yield application
        _db.session.remove()
        _db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def db(app):
    return _db


def _register(client, email, username, password="password123", full_name=None):
    payload = {"email": email, "username": username, "password": password}
    if full_name is not None:
        payload["full_name"] = full_name
    return client.post("/api/auth/register", json=payload)


@pytest.fixture()
def make_user(client):
    """Factory fixture: registers a user and returns (user_dict, access_token, refresh_token)."""

    def _make_user(email="user@example.com", username="user1", password="password123"):
        response = _register(client, email, username, password)
        assert response.status_code == 201, response.get_json()
        body = response.get_json()
        return body["user"], body["access_token"], body["refresh_token"]

    return _make_user


@pytest.fixture()
def auth_headers(make_user):
    _, access_token, _ = make_user()
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture()
def second_user_headers(make_user):
    _, access_token, _ = make_user(email="other@example.com", username="user2")
    return {"Authorization": f"Bearer {access_token}"}
