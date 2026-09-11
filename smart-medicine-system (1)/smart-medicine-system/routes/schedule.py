from datetime import date, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user

from models.medicine import Medicine
from services import reminder_service

schedule_bp = Blueprint("schedule", __name__, url_prefix="/schedule")


@schedule_bp.route("/")
@login_required
def index():
    user_id = current_user.id
    view = request.args.get("view", "today")  # today | week

    reminder_service.sweep_missed_doses(user_id)

    if view == "week":
        today = date.today()
        days = []
        for offset in range(7):
            target = today + timedelta(days=offset)
            reminder_service.ensure_history_for_date(user_id, target)
            from models.history import MedicineHistory
            rows = (
                MedicineHistory.query.filter_by(user_id=user_id, date=target)
                .order_by(MedicineHistory.scheduled_time.asc())
                .all()
            )
            days.append({"date": target, "rows": rows})
        medicine_lookup = {m.id: m for m in Medicine.query.filter_by(user_id=user_id).all()}
        return render_template("schedule.html", view="week", days=days, medicine_lookup=medicine_lookup)

    today_rows = reminder_service.get_today_schedule(user_id)
    missed = reminder_service.get_missed_today(user_id)
    upcoming = reminder_service.get_upcoming_schedule(user_id, days_ahead=3)
    medicine_lookup = {m.id: m for m in Medicine.query.filter_by(user_id=user_id).all()}

    return render_template(
        "schedule.html",
        view="today",
        today_rows=today_rows,
        missed=missed,
        upcoming=upcoming,
        medicine_lookup=medicine_lookup,
    )


@schedule_bp.route("/action/<int:history_id>", methods=["POST"])
@login_required
def dose_action(history_id):
    action = request.form.get("action")  # taken | skipped | remind_later
    redirect_to = request.form.get("redirect_to", "dashboard.index")

    if action in ("taken", "skipped"):
        row = reminder_service.record_action(history_id, current_user.id, action)
        if row:
            flash(f"Marked as {action.capitalize()}.", "success")
        else:
            flash("Could not update that dose.", "danger")
    elif action == "remind_later":
        minutes = request.form.get("minutes", "10")
        minutes = int(minutes) if minutes.isdigit() else 10
        row = reminder_service.remind_later(history_id, current_user.id, minutes)
        if row:
            flash(f"You'll be reminded again in {minutes} minutes.", "info")
        else:
            flash("Could not snooze that dose.", "danger")
    else:
        flash("Unknown action.", "danger")

    try:
        return redirect(url_for(redirect_to))
    except Exception:
        return redirect(url_for("dashboard.index"))
