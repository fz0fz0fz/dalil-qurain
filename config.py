import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()


def env_bool(name, default=False):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key")

    raw_db_url = os.environ.get("DATABASE_URL", "sqlite:///local.db")
    if raw_db_url.startswith("postgres://"):
        raw_db_url = raw_db_url.replace("postgres://", "postgresql://", 1)
    SQLALCHEMY_DATABASE_URI = raw_db_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}

    ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")
    ADMIN_PASSWORD_HASH = os.environ.get("ADMIN_PASSWORD_HASH", "")

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = env_bool("SESSION_COOKIE_SECURE", False)
    PERMANENT_SESSION_LIFETIME = timedelta(hours=12)

    ADMIN_LOGIN_MAX_ATTEMPTS = int(os.environ.get("ADMIN_LOGIN_MAX_ATTEMPTS", 5))
    ADMIN_LOGIN_LOCK_MINUTES = int(os.environ.get("ADMIN_LOGIN_LOCK_MINUTES", 15))

    MAX_LISTINGS_PER_CATEGORY = int(os.environ.get("MAX_LISTINGS_PER_CATEGORY", 100))
