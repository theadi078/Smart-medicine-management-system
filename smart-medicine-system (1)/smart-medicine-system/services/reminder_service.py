"""
Reminder / dose-tracking service.

Responsibilities:
1. Ensure a MedicineHistory row (status=Pending) exists for every schedule
   that applies "today" - this is what powers "Today's Medicines".
2. Generate a MEDICINE_REMINDER notification when a scheduled time arrives.
3. Handle user actions: Taken / Skip / Remind Later.
4. Sweep for doses whose reminder window has elapsed and mark them Missed.

All functions are idempotent / safe to call repeatedly (e.g. from
APScheduler on a periodic tick, or synchronously on page load) thanks to
the UniqueConstraint on (schedule_id, date) in MedicineHistory.
"""

from datetime import datetime, date, timedelta, time as dtime

from models import db
from models.medicine import Medicine
from models.schedule import MedicineSchedule
from models.history import (
    MedicineHistory,
    STATUS_PENDING,
    STATUS_TAKEN,
    STATUS_SKIPPED,
    STATUS_MISSED,
)
from services.notification_service import create_notification
from models.notification import TYPE_REMINDER, TYPE_MISSED

WEEKDAY_ABBREVS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def _weekday_abbrev(d: date) -> str:
    return WEEKDAY_ABBREVS[d.weekday()]


def ensure_history_for_date(user_id, target_date: date):
    """
    Make sure every applicable schedule for the given user has a
    MedicineHistory row (Pending) for target_date. Skips medicines outside
    their start/end date range. Idempotent - relies on the unique
    constraint to avoid duplicates.
    """
    medicines = Medicine.query.filter_by(user_id=user_id, is_active=True).all()
    weekday = _weekday_abbrev(target_date)
    created_rows = []

    for medicine in medicines:
        if medicine.start_date and target_date < medicine.start_date:
            continue
        if medicine.end_date and target_date > medicine.end_date:
            continue

        for schedule in medicine.schedules:
            if not schedule.applies_to_weekday(weekday):
                continue

            existing = MedicineHistory.query.filter_by(
                schedule_id=schedule.id, date=target_date
            ).first()
            if existing:
                continue

            row = MedicineHistory(
                user_id=user_id,
                medicine_id=medicine.id,
                schedule_id=schedule.id,
                date=target_date,
                scheduled_time=schedule.scheduled_time,
                status=STATUS_PENDING,
            )
            db.session.add(row)
            created_rows.append(row)

    if created_rows:
        db.session.commit()
    return created_rows


def get_today_schedule(user_id):
    """Ensure today's rows exist, then return them ordered by time."""
    today = date.today()
    ensure_history_for_date(user_id, today)
    rows = (
        MedicineHistory.query.filter_by(user_id=user_id, date=today)
        .order_by(MedicineHistory.scheduled_time.asc())
        .all()
    )
    return rows


def get_upcoming_schedule(user_id, days_ahead=3):
    """Next few upcoming (still-pending, future) doses across the next N days, for dashboard widget."""
    today = date.today()
    upcoming = []
    for offset in range(0, days_ahead + 1):
        target = today + timedelta(days=offset)
        ensure_history_for_date(user_id, target)
        rows = (
            MedicineHistory.query.filter_by(user_id=user_id, date=target, status=STATUS_PENDING)
            .order_by(MedicineHistory.scheduled_time.asc())
            .all()
        )
        for r in rows:
            # Skip times already past today
            if target == today:
                due_dt = datetime.combine(target, r.scheduled_time)
                if due_dt < datetime.now():
                    continue
            upcoming.append(r)
    return upcoming[:10]


def get_next_medicine(user_id):
    """Single next upcoming scheduled dose (soonest pending one from now onward)."""
    upcoming = get_upcoming_schedule(user_id, days_ahead=7)
    return upcoming[0] if upcoming else None


def get_current_scheduled_medicine(user_id, window_minutes=60):
    """
    'Current' medicine = a Pending dose whose scheduled time is within
    +/- window_minutes of right now. Used for "what's scheduled now".
    """
    now = datetime.now()
    today_rows = get_today_schedule(user_id)
    current = []
    for r in today_rows:
        if r.status != STATUS_PENDING:
            continue
        due_dt = datetime.combine(r.date, r.scheduled_time)
        delta_minutes = abs((now - due_dt).total_seconds()) / 60
        if delta_minutes <= window_minutes:
            current.append(r)
    return current


