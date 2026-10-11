def test_register_success(client):
    response = client.post(
        "/api/auth/register",
        json={"email": "new@example.com", "username": "newuser", "password": "password123"},
    )
    assert response.status_code == 201
    body = response.get_json()
    assert body["user"]["email"] == "new@example.com"
    assert body["user"]["username"] == "newuser"
    assert "password" not in body["user"]
    assert "password_hash" not in body["user"]
    assert body["access_token"]
    assert body["refresh_token"]


def test_register_duplicate_email_fails(client, make_user):
    make_user(email="dupe@example.com", username="dupe1")
    response = client.post(
        "/api/auth/register",
        json={"email": "dupe@example.com", "username": "dupe2", "password": "password123"},
    )
    assert response.status_code == 400
    assert "email" in response.get_json()["error"].lower()


def test_register_duplicate_username_fails(client, make_user):
    make_user(email="a@example.com", username="dupeuser")
    response = client.post(
        "/api/auth/register",
        json={"email": "b@example.com", "username": "dupeuser", "password": "password123"},
    )
    assert response.status_code == 400
    assert "username" in response.get_json()["error"].lower()


def test_register_invalid_email_returns_400(client):
    response = client.post(
        "/api/auth/register",
        json={"email": "not-an-email", "username": "someone", "password": "password123"},
    )
    assert response.status_code == 400
    body = response.get_json()
    assert body["status_code"] == 400
    assert "details" in body


def test_register_short_password_returns_400(client):
    response = client.post(
        "/api/auth/register",
        json={"email": "short@example.com", "username": "shortpw", "password": "abc"},
    )
    assert response.status_code == 400


def test_register_missing_fields_returns_400(client):
    response = client.post("/api/auth/register", json={"email": "missing@example.com"})
    assert response.status_code == 400


def test_login_success(client, make_user):
    make_user(email="login@example.com", username="loginuser", password="password123")
    response = client.post(
        "/api/auth/login",
        json={"email": "login@example.com", "password": "password123"},
    )
    assert response.status_code == 200
    body = response.get_json()
    assert body["access_token"]
    assert body["refresh_token"]


def test_login_wrong_password_fails(client, make_user):
    make_user(email="wrongpw@example.com", username="wrongpwuser", password="password123")
    response = client.post(
        "/api/auth/login",
        json={"email": "wrongpw@example.com", "password": "incorrect"},
    )
    assert response.status_code == 401


def test_login_nonexistent_user_fails(client):
    response = client.post(
        "/api/auth/login",
        json={"email": "ghost@example.com", "password": "password123"},
    )
    assert response.status_code == 401


def test_refresh_returns_new_tokens(client, make_user):
    _, _, refresh_token = make_user(email="refresh@example.com", username="refreshuser")
    response = client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
    assert response.status_code == 200
    body = response.get_json()
    assert body["access_token"]
    assert body["refresh_token"]


def test_refresh_with_access_token_fails(client, make_user):
    _, access_token, _ = make_user(email="badrefresh@example.com", username="badrefreshuser")
    response = client.post("/api/auth/refresh", json={"refresh_token": access_token})
    assert response.status_code == 401


def test_refresh_with_garbage_token_fails(client):
    response = client.post("/api/auth/refresh", json={"refresh_token": "not-a-real-token"})
    assert response.status_code == 401


def test_protected_route_without_token_fails(client):
    response = client.get("/api/users/me")
    assert response.status_code == 401


def test_protected_route_with_malformed_header_fails(client):
    response = client.get("/api/users/me", headers={"Authorization": "Token abc123"})
    assert response.status_code == 401


def test_protected_route_with_invalid_token_fails(client):
    response = client.get(
        "/api/users/me", headers={"Authorization": "Bearer not-a-real-token"}
    )
    assert response.status_code == 401
