from datetime import datetime
from models import db

TYPE_REMINDER = "MEDICINE_REMINDER"
TYPE_EXPIRY = "EXPIRY_ALERT"
TYPE_MISSED = "MISSED_MEDICINE"
TYPE_SYSTEM = "SYSTEM"

ALLOWED_TYPES = [TYPE_REMINDER, TYPE_EXPIRY, TYPE_MISSED, TYPE_SYSTEM]


class Notification(db.Model):
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    medicine_id = db.Column(db.Integer, db.ForeignKey("medicines.id"), nullable=True)

    notification_type = db.Column(db.String(30), nullable=False)
    message = db.Column(db.String(500), nullable=False)
    is_read = db.Column(db.Boolean, default=False)

    # Used to prevent duplicate expiry alerts for the same medicine+threshold
    dedupe_key = db.Column(db.String(150), nullable=True, index=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<Notification {self.notification_type} user={self.user_id}>"
