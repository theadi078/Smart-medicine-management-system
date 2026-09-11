from datetime import date
from flask import Blueprint, render_template
from flask_login import login_required, current_user

from models.medicine import Medicine
from models.history import MedicineHistory, STATUS_TAKEN, STATUS_SKIPPED, STATUS_MISSED
from services import reminder_service, expiry_service, notification_service

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/dashboard")
@login_required
def index():
    user_id = current_user.id

    # Ensure today's dose rows exist and missed doses are swept before we count.
    today_rows = reminder_service.get_today_schedule(user_id)
    reminder_service.sweep_missed_doses(user_id)
    expiry_service.run_expiry_check_for_all()

    total_medicines = Medicine.query.filter_by(user_id=user_id, is_active=True).count()
    today_count = len(today_rows)
    expiring_soon = expiry_service.get_expiring_medicines(user_id, within_days=30)
    missed_today = reminder_service.get_missed_today(user_id)
    upcoming = reminder_service.get_upcoming_schedule(user_id, days_ahead=3)

    taken_count = MedicineHistory.query.filter_by(user_id=user_id, date=date.today(), status=STATUS_TAKEN).count()
    skipped_count = MedicineHistory.query.filter_by(user_id=user_id, date=date.today(), status=STATUS_SKIPPED).count()

    unread_notifications = notification_service.get_unread_count(user_id)

    # Refresh today_rows after sweep so statuses (e.g. newly Missed) are current
    today_rows = reminder_service.get_today_schedule(user_id)

    medicine_lookup = {m.id: m for m in Medicine.query.filter_by(user_id=user_id).all()}

    return render_template(
        "dashboard.html",
        total_medicines=total_medicines,
        today_count=today_count,
        expiring_soon_count=len(expiring_soon),
        missed_count=len(missed_today),
        taken_count=taken_count,
        skipped_count=skipped_count,
        today_rows=today_rows,
        expiring_soon=expiring_soon[:5],
        upcoming=upcoming,
        medicine_lookup=medicine_lookup,
        unread_notifications=unread_notifications,
    )
