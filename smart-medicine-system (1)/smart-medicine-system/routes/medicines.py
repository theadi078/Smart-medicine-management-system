import os
import uuid
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from models import db
from models.medicine import Medicine, FOOD_INSTRUCTIONS
from models.schedule import MedicineSchedule, FREQUENCY_CHOICES

medicines_bp = Blueprint("medicines", __name__, url_prefix="/medicines")


def _allowed_file(filename):
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return ext in current_app.config["ALLOWED_UPLOAD_EXTENSIONS"]


def _save_prescription_file(file_storage):
    """Validate and safely store an uploaded prescription file. Returns stored filename or None."""
    if not file_storage or file_storage.filename == "":
        return None
    if not _allowed_file(file_storage.filename):
        flash("Unsupported file type. Only PNG, JPG, JPEG, and PDF are allowed.", "warning")
        return None

    original = secure_filename(file_storage.filename)
    ext = original.rsplit(".", 1)[-1].lower()
    # Generate a random safe filename to prevent collisions/path issues - never trust user filenames directly.
    safe_name = f"{uuid.uuid4().hex}.{ext}"
    dest = os.path.join(current_app.config["UPLOAD_FOLDER"], safe_name)
    file_storage.save(dest)
    return safe_name


def _parse_date(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def _parse_time(value):
    try:
        return datetime.strptime(value, "%H:%M").time()
    except (ValueError, TypeError):
        return None


@medicines_bp.route("/")
@login_required
def list_medicines():
    search = request.args.get("q", "").strip()
    status_filter = request.args.get("status", "").strip()  # active, expired, expiring_soon, completed
    sort_by = request.args.get("sort", "name")

    query = Medicine.query.filter_by(user_id=current_user.id)
    if search:
        query = query.filter(Medicine.name.ilike(f"%{search}%"))

    medicines = query.all()

    if status_filter == "expired":
        medicines = [m for m in medicines if m.days_until_expiry < 0]
    elif status_filter == "expiring_soon":
        medicines = [m for m in medicines if 0 <= m.days_until_expiry <= 30]
    elif status_filter == "completed":
        medicines = [m for m in medicines if not m.is_active]
    elif status_filter == "active":
        medicines = [m for m in medicines if m.is_active and m.days_until_expiry >= 0]

    if sort_by == "expiry_date":
        medicines.sort(key=lambda m: m.expiry_date)
    elif sort_by == "created_date":
        medicines.sort(key=lambda m: m.created_at, reverse=True)
    else:
        medicines.sort(key=lambda m: m.name.lower())

    return render_template("medicines.html", medicines=medicines, search=search,
                            status_filter=status_filter, sort_by=sort_by)


@medicines_bp.route("/add", methods=["GET", "POST"])
@login_required
def add_medicine():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        medicine_type = request.form.get("medicine_type", "").strip()
        dosage = request.form.get("dosage", "").strip()
        quantity = request.form.get("quantity", "").strip()
        expiry_date = _parse_date(request.form.get("expiry_date"))
        start_date = _parse_date(request.form.get("start_date"))
        end_date = _parse_date(request.form.get("end_date"))
        food_instruction = request.form.get("food_instruction", "Not Specified")
        notes = request.form.get("notes", "").strip()

        errors = []
        if not name:
            errors.append("Medicine name is required.")
        if not expiry_date:
            errors.append("A valid expiry date is required.")
        if quantity and (not quantity.isdigit() or int(quantity) < 0):
            errors.append("Quantity must be a positive number.")
        if start_date and end_date and end_date < start_date:
            errors.append("End date cannot be before start date.")

        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template("add_medicine.html", form=request.form,
                                    food_instructions=FOOD_INSTRUCTIONS,
                                    frequency_choices=FREQUENCY_CHOICES)

        prescription_file = _save_prescription_file(request.files.get("prescription_file"))

        medicine = Medicine(
            user_id=current_user.id,
            name=name,
            medicine_type=medicine_type or None,
            dosage=dosage or None,
            quantity=int(quantity) if quantity else None,
            expiry_date=expiry_date,
            start_date=start_date,
            end_date=end_date,
            food_instruction=food_instruction,
            notes=notes or None,
            prescription_file=prescription_file,
        )
        db.session.add(medicine)
        db.session.flush()  # get medicine.id before commit

        # --- Schedule times (supports multiple) ---
        times = request.form.getlist("schedule_time[]")
        frequency = request.form.get("frequency", "Daily")
        days_of_week = request.form.get("days_of_week", "").strip() or None
        reminder_window = request.form.get("reminder_window", "60")
        reminder_window = int(reminder_window) if reminder_window.isdigit() else 60

        for t in times:
            parsed_time = _parse_time(t)
            if parsed_time:
                db.session.add(MedicineSchedule(
                    medicine_id=medicine.id,
                    scheduled_time=parsed_time,
                    frequency=frequency,
                    days_of_week=days_of_week if frequency == "Specific Days" else None,
                    reminder_window=reminder_window,
                ))

        db.session.commit()
        flash(f"{medicine.name} added successfully.", "success")
        return redirect(url_for("medicines.list_medicines"))

    return render_template("add_medicine.html", form={}, food_instructions=FOOD_INSTRUCTIONS,
                            frequency_choices=FREQUENCY_CHOICES)


@medicines_bp.route("/<int:medicine_id>")
@login_required
def medicine_details(medicine_id):
    medicine = Medicine.query.filter_by(id=medicine_id, user_id=current_user.id).first_or_404()
    return render_template("medicine_details.html", medicine=medicine)


@medicines_bp.route("/<int:medicine_id>/edit", methods=["GET", "POST"])
@login_required
def edit_medicine(medicine_id):
    medicine = Medicine.query.filter_by(id=medicine_id, user_id=current_user.id).first_or_404()

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        expiry_date = _parse_date(request.form.get("expiry_date"))

        errors = []
        if not name:
            errors.append("Medicine name is required.")
        if not expiry_date:
            errors.append("A valid expiry date is required.")

        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template("edit_medicine.html", medicine=medicine,
                                    food_instructions=FOOD_INSTRUCTIONS,
                                    frequency_choices=FREQUENCY_CHOICES)

        medicine.name = name
        medicine.medicine_type = request.form.get("medicine_type", "").strip() or None
        medicine.dosage = request.form.get("dosage", "").strip() or None
        quantity = request.form.get("quantity", "").strip()
        medicine.quantity = int(quantity) if quantity.isdigit() else None
        medicine.expiry_date = expiry_date
        medicine.start_date = _parse_date(request.form.get("start_date"))
        medicine.end_date = _parse_date(request.form.get("end_date"))
        medicine.food_instruction = request.form.get("food_instruction", "Not Specified")
        medicine.notes = request.form.get("notes", "").strip() or None
        medicine.is_active = "is_active" in request.form

        new_file = _save_prescription_file(request.files.get("prescription_file"))
        if new_file:
            medicine.prescription_file = new_file

        db.session.commit()
        flash(f"{medicine.name} updated successfully.", "success")
        return redirect(url_for("medicines.medicine_details", medicine_id=medicine.id))

    return render_template("edit_medicine.html", medicine=medicine,
                            food_instructions=FOOD_INSTRUCTIONS,
                            frequency_choices=FREQUENCY_CHOICES)


@medicines_bp.route("/<int:medicine_id>/delete", methods=["POST"])
@login_required
def delete_medicine(medicine_id):
    medicine = Medicine.query.filter_by(id=medicine_id, user_id=current_user.id).first_or_404()
    name = medicine.name
    db.session.delete(medicine)
    db.session.commit()
    flash(f"{name} was deleted.", "info")
    return redirect(url_for("medicines.list_medicines"))


@medicines_bp.route("/<int:medicine_id>/schedule/add", methods=["POST"])
@login_required
def add_schedule(medicine_id):
    medicine = Medicine.query.filter_by(id=medicine_id, user_id=current_user.id).first_or_404()
    parsed_time = _parse_time(request.form.get("scheduled_time"))
    if not parsed_time:
        flash("Please provide a valid time.", "danger")
        return redirect(url_for("medicines.medicine_details", medicine_id=medicine.id))

    frequency = request.form.get("frequency", "Daily")
    days_of_week = request.form.get("days_of_week", "").strip() or None
    reminder_window = request.form.get("reminder_window", "60")
    reminder_window = int(reminder_window) if reminder_window.isdigit() else 60

    db.session.add(MedicineSchedule(
        medicine_id=medicine.id,
        scheduled_time=parsed_time,
        frequency=frequency,
        days_of_week=days_of_week if frequency == "Specific Days" else None,
        reminder_window=reminder_window,
    ))
    db.session.commit()
    flash("Schedule added.", "success")
    return redirect(url_for("medicines.medicine_details", medicine_id=medicine.id))


@medicines_bp.route("/schedule/<int:schedule_id>/delete", methods=["POST"])
@login_required
def delete_schedule(schedule_id):
    schedule = MedicineSchedule.query.get_or_404(schedule_id)
    medicine = Medicine.query.filter_by(id=schedule.medicine_id, user_id=current_user.id).first_or_404()
    db.session.delete(schedule)
    db.session.commit()
    flash("Schedule removed.", "info")
    return redirect(url_for("medicines.medicine_details", medicine_id=medicine.id))
