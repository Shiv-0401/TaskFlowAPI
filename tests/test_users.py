def test_get_me_success(client, auth_headers):
    response = client.get("/api/users/me", headers=auth_headers)
    assert response.status_code == 200
    body = response.get_json()
    assert body["email"] == "user@example.com"
    assert "password" not in body
    assert "password_hash" not in body


def test_get_me_without_auth_fails(client):
    response = client.get("/api/users/me")
    assert response.status_code == 401


def test_update_me_full_name(client, auth_headers):
    response = client.put(
        "/api/users/me", json={"full_name": "Ada Lovelace"}, headers=auth_headers
    )
    assert response.status_code == 200
    assert response.get_json()["full_name"] == "Ada Lovelace"


def test_update_me_username(client, auth_headers):
    response = client.put(
        "/api/users/me", json={"username": "newusername"}, headers=auth_headers
    )
    assert response.status_code == 200
    assert response.get_json()["username"] == "newusername"


def test_update_me_duplicate_username_fails(client, make_user, auth_headers):
    make_user(email="taken@example.com", username="takenname")
    response = client.put(
        "/api/users/me", json={"username": "takenname"}, headers=auth_headers
    )
    assert response.status_code == 400


def test_update_me_invalid_field_type_fails(client, auth_headers):
    response = client.put(
        "/api/users/me", json={"username": "ab"}, headers=auth_headers
    )
    assert response.status_code == 400
