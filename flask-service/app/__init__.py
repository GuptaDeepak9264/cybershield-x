from flask import Flask, g
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .config import Settings


def create_app(settings: Settings | None = None) -> Flask:
    """
    Application factory rather than a module-level `app = Flask(__name__)`.
    Same reason as fastapi-service's get_settings() lesson: a factory lets
    tests build an app with different settings/engine without fighting
    module-level state.
    """
    app = Flask(__name__)
    app.config["SETTINGS"] = settings or Settings()

    connect_args = {"check_same_thread": False} if app.config["SETTINGS"].DB_ENGINE == "sqlite3" else {}
    engine = create_engine(app.config["SETTINGS"].database_url, connect_args=connect_args, pool_pre_ping=True)
    app.config["DB_SESSION_FACTORY"] = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    app.config["DB_ENGINE_OBJ"] = engine

    @app.teardown_appcontext
    def close_db_session(exception=None):
        session = g.pop("db_session", None)
        if session is not None:
            session.close()

    from .routes.analytics import analytics_bp
    from .routes.email import email_bp
    from .routes.export import export_bp
    from .routes.log_analysis import log_analysis_bp
    from .routes.reports import reports_bp

    app.register_blueprint(reports_bp)
    app.register_blueprint(email_bp)
    app.register_blueprint(export_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(log_analysis_bp)

    @app.get("/health")
    def health_check():
        return {"status": "ok", "service": "cybershield-x-flask"}

    return app


def get_db():
    """Per-request SQLAlchemy session, cached on Flask's request-local `g`."""
    if "db_session" not in g:
        from flask import current_app

        g.db_session = current_app.config["DB_SESSION_FACTORY"]()
    return g.db_session
