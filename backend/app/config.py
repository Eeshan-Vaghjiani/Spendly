"""Environment-backed Flask configuration."""

from __future__ import annotations

import os
from datetime import timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def database_url() -> str | None:
    value = os.getenv("DATABASE_URL")
    if value and value.startswith("postgresql://"):
        return value.replace("postgresql://", "postgresql+psycopg://", 1)
    if value and value.startswith("postgres://"):
        return value.replace("postgres://", "postgresql+psycopg://", 1)
    return value


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
    SQLALCHEMY_DATABASE_URI = database_url()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True, "pool_recycle": 300}
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(
        seconds=int(os.getenv("JWT_ACCESS_TOKEN_SECONDS", "2592000"))
    )
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_UPLOAD_BYTES", str(2 * 1024 * 1024)))
    ALLOWED_CORS_ORIGINS = tuple(
        value.strip()
        for value in os.getenv("ALLOWED_CORS_ORIGINS", "http://localhost:3000").split(
            ","
        )
        if value.strip()
    )
    MODEL_ROOT = Path(
        os.getenv("MODEL_ROOT", str(PROJECT_ROOT / "artifacts" / "models"))
    )
    FORECAST_MODEL_VERSION = os.getenv("FORECAST_MODEL_VERSION", "v1")
    ANOMALY_MODEL_VERSION = os.getenv("ANOMALY_MODEL_VERSION", "v1")
    MODEL_RUNTIME = os.getenv("MODEL_RUNTIME", "full").lower()
    SELECTED_MODEL_ROOT = os.getenv("SELECTED_MODEL_ROOT")
    LOAD_MODELS = os.getenv("LOAD_MODELS", "true").lower() == "true"
    DATA_RETENTION_DAYS = int(os.getenv("DATA_RETENTION_DAYS", "0"))
    ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
    ADMIN_SESSION_IDLE_SECONDS = 1800
    ADMIN_SESSION_MAX_SECONDS = 28800
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Strict"
    SESSION_COOKIE_SECURE = (
        os.getenv("SESSION_COOKIE_SECURE", os.getenv("RENDER", "false")).lower()
        == "true"
    )
    GOOGLE_WEB_CLIENT_ID = os.getenv("GOOGLE_WEB_CLIENT_ID")
    JSON_SORT_KEYS = False


class TestingConfig(Config):
    TESTING = True
    SECRET_KEY = "test-only-secret-key-at-least-32-bytes"
    JWT_SECRET_KEY = "test-only-jwt-secret-at-least-32-bytes"
    SQLALCHEMY_DATABASE_URI = "sqlite+pysqlite:///:memory:"
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=5)
    LOAD_MODELS = False
    ALLOWED_CORS_ORIGINS = ("http://localhost",)
