from datetime import datetime
from models import db

FREQUENCY_CHOICES = ["Daily", "Specific Days", "Alternate Days"]


class MedicineSchedule(db.Model):
    """
    A single scheduled time for a medicine. A medicine can have multiple
    schedules (e.g. morning/afternoon/night).
    """

    __tablename__ = "medicine_schedules"

    id = db.Column(db.Integer, primary_key=True)
    medicine_id = db.Column(db.Integer, db.ForeignKey("medicines.id"), nullable=False, index=True)

    scheduled_time = db.Column(db.Time, nullable=False)  # time-of-day, e.g. 08:00
    frequency = db.Column(db.String(30), default="Daily")
    days_of_week = db.Column(db.String(30), nullable=True)  # e.g. "Mon,Wed,Fri" if not Daily
    reminder_window = db.Column(db.Integer, default=60)  # minutes before "Missed"
    label = db.Column(db.String(30), nullable=True)  # e.g. "Morning", "Night"

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def applies_to_weekday(self, weekday_abbrev: str) -> bool:
        """weekday_abbrev like 'Mon', 'Tue', ... Used for Specific Days schedules."""
        if self.frequency == "Daily":
            return True
        if not self.days_of_week:
            return False
        return weekday_abbrev in [d.strip() for d in self.days_of_week.split(",")]

    def __repr__(self):
        return f"<Schedule {self.scheduled_time} for medicine={self.medicine_id}>"
