from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.audit import write_audit_log
from app.core.auth import get_current_user
from app.core.database import get_db
from app.models.user import User, UserRole
from app.schemas.data_quality import QualityReportOut, QuarantineOut, ResolveIn, ValidateWriteIn, ValidateWriteOut
from app.services import data_quality_service

router = APIRouter(prefix="/data-quality", tags=["data-quality"])


def _ensure_admin(user: User) -> None:
    if user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Admin access required")


@router.post("/validate-write", response_model=ValidateWriteOut, status_code=202)
def validate_write(payload: ValidateWriteIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if user.role not in {UserRole.admin, UserRole.instructor, UserRole.finance_clerk}:
        raise HTTPException(status_code=403, detail="Forbidden")

    accepted, score, reasons, fingerprint = data_quality_service.evaluate_payload(
        db,
        entity_type=payload.entity_type,
        payload=payload.payload,
        required_fields=payload.required_fields,
        ranges=payload.ranges,
        unique_keys=payload.unique_keys,
    )

    if accepted:
        return ValidateWriteOut(accepted=True, quality_score=score, reasons=[], quarantine_id=None)

    entry = data_quality_service.quarantine_write(
        db,
        entity_type=payload.entity_type,
        payload=payload.payload,
        reasons=reasons,
        quality_score=score,
        fingerprint=fingerprint,
    )
    write_audit_log(
        db,
        actor_id=user.id,
        action="data_quality.quarantine",
        entity_name="QuarantineEntry",
        entity_id=entry.id,
        before=None,
        after={"id": entry.id, "entity_type": entry.entity_type, "quality_score": entry.quality_score},
    )
    db.commit()
    return ValidateWriteOut(accepted=False, quality_score=score, reasons=reasons, quarantine_id=entry.id)


@router.get("/quarantine", response_model=list[QuarantineOut])
def list_quarantine(
    status: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _ensure_admin(user)
    rows = data_quality_service.list_quarantine(db, status=status, limit=limit, offset=offset)
    return [
        QuarantineOut(
            id=row.id,
            entity_type=row.entity_type,
            rejection_reason=row.rejection_reason,
            quality_score=row.quality_score,
            status=row.status.value,
            created_at=row.created_at,
            resolved_at=row.resolved_at,
        )
        for row in rows
    ]


@router.patch("/quarantine/{entry_id}/resolve", response_model=QuarantineOut)
def resolve_quarantine(entry_id: int, payload: ResolveIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _ensure_admin(user)
    row = data_quality_service.resolve_quarantine(db, entry_id, payload.action, user.id)
    write_audit_log(
        db,
        actor_id=user.id,
        action="data_quality.resolve",
        entity_name="QuarantineEntry",
        entity_id=row.id,
        before=None,
        after={"id": row.id, "status": row.status.value},
    )
    db.commit()
    return QuarantineOut(
        id=row.id,
        entity_type=row.entity_type,
        rejection_reason=row.rejection_reason,
        quality_score=row.quality_score,
        status=row.status.value,
        created_at=row.created_at,
        resolved_at=row.resolved_at,
    )


@router.get("/report", response_model=list[QualityReportOut])
def get_report(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _ensure_admin(user)
    rows = data_quality_service.quality_report(db)
    return [QualityReportOut(**row) for row in rows]
