"""
Application configuration.

All secrets and environment-specific values are loaded from environment
variables (see .env.example). Never hard-code secrets here.
"""

import os
from datetime import timedelta
from dotenv import load_dotenv

# Load variables from a .env file if present (does nothing in production
# environments where real env vars are already set).
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))


class Config:
    """Base configuration shared by all environments."""

    # --- Core Flask ---
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-insecure-key-change-me")
    DEBUG = os.environ.get("FLASK_DEBUG", "False").lower() in ("1", "true", "yes")

    # --- Database ---
    # Default to a local SQLite DB inside /database. Designed so that
    # swapping DATABASE_URL to a MySQL/PostgreSQL URI is a drop-in change
    # because we only use SQLAlchemy ORM features (no raw SQLite-specific SQL).
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        f"sqlite:///{os.path.join(BASE_DIR, 'database', 'smart_medicine.db')}",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # --- Uploads ---
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
    ALLOWED_UPLOAD_EXTENSIONS = {"png", "jpg", "jpeg", "pdf"}
    MAX_CONTENT_LENGTH = int(os.environ.get("MAX_UPLOAD_MB", 5)) * 1024 * 1024

    # --- Sessions ---
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"

    # --- App-specific business rules ---
    DEFAULT_REMINDER_WINDOW_MINUTES = int(os.environ.get("DEFAULT_REMINDER_WINDOW", 60))
    EXPIRY_ALERT_DAYS = [30, 7, 1]  # thresholds for expiry notifications

    # --- Optional AI ---
    AI_API_KEY = os.environ.get("AI_API_KEY", "").strip()

    # --- CSRF ---
    WTF_CSRF_ENABLED = True


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


config_map = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
