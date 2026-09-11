from datetime import date, timedelta
from flask import Blueprint, render_template, request
from flask_login import login_required, current_user

from models.medicine import Medicine
from models.history import MedicineHistory

history_bp = Blueprint("history", __name__, url_prefix="/history")

PER_PAGE = 20


@history_bp.route("/")
@login_required
def index():
    user_id = current_user.id
    date_filter = request.args.get("date_filter", "")  # today, yesterday, week, month
    status_filter = request.args.get("status", "")      # Taken, Skipped, Missed
    page = request.args.get("page", 1, type=int)

    query = MedicineHistory.query.filter_by(user_id=user_id)

    today = date.today()
    if date_filter == "today":
        query = query.filter(MedicineHistory.date == today)
    elif date_filter == "yesterday":
        query = query.filter(MedicineHistory.date == today - timedelta(days=1))
    elif date_filter == "week":
        query = query.filter(MedicineHistory.date >= today - timedelta(days=7))
    elif date_filter == "month":
        query = query.filter(MedicineHistory.date >= today - timedelta(days=30))

    if status_filter in ("Taken", "Skipped", "Missed", "Pending"):
        query = query.filter(MedicineHistory.status == status_filter)

    query = query.order_by(MedicineHistory.date.desc(), MedicineHistory.scheduled_time.desc())

    pagination = query.paginate(page=page, per_page=PER_PAGE, error_out=False)
    medicine_lookup = {m.id: m for m in Medicine.query.filter_by(user_id=user_id).all()}

    return render_template(
        "history.html",
        pagination=pagination,
        rows=pagination.items,
        medicine_lookup=medicine_lookup,
        date_filter=date_filter,
        status_filter=status_filter,
    )
