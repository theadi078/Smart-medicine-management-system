"""
Expiry monitoring service.

Checks every active medicine's expiry_date against configured thresholds
(30/7/1 days, and the expiry date itself) and generates de-duplicated
alerts. Designed to be called periodically by APScheduler, and also
safe to call synchronously (e.g. on dashboard load) since it is idempotent.
"""

from datetime import date
from models.medicine import Medicine
from services.notification_service import create_notification
from models.notification import TYPE_EXPIRY

EXPIRY_THRESHOLDS = [30, 7, 1]  # days-before-expiry alert points


def _dedupe_key(medicine_id, threshold_label):
    return f"expiry:{medicine_id}:{threshold_label}"


def check_expiry_for_medicine(medicine: Medicine):
    """Generate any due expiry alerts for a single medicine. Returns list of created/found notifications."""
    if not medicine.is_active:
        return []

    days_left = (medicine.expiry_date - date.today()).days
    created = []

    if days_left == 30:
        created.append(create_notification(
            user_id=medicine.user_id,
            medicine_id=medicine.id,
            notification_type=TYPE_EXPIRY,
            message=f"{medicine.name} will expire in 30 days.",
            dedupe_key=_dedupe_key(medicine.id, "30"),
        ))
    elif days_left == 7:
        created.append(create_notification(
            user_id=medicine.user_id,
            medicine_id=medicine.id,
            notification_type=TYPE_EXPIRY,
            message=f"{medicine.name} will expire in 7 days.",
            dedupe_key=_dedupe_key(medicine.id, "7"),
        ))
    elif days_left == 1:
        created.append(create_notification(
            user_id=medicine.user_id,
            medicine_id=medicine.id,
            notification_type=TYPE_EXPIRY,
            message=f"{medicine.name} will expire tomorrow.",
            dedupe_key=_dedupe_key(medicine.id, "1"),
        ))
    elif days_left == 0:
        created.append(create_notification(
            user_id=medicine.user_id,
            medicine_id=medicine.id,
            notification_type=TYPE_EXPIRY,
            message=f"{medicine.name} has reached its expiry date.",
            dedupe_key=_dedupe_key(medicine.id, "0"),
        ))

    return [c for c in created if c is not None]


def run_expiry_check_for_all():
    """Called by the scheduler (and safe to call ad-hoc) to sweep all active medicines."""
    medicines = Medicine.query.filter_by(is_active=True).all()
    total_created = 0
    for medicine in medicines:
        total_created += len(check_expiry_for_medicine(medicine))
    return total_created


def get_expiring_medicines(user_id, within_days=30):
    """Medicines expiring within N days (including already-expired), sorted soonest first."""
    medicines = Medicine.query.filter_by(user_id=user_id, is_active=True).all()
    result = [m for m in medicines if m.days_until_expiry <= within_days]
    result.sort(key=lambda m: m.days_until_expiry)
    return result


def get_expired_medicines(user_id):
    medicines = Medicine.query.filter_by(user_id=user_id, is_active=True).all()
    return sorted(
        [m for m in medicines if m.days_until_expiry < 0],
        key=lambda m: m.days_until_expiry,
    )
