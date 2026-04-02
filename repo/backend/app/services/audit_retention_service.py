from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.admin import AuditLog, AuditLogArchive


def run_archive_and_purge(db: Session, years: int = 7, batch_limit: int = 5000) -> tuple[int, int, datetime]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=365 * years)
    old_logs = (
        db.query(AuditLog)
        .filter(AuditLog.created_at < cutoff)
        .order_by(AuditLog.id.asc())
        .limit(batch_limit)
        .all()
    )
    if not old_logs:
        return 0, 0, cutoff

    archived_count = 0
    for row in old_logs:
        existing = db.query(AuditLogArchive.id).filter(AuditLogArchive.original_audit_id == row.id).first()
        if existing is not None:
            continue
        db.add(
            AuditLogArchive(
                original_audit_id=row.id,
                actor_id=row.actor_id,
                action=row.action,
                entity_name=row.entity_name,
                entity_id=row.entity_id,
                before_hash=row.before_hash,
                after_hash=row.after_hash,
                created_at=row.created_at,
                metadata_json=row.metadata_json,
            )
        )
        archived_count += 1

    db.flush()

    original_ids = [row.id for row in old_logs]
    archived_ids = {
        row[0]
        for row in db.query(AuditLogArchive.original_audit_id)
        .filter(AuditLogArchive.original_audit_id.in_(original_ids))
        .all()
    }
    if archived_ids:
        purged_count = (
            db.query(AuditLog)
            .filter(AuditLog.id.in_(list(archived_ids)))
            .delete(synchronize_session=False)
        )
    else:
        purged_count = 0

    return archived_count, purged_count, cutoff
