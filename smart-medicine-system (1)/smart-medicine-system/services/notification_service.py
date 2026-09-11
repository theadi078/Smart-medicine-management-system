"""
Centralized notification creation. All other services (reminders, expiry)
funnel through here so notification logic (dedupe, persistence) lives in
one place, per:

    Scheduler -> check schedules/expiry -> generate notification
    -> save to DB -> displayed in UI
"""

from models import db
from models.notification import (
    Notification,
    TYPE_REMINDER,
    TYPE_EXPIRY,
    TYPE_MISSED,
    TYPE_SYSTEM,
)


def create_notification(user_id, message, notification_type=TYPE_SYSTEM,
                         medicine_id=None, dedupe_key=None):
    """
    Create a notification, avoiding duplicates when dedupe_key is provided
    and a notification with that key already exists for this user.
    """
    if dedupe_key:
        existing = Notification.query.filter_by(
            user_id=user_id, dedupe_key=dedupe_key
        ).first()
        if existing:
            return existing  # already notified - do not duplicate

    notification = Notification(
        user_id=user_id,
        medicine_id=medicine_id,
        notification_type=notification_type,
        message=message,
        dedupe_key=dedupe_key,
    )
    db.session.add(notification)
    db.session.commit()
    return notification


def get_unread_count(user_id):
    return Notification.query.filter_by(user_id=user_id, is_read=False).count()


def mark_as_read(notification_id, user_id):
    notif = Notification.query.filter_by(id=notification_id, user_id=user_id).first()
    if notif:
        notif.is_read = True
        db.session.commit()
    return notif


def mark_all_as_read(user_id):
    Notification.query.filter_by(user_id=user_id, is_read=False).update({"is_read": True})
    db.session.commit()


def get_user_notifications(user_id, category=None, limit=100):
    query = Notification.query.filter_by(user_id=user_id)
    if category:
        query = query.filter_by(notification_type=category)
    return query.order_by(Notification.created_at.desc()).limit(limit).all()
