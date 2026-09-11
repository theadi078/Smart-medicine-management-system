from flask import Blueprint, render_template, request, redirect, url_for
from flask_login import login_required, current_user

from services import notification_service

notifications_bp = Blueprint("notifications", __name__, url_prefix="/notifications")


@notifications_bp.route("/")
@login_required
def index():
    category = request.args.get("category", "")
    notifications = notification_service.get_user_notifications(
        current_user.id, category=category or None
    )
    return render_template("notifications.html", notifications=notifications, category=category)


@notifications_bp.route("/<int:notification_id>/read", methods=["POST"])
@login_required
def mark_read(notification_id):
    notification_service.mark_as_read(notification_id, current_user.id)
    return redirect(url_for("notifications.index"))


@notifications_bp.route("/read-all", methods=["POST"])
@login_required
def mark_all_read():
    notification_service.mark_all_as_read(current_user.id)
    return redirect(url_for("notifications.index"))
