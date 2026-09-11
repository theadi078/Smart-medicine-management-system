from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from models import db


class User(UserMixin, db.Model):
    """
    A registered user of the system. UserMixin supplies Flask-Login's
    required properties (is_authenticated, is_active, is_anonymous, get_id).
    """

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # --- Settings (Priority 2, kept simple and user-specific) ---
    theme_preference = db.Column(db.String(20), default="light")
    default_reminder_window = db.Column(db.Integer, default=60)  # minutes
    notifications_enabled = db.Column(db.Boolean, default=True)

    # --- Relationships ---
    medicines = db.relationship(
        "Medicine", backref="user", lazy=True, cascade="all, delete-orphan"
    )
    history_entries = db.relationship(
        "MedicineHistory", backref="user", lazy=True, cascade="all, delete-orphan"
    )
    notifications = db.relationship(
        "Notification", backref="user", lazy=True, cascade="all, delete-orphan"
    )

    def set_password(self, raw_password: str) -> None:
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password: str) -> bool:
        return check_password_hash(self.password_hash, raw_password)

    def __repr__(self):
        return f"<User {self.email}>"
