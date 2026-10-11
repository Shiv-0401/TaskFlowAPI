from flask import Flask, jsonify
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

from app.config import get_config
from app.middleware.rate_limiter import limiter

db = SQLAlchemy()
migrate = Migrate()


def create_app(config_object=None):
    app = Flask(__name__)
    app.config.from_object(config_object or get_config())

    db.init_app(app)
    migrate.init_app(app, db)
    limiter.init_app(app)

    from app import models  # noqa: F401  (registers models with SQLAlchemy metadata)

    from app.routes.auth import auth_bp
    from app.routes.tasks import tasks_bp
    from app.routes.users import users_bp

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(tasks_bp, url_prefix="/api/tasks")
    app.register_blueprint(users_bp, url_prefix="/api/users")

    from app.errors import register_error_handlers

    register_error_handlers(app)

    @app.get("/health")
    def health():
        return jsonify({"status": "ok"})

    return app
