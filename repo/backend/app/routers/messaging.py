from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.audit import write_audit_log
from app.core.auth import get_current_user
from app.core.database import get_db
from app.models.user import User, UserRole
from app.schemas.messaging import NotificationListOut, NotificationOut, TriggerDispatchIn
from app.services import messaging_service

router = APIRouter(prefix="/messaging", tags=["messaging"])


def _can_dispatch(user: User) -> bool:
    return user.role in {UserRole.admin, UserRole.instructor, UserRole.finance_clerk}


@router.post("/dispatch")
def dispatch(payload: TriggerDispatchIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if not _can_dispatch(user):
        raise HTTPException(status_code=403, detail="Forbidden")
    result = messaging_service.dispatch_notifications(
        db,
        trigger_type=payload.trigger_type,
        title=payload.title,
        message=payload.message,
        recipient_ids=payload.recipient_ids,
        metadata=payload.metadata,
    )
    write_audit_log(
        db,
        actor_id=user.id,
        action="messaging.dispatch",
        entity_name="Notification",
        entity_id=None,
        before=None,
        after={"trigger_type": payload.trigger_type, "created": result["created"]},
        metadata={"recipient_ids": payload.recipient_ids},
    )
    db.commit()
    return result


@router.get("/notifications", response_model=NotificationListOut)
def list_notifications(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    unread_count, rows = messaging_service.list_notifications(db, user.id, limit=limit, offset=offset)
    return NotificationListOut(
        unread_count=unread_count,
        notifications=[
            NotificationOut(
                id=row.id,
                trigger_type=row.trigger_type.value,
                title=row.title,
                message=row.message,
                read=row.read,
                delivered_at=row.delivered_at,
                read_at=row.read_at,
            )
            for row in rows
        ],
    )


@router.patch("/notifications/{notification_id}/read", response_model=NotificationOut)
def mark_notification_read(notification_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    row = messaging_service.mark_read(db, notification_id, user.id)
    return NotificationOut(
        id=row.id,
        trigger_type=row.trigger_type.value,
        title=row.title,
        message=row.message,
        read=row.read,
        delivered_at=row.delivered_at,
        read_at=row.read_at,
    )
