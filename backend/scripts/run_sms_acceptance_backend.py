"""Disposable loopback SMS lab. Never reads a persistent DATABASE_URL or inbox."""
from pathlib import Path
from uuid import uuid4

from sqlalchemy.pool import StaticPool
from flask import request

from backend.app import create_app
from backend.app.extensions import db


def create_sms_acceptance_app():
    root = Path(__file__).resolve().parents[2]
    app = create_app({
        "TESTING": True, "LOAD_MODELS": False, "SELECTED_MODEL_ROOT": None,
        "MODEL_ROOT": root / "artifacts/models", "MPESA_SMS_ENABLED": True,
        "SECRET_KEY": "sms-disposable-local-fixture-only-32-bytes",
        "JWT_SECRET_KEY": "sms-disposable-local-jwt-fixture-32-bytes",
        "SQLALCHEMY_DATABASE_URI": "sqlite+pysqlite:///:memory:",
        "SQLALCHEMY_ENGINE_OPTIONS": {"poolclass": StaticPool, "pool_recycle": -1,
            "connect_args": {"check_same_thread": False}},
        "ADMIN_USERNAME": None, "ADMIN_PASSWORD": None, "GOOGLE_WEB_CLIENT_ID": None,
        "SOURCE_REVISION": None, "SESSION_COOKIE_SECURE": False,
        "ALLOWED_CORS_ORIGINS": ("http://localhost",),
    })
    with app.app_context():
        db.create_all()

    # Coordination contains only phase labels, never SMS or credentials. These
    # routes exist solely in this loopback-only, in-memory test application.
    checkpoint = {"phase": "waiting", "ack": False}
    lab_id = str(uuid4())

    @app.route("/api/v1/sms-lab-checkpoint", methods=["GET", "POST"])
    def lab_checkpoint():
        if request.method == "POST":
            payload = request.get_json() or {}
            if "phase" in payload:
                checkpoint.update(phase=payload["phase"], ack=False)
            elif payload.get("ack") is True:
                checkpoint["ack"] = True
        return {"success": True, "data": checkpoint}

    @app.get("/api/v1/sms-acceptance-target")
    def attest_target():
        return {"success": True, "data": {"disposable": True, "database": "in_memory",
            "mpesa_sms": True, "inference": "not_exercised", "lab_id": lab_id}}
    return app


if __name__ == "__main__":
    create_sms_acceptance_app().run(host="127.0.0.1", port=5057, debug=False, use_reloader=False, threaded=False)
