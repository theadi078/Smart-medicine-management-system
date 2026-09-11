from datetime import datetime, date
from models import db

FOOD_INSTRUCTIONS = ["Before Food", "After Food", "With Food", "Not Specified"]


class Medicine(db.Model):
    """
    A medicine the user has added, based on their own prescription/
    instructions. This app never generates or invents this data - it is
    always user-entered.
    """

    __tablename__ = "medicines"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)

    name = db.Column(db.String(150), nullable=False)
    medicine_type = db.Column(db.String(50), nullable=True)  # Tablet, Syrup, Capsule, etc.
    dosage = db.Column(db.String(100), nullable=True)  # user-entered, e.g. "500mg"
    quantity = db.Column(db.Integer, nullable=True)  # units remaining/purchased

    expiry_date = db.Column(db.Date, nullable=False)
    start_date = db.Column(db.Date, nullable=True)
    end_date = db.Column(db.Date, nullable=True)

    food_instruction = db.Column(db.String(30), default="Not Specified")
    notes = db.Column(db.Text, nullable=True)
    prescription_file = db.Column(db.String(255), nullable=True)  # stored filename

    is_active = db.Column(db.Boolean, default=True)  # soft "completed/archived" flag

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # --- Relationships ---
    schedules = db.relationship(
        "MedicineSchedule", backref="medicine", lazy=True, cascade="all, delete-orphan"
    )
    history_entries = db.relationship(
        "MedicineHistory", backref="medicine", lazy=True, cascade="all, delete-orphan"
    )
    notifications = db.relationship(
        "Notification", backref="medicine", lazy=True, cascade="all, delete-orphan"
    )

    # --- Derived/helper properties ---
    @property
    def days_until_expiry(self) -> int:
        return (self.expiry_date - date.today()).days

    @property
    def expiry_status(self) -> str:
        """Returns one of: expired, expiring_tomorrow, expiring_soon, normal."""
        days = self.days_until_expiry
        if days < 0:
            return "expired"
        if days == 0:
            return "expiring_tomorrow"  # expires today - treat as most urgent visible state
        if days == 1:
            return "expiring_tomorrow"
        if days <= 7:
            return "expiring_soon"
        if days <= 30:
            return "expiring_soon"
        return "normal"

    def __repr__(self):
        return f"<Medicine {self.name} (user={self.user_id})>"
