from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user

from models import db

profile_bp = Blueprint("profile", __name__)


@profile_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if name:
            current_user.name = name
            db.session.commit()
            flash("Profile updated.", "success")
        return redirect(url_for("profile.profile"))
    return render_template("profile.html")


@profile_bp.route("/profile/change-password", methods=["POST"])
@login_required
def change_password():
    current_password = request.form.get("current_password", "")
    new_password = request.form.get("new_password", "")
    confirm_password = request.form.get("confirm_password", "")

    if not current_user.check_password(current_password):
        flash("Current password is incorrect.", "danger")
    elif len(new_password) < 6:
        flash("New password must be at least 6 characters.", "danger")
    elif new_password != confirm_password:
        flash("New passwords do not match.", "danger")
    else:
        current_user.set_password(new_password)
        db.session.commit()
        flash("Password changed successfully.", "success")

    return redirect(url_for("profile.profile"))


@profile_bp.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    if request.method == "POST":
        current_user.theme_preference = request.form.get("theme_preference", "light")
        current_user.notifications_enabled = "notifications_enabled" in request.form
        window = request.form.get("default_reminder_window", "60")
        current_user.default_reminder_window = int(window) if window.isdigit() else 60
        db.session.commit()
        flash("Settings saved.", "success")
        return redirect(url_for("profile.settings"))
    return render_template("settings.html")