def record_action(history_id, user_id, action):
    """
    action: 'taken' | 'skipped'
    Records the user's response to a scheduled dose. Ownership-checked.
    """
    row = MedicineHistory.query.filter_by(id=history_id, user_id=user_id).first()
    if not row:
        return None

    if action == "taken":
        row.status = STATUS_TAKEN
    elif action == "skipped":
        row.status = STATUS_SKIPPED
    else:
        return None

    row.action_time = datetime.utcnow()
    db.session.commit()
    return row


def remind_later(history_id, user_id, minutes):
    """
    'Remind Later' does not change the dose's original scheduled_time
    (so history stays accurate) - instead it creates a fresh reminder
    notification timed for now + minutes. The dose row itself stays
    Pending until the user takes/skips it or it is swept into Missed.
    """
    row = MedicineHistory.query.filter_by(id=history_id, user_id=user_id).first()
    if not row:
        return None

    medicine = Medicine.query.get(row.medicine_id)
    remind_at = datetime.now() + timedelta(minutes=minutes)
    dedupe_key = f"remind_later:{history_id}:{remind_at.strftime('%Y%m%d%H%M')}"

    create_notification(
        user_id=user_id,
        medicine_id=row.medicine_id,
        notification_type=TYPE_REMINDER,
        message=f"Reminder: take {medicine.name} (snoozed for {minutes} min).",
        dedupe_key=dedupe_key,
    )
    return row


def generate_due_reminders(user_id=None, tolerance_minutes=1):
    """
    Called periodically by the scheduler. Finds Pending doses whose
    scheduled time has just arrived (within tolerance_minutes of now) and
    creates a MEDICINE_REMINDER notification for each, if not already sent.
    """
    today = date.today()
    query = MedicineHistory.query.filter_by(date=today, status=STATUS_PENDING)
    if user_id:
        query = query.filter_by(user_id=user_id)
    rows = query.all()

    now = datetime.now()
    created = 0
    for row in rows:
        due_dt = datetime.combine(row.date, row.scheduled_time)
        delta = (now - due_dt).total_seconds() / 60
        if 0 <= delta <= tolerance_minutes:
            medicine = Medicine.query.get(row.medicine_id)
            if not medicine:
                continue
            dedupe_key = f"reminder:{row.id}"
            create_notification(
                user_id=row.user_id,
                medicine_id=row.medicine_id,
                notification_type=TYPE_REMINDER,
                message=f"Your scheduled dose of {medicine.name} ({row.scheduled_time.strftime('%I:%M %p')}) is due.",
                dedupe_key=dedupe_key,
            )
            created += 1
    return created


def sweep_missed_doses(user_id=None):
    """
    Called periodically by the scheduler. Any Pending dose whose scheduled
    time + reminder window has elapsed is marked Missed, and a
    MISSED_MEDICINE notification is created.
    """
    today = date.today()
    query = MedicineHistory.query.filter_by(date=today, status=STATUS_PENDING)
    if user_id:
        query = query.filter_by(user_id=user_id)
    rows = query.all()

    now = datetime.now()
    missed_count = 0
    for row in rows:
        schedule = MedicineSchedule.query.get(row.schedule_id) if row.schedule_id else None
        window = schedule.reminder_window if schedule else 60
        due_dt = datetime.combine(row.date, row.scheduled_time)
        elapsed_minutes = (now - due_dt).total_seconds() / 60

        if elapsed_minutes > window:
            row.status = STATUS_MISSED
            row.action_time = datetime.utcnow()
            medicine = Medicine.query.get(row.medicine_id)
            create_notification(
                user_id=row.user_id,
                medicine_id=row.medicine_id,
                notification_type=TYPE_MISSED,
                message=f"You missed your scheduled dose of {medicine.name} at {row.scheduled_time.strftime('%I:%M %p')}.",
                dedupe_key=f"missed:{row.id}",
            )
            missed_count += 1

    if missed_count:
        db.session.commit()
    return missed_count


def get_missed_today(user_id):
    today = date.today()
    sweep_missed_doses(user_id)
    return (
        MedicineHistory.query.filter_by(user_id=user_id, date=today, status=STATUS_MISSED)
        .order_by(MedicineHistory.scheduled_time.asc())
        .all()
    )
