from datetime import datetime
from models import db

STATUS_PENDING = "Pending"
STATUS_TAKEN = "Taken"
STATUS_SKIPPED = "Skipped"
STATUS_MISSED = "Missed"

ALLOWED_STATUSES = [STATUS_PENDING, STATUS_TAKEN, STATUS_SKIPPED, STATUS_MISSED]


class MedicineHistory(db.Model):
    """
    One row per scheduled dose occurrence. Created (as Pending) when a
    scheduled time is generated for a given date, then updated when the
    user acts (Taken/Skipped) or when the scheduler marks it Missed after
    the reminder window elapses.
    """

    __tablename__ = "medicine_history"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    medicine_id = db.Column(db.Integer, db.ForeignKey("medicines.id"), nullable=False, index=True)
    schedule_id = db.Column(db.Integer, db.ForeignKey("medicine_schedules.id"), nullable=True)

    date = db.Column(db.Date, nullable=False, index=True)  # calendar date of the dose
    scheduled_time = db.Column(db.Time, nullable=False)  # time-of-day it was due
    action_time = db.Column(db.DateTime, nullable=True)  # when user acted (or scheduler marked missed)
    status = db.Column(db.String(20), default=STATUS_PENDING, nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Prevent duplicate rows for the same medicine/schedule/date
    __table_args__ = (
        db.UniqueConstraint("schedule_id", "date", name="uq_schedule_date"),
    )

    def __repr__(self):
        return f"<History med={self.medicine_id} {self.date} {self.scheduled_time} {self.status}>"
