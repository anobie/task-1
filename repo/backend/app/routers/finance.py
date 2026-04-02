from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.audit import write_audit_log
from app.core.auth import get_current_user
from app.core.database import get_db
from app.models.user import User, UserRole
from app.schemas.finance import AccountSummaryOut, ArrearsItem, LedgerEntryOut, PaymentIn, ReconciliationImportOut, RefundIn
from app.services import finance_service

router = APIRouter(prefix="/finance", tags=["finance"])


def _ensure_finance_or_admin(user: User) -> None:
    if user.role not in {UserRole.finance_clerk, UserRole.admin}:
        raise HTTPException(status_code=403, detail="Finance clerk or admin access required.")


@router.get("/accounts/{student_id}", response_model=AccountSummaryOut)
def get_account(student_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _ensure_finance_or_admin(user)
    balance, entries = finance_service.get_account_summary(db, student_id)
    return AccountSummaryOut(
        student_id=student_id,
        balance=balance,
        entries=[
            LedgerEntryOut(
                id=e.id,
                entry_type=e.entry_type.value,
                amount=e.amount,
                instrument=e.instrument.value if e.instrument else None,
                reference_entry_id=e.reference_entry_id,
                description=e.description,
                entry_date=e.entry_date,
                created_at=e.created_at,
            )
            for e in entries
        ],
    )


@router.post("/payments", response_model=LedgerEntryOut)
def post_payment(payload: PaymentIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _ensure_finance_or_admin(user)
    entry = finance_service.record_payment(
        db,
        student_id=payload.student_id,
        amount=payload.amount,
        instrument=payload.instrument,
        description=payload.description,
        entry_date=payload.entry_date,
    )
    write_audit_log(
        db,
        actor_id=user.id,
        action="finance.payment.record",
        entity_name="LedgerEntry",
        entity_id=entry.id,
        before=None,
        after={"id": entry.id, "student_id": entry.student_id, "amount": entry.amount, "entry_type": entry.entry_type.value},
    )
    db.commit()
    return LedgerEntryOut(
        id=entry.id,
        entry_type=entry.entry_type.value,
        amount=entry.amount,
        instrument=entry.instrument.value if entry.instrument else None,
        reference_entry_id=entry.reference_entry_id,
        description=entry.description,
        entry_date=entry.entry_date,
        created_at=entry.created_at,
    )


@router.post("/refunds", response_model=LedgerEntryOut)
def post_refund(payload: RefundIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _ensure_finance_or_admin(user)
    entry = finance_service.record_refund(
        db,
        student_id=payload.student_id,
        amount=payload.amount,
        reference_entry_id=payload.reference_entry_id,
        description=payload.description,
        entry_date=payload.entry_date,
    )
    write_audit_log(
        db,
        actor_id=user.id,
        action="finance.refund.record",
        entity_name="LedgerEntry",
        entity_id=entry.id,
        before=None,
        after={"id": entry.id, "student_id": entry.student_id, "amount": entry.amount, "entry_type": entry.entry_type.value},
    )
    db.commit()
    return LedgerEntryOut(
        id=entry.id,
        entry_type=entry.entry_type.value,
        amount=entry.amount,
        instrument=entry.instrument.value if entry.instrument else None,
        reference_entry_id=entry.reference_entry_id,
        description=entry.description,
        entry_date=entry.entry_date,
        created_at=entry.created_at,
    )


@router.get("/arrears", response_model=list[ArrearsItem])
def get_arrears(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _ensure_finance_or_admin(user)
    rows = finance_service.arrears_with_late_fee(db)
    return [ArrearsItem(**row) for row in rows]


@router.post("/reconciliation/import", response_model=ReconciliationImportOut)
async def import_reconciliation(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _ensure_finance_or_admin(user)
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=422, detail="Only CSV files are supported.")
    content = await file.read()
    report = finance_service.import_reconciliation_csv(db, content.decode("utf-8"))
    write_audit_log(
        db,
        actor_id=user.id,
        action="finance.reconciliation.import",
        entity_name="ReconciliationReport",
        entity_id=report.id,
        before=None,
        after={"import_id": report.import_id, "matched_total": report.matched_total, "unmatched_total": report.unmatched_total},
    )
    db.commit()
    return ReconciliationImportOut(
        import_id=report.import_id,
        matched_total=report.matched_total,
        unmatched_total=report.unmatched_total,
    )


@router.get("/reconciliation/{import_id}/report", response_model=ReconciliationImportOut)
def get_reconciliation(import_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _ensure_finance_or_admin(user)
    report = finance_service.get_reconciliation_report(db, import_id)
    return ReconciliationImportOut(import_id=report.import_id, matched_total=report.matched_total, unmatched_total=report.unmatched_total)
