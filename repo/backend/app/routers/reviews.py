from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.core.audit import write_audit_log
from app.core.auth import get_current_user
from app.core.database import get_db
from app.models.review import (
    IdentityMode,
    OutlierFlag,
    RecheckRequest,
    RecheckStatus,
    ReviewRound,
    ReviewRoundStatus,
    ReviewerAssignment,
    Score,
    ScoringForm,
)
from app.models.user import User, UserRole
from app.schemas.review import (
    AssignmentOut,
    AutoAssignmentIn,
    ManualAssignmentIn,
    OutlierOut,
    RecheckAssignIn,
    RecheckCreateIn,
    ReviewRoundCreate,
    ReviewRoundOut,
    ScoreOut,
    ScoreSubmitIn,
    ScoringFormCreate,
)
from app.services import review_service

router = APIRouter(prefix="/reviews", tags=["reviews"])


def _ensure_instructor_or_admin(user: User) -> None:
    if user.role not in {UserRole.instructor, UserRole.admin}:
        raise HTTPException(status_code=403, detail="Instructor or admin access required.")


@router.post("/forms")
def create_scoring_form(payload: ScoringFormCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _ensure_instructor_or_admin(user)
    form = ScoringForm(name=payload.name, criteria=payload.criteria)
    db.add(form)
    db.flush()
    write_audit_log(
        db,
        actor_id=user.id,
        action="review.form.create",
        entity_name="ScoringForm",
        entity_id=form.id,
        before=None,
        after={"id": form.id, "name": form.name},
    )
    db.commit()
    return {"id": form.id, "name": form.name}


@router.post("/rounds", response_model=ReviewRoundOut)
def create_round(payload: ReviewRoundCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _ensure_instructor_or_admin(user)
    mode = IdentityMode(payload.identity_mode)
    round_obj = ReviewRound(
        name=payload.name,
        term_id=payload.term_id,
        section_id=payload.section_id,
        scoring_form_id=payload.scoring_form_id,
        identity_mode=mode,
        status=ReviewRoundStatus.active,
        created_by=user.id,
    )
    db.add(round_obj)
    db.flush()
    write_audit_log(
        db,
        actor_id=user.id,
        action="review.round.create",
        entity_name="ReviewRound",
        entity_id=round_obj.id,
        before=None,
        after={"id": round_obj.id, "name": round_obj.name, "status": round_obj.status.value},
    )
    db.commit()
    return ReviewRoundOut(
        id=round_obj.id,
        name=round_obj.name,
        term_id=round_obj.term_id,
        section_id=round_obj.section_id,
        scoring_form_id=round_obj.scoring_form_id,
        identity_mode=round_obj.identity_mode.value,
        status=round_obj.status.value,
    )


@router.post("/rounds/{round_id}/assignments/manual", response_model=AssignmentOut)
def manual_assign(
    round_id: int,
    payload: ManualAssignmentIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _ensure_instructor_or_admin(user)
    round_obj = review_service._get_round(db, round_id)
    review_service._check_coi(db, round_obj, payload.reviewer_id, payload.student_id)
    assignment = ReviewerAssignment(
        round_id=round_id,
        reviewer_id=payload.reviewer_id,
        student_id=payload.student_id,
        section_id=round_obj.section_id,
        assigned_manually=True,
    )
    db.add(assignment)
    db.flush()
    db.commit()
    return AssignmentOut(
        id=assignment.id,
        round_id=assignment.round_id,
        reviewer_id=assignment.reviewer_id,
        student_id=assignment.student_id,
        section_id=assignment.section_id,
        assigned_manually=assignment.assigned_manually,
    )


@router.post("/rounds/{round_id}/assignments/auto")
def auto_assign(
    round_id: int,
    payload: AutoAssignmentIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _ensure_instructor_or_admin(user)
    round_obj = review_service._get_round(db, round_id)
    reviewers = db.query(User).filter(User.role == UserRole.reviewer, User.is_active.is_(True)).all()
    if not reviewers:
        raise HTTPException(status_code=422, detail="No active reviewers available.")

    created = 0
    pointer = 0
    for student_id in payload.student_ids:
        assigned_for_student = 0
        tried = 0
        while assigned_for_student < payload.reviewers_per_student and tried < len(reviewers) * 3:
            reviewer = reviewers[pointer % len(reviewers)]
            pointer += 1
            tried += 1
            try:
                review_service._check_coi(db, round_obj, reviewer.id, student_id)
            except HTTPException:
                continue
            exists = (
                db.query(ReviewerAssignment)
                .filter(ReviewerAssignment.round_id == round_id, ReviewerAssignment.reviewer_id == reviewer.id, ReviewerAssignment.student_id == student_id)
                .first()
            )
            if exists:
                continue
            db.add(
                ReviewerAssignment(
                    round_id=round_id,
                    reviewer_id=reviewer.id,
                    student_id=student_id,
                    section_id=round_obj.section_id,
                    assigned_manually=False,
                )
            )
            created += 1
            assigned_for_student += 1
    db.commit()
    return {"created_assignments": created}


@router.get("/rounds/{round_id}/assignments", response_model=list[AssignmentOut])
def list_assignments(round_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    round_obj = review_service._get_round(db, round_id)
    rows = db.query(ReviewerAssignment).filter(ReviewerAssignment.round_id == round_id).order_by(ReviewerAssignment.id.asc()).all()
    return [
        AssignmentOut(**review_service.mask_assignment_for_view(round_obj.identity_mode, row, user))
        for row in rows
    ]


@router.post("/scores", response_model=ScoreOut)
def submit_score(payload: ScoreSubmitIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    assignment = db.query(ReviewerAssignment).filter(ReviewerAssignment.id == payload.assignment_id).first()
    if assignment is None:
        raise HTTPException(status_code=404, detail="Assignment not found.")
    if user.role == UserRole.reviewer and assignment.reviewer_id != user.id:
        raise HTTPException(status_code=403, detail="Cannot submit score for unassigned work.")

    round_obj = review_service._get_round(db, assignment.round_id)
    if round_obj.status == ReviewRoundStatus.closed:
        raise HTTPException(status_code=409, detail="Round is closed.")
    form = db.query(ScoringForm).filter(ScoringForm.id == round_obj.scoring_form_id).first()
    if form is None:
        raise HTTPException(status_code=404, detail="Scoring form not found.")

    total = review_service._calculate_total_score(form, payload.criterion_scores)
    existing = db.query(Score).filter(Score.assignment_id == assignment.id).first()
    if existing:
        existing.criterion_scores = payload.criterion_scores
        existing.total_score = total
        existing.comment = payload.comment
        score = existing
    else:
        score = Score(
            assignment_id=assignment.id,
            criterion_scores=payload.criterion_scores,
            total_score=total,
            comment=payload.comment,
        )
        db.add(score)
        db.flush()

    review_service._evaluate_outliers(db, assignment.round_id, assignment.student_id)
    db.commit()
    db.refresh(score)
    return ScoreOut(id=score.id, assignment_id=score.assignment_id, total_score=score.total_score, submitted_at=score.submitted_at)


@router.get("/rounds/{round_id}/outliers", response_model=list[OutlierOut])
def list_outliers(round_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _ensure_instructor_or_admin(user)
    rows = db.query(OutlierFlag).filter(OutlierFlag.round_id == round_id).order_by(OutlierFlag.id.desc()).all()
    return [
        OutlierOut(
            id=row.id,
            round_id=row.round_id,
            student_id=row.student_id,
            score_id=row.score_id,
            median_score=row.median_score,
            deviation=row.deviation,
            resolved=row.resolved,
        )
        for row in rows
    ]


@router.post("/rounds/{round_id}/outliers/{flag_id}/resolve")
def resolve_outlier(round_id: int, flag_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _ensure_instructor_or_admin(user)
    flag = db.query(OutlierFlag).filter(OutlierFlag.round_id == round_id, OutlierFlag.id == flag_id).first()
    if flag is None:
        raise HTTPException(status_code=404, detail="Outlier flag not found.")
    flag.resolved = True
    db.commit()
    return {"message": "Resolved."}


@router.post("/rechecks")
def create_recheck(payload: RecheckCreateIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    request = RecheckRequest(
        round_id=payload.round_id,
        student_id=payload.student_id,
        section_id=payload.section_id,
        requested_by=user.id,
        reason=payload.reason,
        status=RecheckStatus.requested,
    )
    db.add(request)
    db.commit()
    db.refresh(request)
    return {"id": request.id, "status": request.status.value}


@router.post("/rechecks/{recheck_id}/assign")
def assign_recheck(
    recheck_id: int,
    payload: RecheckAssignIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _ensure_instructor_or_admin(user)
    request = db.query(RecheckRequest).filter(RecheckRequest.id == recheck_id).first()
    if request is None:
        raise HTTPException(status_code=404, detail="Recheck request not found.")
    round_obj = review_service._get_round(db, request.round_id)
    review_service._check_coi(db, round_obj, payload.reviewer_id, request.student_id)
    existing_assignment = (
        db.query(ReviewerAssignment)
        .filter(
            ReviewerAssignment.round_id == request.round_id,
            ReviewerAssignment.reviewer_id == payload.reviewer_id,
            ReviewerAssignment.student_id == request.student_id,
        )
        .first()
    )
    if existing_assignment is None:
        db.add(
            ReviewerAssignment(
                round_id=request.round_id,
                reviewer_id=payload.reviewer_id,
                student_id=request.student_id,
                section_id=request.section_id,
                assigned_manually=True,
            )
        )
    request.status = RecheckStatus.assigned
    request.assigned_reviewer_id = payload.reviewer_id
    db.commit()
    return {"message": "Assigned."}


@router.post("/rounds/{round_id}/close")
def close_round(round_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    _ensure_instructor_or_admin(user)
    round_obj = review_service._get_round(db, round_id)
    review_service.ensure_round_closable(db, round_obj)
    round_obj.status = ReviewRoundStatus.closed
    db.commit()
    return {"message": "Round closed."}


@router.get("/rounds/{round_id}/export")
def export_round(
    round_id: int,
    format: str = Query(default="json", pattern="^(json|csv)$"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _ensure_instructor_or_admin(user)
    content = review_service.export_round_scores(db, round_id, format)
    media = "application/json" if format == "json" else "text/csv"
    return PlainTextResponse(content=content, media_type=media)
