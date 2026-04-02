from datetime import datetime, timezone
import json

from fastapi import HTTPException
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.models.messaging import Notification, NotificationLog, NotificationTrigger


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _parse_trigger(trigger_type: str) -> NotificationTrigger:
    try:
        return NotificationTrigger(trigger_type)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Unsupported trigger type.") from exc


def dispatch_notifications(
    db: Session,
    *,
    trigger_type: str,
    title: str,
    message: str,
    recipient_ids: list[int],
    metadata: dict | None = None,
) -> dict:
    trigger = _parse_trigger(trigger_type)
    created_ids: list[int] = []

    for recipient_id in recipient_ids:
        notification = Notification(
            recipient_id=recipient_id,
            trigger_type=trigger,
            title=title,
            message=message,
            metadata_json=json.dumps(metadata, sort_keys=True, default=str) if metadata else None,
        )
        db.add(notification)
        db.flush()
        db.add(
            NotificationLog(
                notification_id=notification.id,
                recipient_id=recipient_id,
                event_type="DELIVERED",
                details=f"trigger={trigger.value}",
            )
        )
        created_ids.append(notification.id)

    db.commit()
    return {"created": len(created_ids), "notification_ids": created_ids}


def list_notifications(db: Session, recipient_id: int, limit: int = 50, offset: int = 0) -> tuple[int, list[Notification]]:
    unread_count = (
        db.query(func.count(Notification.id))
        .filter(Notification.recipient_id == recipient_id, Notification.read.is_(False))
        .scalar()
    )
    rows = (
        db.query(Notification)
        .filter(Notification.recipient_id == recipient_id)
        .order_by(desc(Notification.id))
        .offset(offset)
        .limit(limit)
        .all()
    )
    return int(unread_count or 0), rows


def mark_read(db: Session, notification_id: int, recipient_id: int) -> Notification:
    notification = (
        db.query(Notification)
        .filter(Notification.id == notification_id, Notification.recipient_id == recipient_id)
        .first()
    )
    if notification is None:
        raise HTTPException(status_code=404, detail="Notification not found.")
    if not notification.read:
        notification.read = True
        notification.read_at = _utcnow()
        db.add(
            NotificationLog(
                notification_id=notification.id,
                recipient_id=recipient_id,
                event_type="READ",
                details=None,
            )
        )
        db.commit()
        db.refresh(notification)
    return notification
