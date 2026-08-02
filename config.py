import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key")

    # Render يوفر DATABASE_URL يبدأ بـ postgres:// وSQLAlchemy يحتاج postgresql://
    raw_db_url = os.environ.get("DATABASE_URL", "sqlite:///local.db")
    if raw_db_url.startswith("postgres://"):
        raw_db_url = raw_db_url.replace("postgres://", "postgresql://", 1)
    SQLALCHEMY_DATABASE_URI = raw_db_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
    }

    ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")

    MAX_LISTINGS_PER_CATEGORY = int(os.environ.get("MAX_LISTINGS_PER_CATEGORY", 15))
