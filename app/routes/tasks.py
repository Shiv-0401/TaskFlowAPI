from flask import Blueprint, g, jsonify, request

from app import db
from app.errors import APIError
from app.middleware.auth_middleware import token_required
from app.models import Task
from app.utils.validators import (
    TaskCreateSchema,
    TaskQuerySchema,
    TaskUpdateSchema,
    load_or_400,
)

tasks_bp = Blueprint("tasks", __name__)


def _get_owned_task_or_404(task_id):
    task = db.session.get(Task, task_id)
    if task is None:
        raise APIError("Task not found", 404)
    return task


@tasks_bp.get("")
@token_required
def list_tasks():
    query_params = load_or_400(TaskQuerySchema(), request.args.to_dict())
    page = query_params.get("page", 1)
    per_page = query_params.get("per_page", 20)

    query = Task.query.filter_by(owner_id=g.current_user.id)
    if "status" in query_params:
        query = query.filter_by(status=query_params["status"])
    if "priority" in query_params:
        query = query.filter_by(priority=query_params["priority"])

    pagination = query.order_by(Task.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    return jsonify(
        {
            "tasks": [task.to_dict() for task in pagination.items],
            "page": pagination.page,
            "per_page": pagination.per_page,
            "total": pagination.total,
            "total_pages": pagination.pages,
        }
    )


@tasks_bp.post("")
@token_required
def create_task():
    data = load_or_400(TaskCreateSchema(), request.get_json(silent=True) or {})

    task = Task(
        title=data["title"],
        description=data.get("description"),
        status=data.get("status", "todo"),
        priority=data.get("priority", "medium"),
        owner_id=g.current_user.id,
    )
    db.session.add(task)
    db.session.commit()

    return jsonify(task.to_dict()), 201


@tasks_bp.get("/<int:task_id>")
@token_required
def get_task(task_id):
    task = _get_owned_task_or_404(task_id)
    if task.owner_id != g.current_user.id:
        raise APIError("You do not have access to this task", 403)
    return jsonify(task.to_dict())


@tasks_bp.put("/<int:task_id>")
@token_required
def update_task(task_id):
    task = _get_owned_task_or_404(task_id)
    if task.owner_id != g.current_user.id:
        raise APIError("Only the owner can update this task", 403)

    data = load_or_400(TaskUpdateSchema(), request.get_json(silent=True) or {})
    for field in ("title", "description", "status", "priority"):
        if field in data:
            setattr(task, field, data[field])

    db.session.commit()
    return jsonify(task.to_dict())


@tasks_bp.delete("/<int:task_id>")
@token_required
def delete_task(task_id):
    task = _get_owned_task_or_404(task_id)
    if task.owner_id != g.current_user.id:
        raise APIError("Only the owner can delete this task", 403)

    db.session.delete(task)
    db.session.commit()
    return "", 204
