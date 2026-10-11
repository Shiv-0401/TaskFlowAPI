def _create_task(client, headers, **overrides):
    payload = {"title": "Write tests", "description": "Cover the API", "priority": "high"}
    payload.update(overrides)
    return client.post("/api/tasks", json=payload, headers=headers)


def test_create_task_success(client, auth_headers):
    response = _create_task(client, auth_headers)
    assert response.status_code == 201
    body = response.get_json()
    assert body["title"] == "Write tests"
    assert body["status"] == "todo"
    assert body["priority"] == "high"
    assert body["owner_id"] is not None


def test_create_task_without_auth_fails(client):
    response = client.post("/api/tasks", json={"title": "No auth"})
    assert response.status_code == 401


def test_create_task_missing_title_fails(client, auth_headers):
    response = client.post("/api/tasks", json={"description": "no title"}, headers=auth_headers)
    assert response.status_code == 400


def test_create_task_invalid_status_fails(client, auth_headers):
    response = _create_task(client, auth_headers, status="not-a-status")
    assert response.status_code == 400


def test_create_task_invalid_priority_fails(client, auth_headers):
    response = _create_task(client, auth_headers, priority="urgent")
    assert response.status_code == 400


def test_get_task_success(client, auth_headers):
    created = _create_task(client, auth_headers).get_json()
    response = client.get(f"/api/tasks/{created['id']}", headers=auth_headers)
    assert response.status_code == 200
    assert response.get_json()["id"] == created["id"]


def test_get_task_not_found(client, auth_headers):
    response = client.get("/api/tasks/999999", headers=auth_headers)
    assert response.status_code == 404


def test_get_other_users_task_forbidden(client, auth_headers, second_user_headers):
    created = _create_task(client, auth_headers).get_json()
    response = client.get(f"/api/tasks/{created['id']}", headers=second_user_headers)
    assert response.status_code == 403


def test_update_task_success(client, auth_headers):
    created = _create_task(client, auth_headers).get_json()
    response = client.put(
        f"/api/tasks/{created['id']}",
        json={"status": "in_progress", "title": "Updated title"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.get_json()
    assert body["status"] == "in_progress"
    assert body["title"] == "Updated title"


def test_update_task_invalid_field_fails(client, auth_headers):
    created = _create_task(client, auth_headers).get_json()
    response = client.put(
        f"/api/tasks/{created['id']}",
        json={"status": "bogus"},
        headers=auth_headers,
    )
    assert response.status_code == 400


def test_update_other_users_task_forbidden(client, auth_headers, second_user_headers):
    created = _create_task(client, auth_headers).get_json()
    response = client.put(
        f"/api/tasks/{created['id']}",
        json={"status": "done"},
        headers=second_user_headers,
    )
    assert response.status_code == 403


def test_delete_task_success(client, auth_headers):
    created = _create_task(client, auth_headers).get_json()
    response = client.delete(f"/api/tasks/{created['id']}", headers=auth_headers)
    assert response.status_code == 204

    follow_up = client.get(f"/api/tasks/{created['id']}", headers=auth_headers)
    assert follow_up.status_code == 404


def test_delete_other_users_task_forbidden(client, auth_headers, second_user_headers):
    created = _create_task(client, auth_headers).get_json()
    response = client.delete(f"/api/tasks/{created['id']}", headers=second_user_headers)
    assert response.status_code == 403

    still_there = client.get(f"/api/tasks/{created['id']}", headers=auth_headers)
    assert still_there.status_code == 200


def test_list_tasks_only_returns_own_tasks(client, auth_headers, second_user_headers):
    _create_task(client, auth_headers, title="Mine")
    _create_task(client, second_user_headers, title="Theirs")

    response = client.get("/api/tasks", headers=auth_headers)
    assert response.status_code == 200
    body = response.get_json()
    assert body["total"] == 1
    assert body["tasks"][0]["title"] == "Mine"


def test_list_tasks_pagination(client, auth_headers):
    for i in range(5):
        _create_task(client, auth_headers, title=f"Task {i}")

    response = client.get("/api/tasks?page=1&per_page=2", headers=auth_headers)
    assert response.status_code == 200
    body = response.get_json()
    assert len(body["tasks"]) == 2
    assert body["page"] == 1
    assert body["per_page"] == 2
    assert body["total"] == 5
    assert body["total_pages"] == 3

    response_page_2 = client.get("/api/tasks?page=2&per_page=2", headers=auth_headers)
    assert len(response_page_2.get_json()["tasks"]) == 2


def test_list_tasks_filter_by_status(client, auth_headers):
    _create_task(client, auth_headers, title="Todo task")
    done_task = _create_task(client, auth_headers, title="Done task").get_json()
    client.put(f"/api/tasks/{done_task['id']}", json={"status": "done"}, headers=auth_headers)

    response = client.get("/api/tasks?status=done", headers=auth_headers)
    body = response.get_json()
    assert body["total"] == 1
    assert body["tasks"][0]["status"] == "done"


def test_list_tasks_filter_by_priority(client, auth_headers):
    _create_task(client, auth_headers, title="Low prio", priority="low")
    _create_task(client, auth_headers, title="High prio", priority="high")

    response = client.get("/api/tasks?priority=high", headers=auth_headers)
    body = response.get_json()
    assert body["total"] == 1
    assert body["tasks"][0]["priority"] == "high"


def test_list_tasks_invalid_query_param_fails(client, auth_headers):
    response = client.get("/api/tasks?status=bogus", headers=auth_headers)
    assert response.status_code == 400


def test_list_tasks_invalid_per_page_fails(client, auth_headers):
    response = client.get("/api/tasks?per_page=1000", headers=auth_headers)
    assert response.status_code == 400
