from datetime import datetime, timezone
import csv
import hashlib
import io
from statistics import median

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.admin import Section
from app.models.registration import Enrollment, EnrollmentStatus
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


def _get_round(db: Session, round_id: int) -> ReviewRound:
    round_obj = db.query(ReviewRound).filter(ReviewRound.id == round_id).first()
    if round_obj is None:
        raise HTTPException(status_code=404, detail="Review round not found.")
    return round_obj


def _is_reporting_line_conflict(reviewer: User, student: User) -> bool:
    return reviewer.reports_to == student.id or student.reports_to == reviewer.id


def _check_coi(db: Session, round_obj: ReviewRound, reviewer_id: int, student_id: int) -> None:
    reviewer = db.query(User).filter(User.id == reviewer_id).first()
    student = db.query(User).filter(User.id == student_id).first()
    if reviewer is None or student is None:
        raise HTTPException(status_code=404, detail="Reviewer or student not found.")
    section = db.query(Section).filter(Section.id == round_obj.section_id).first()
    if section and section.instructor_id == reviewer_id:
        raise HTTPException(status_code=409, detail="Conflict of interest: same section instructor.")
    if _is_reporting_line_conflict(reviewer, student):
        raise HTTPException(status_code=409, detail="Conflict of interest: reporting line conflict.")
    if reviewer_id == student_id:
        raise HTTPException(status_code=409, detail="Conflict of interest: self review is not allowed.")
    same_section_enrollment = (
        db.query(Enrollment.id)
        .filter(
            Enrollment.section_id == round_obj.section_id,
            Enrollment.student_id.in_([reviewer_id, student_id]),
            Enrollment.status.in_([EnrollmentStatus.enrolled, EnrollmentStatus.completed]),
        )
        .count()
    )
    if same_section_enrollment >= 2:
        raise HTTPException(status_code=409, detail="Conflict of interest: reviewer and student are in the same section.")


def _calculate_total_score(form: ScoringForm, criterion_scores: dict[str, float]) -> float:
    criteria = form.criteria or []
    if not criteria:
        raise HTTPException(status_code=422, detail="Scoring form has no criteria.")
    total_weight = sum(float(item.get("weight", 0)) for item in criteria)
    if total_weight <= 0:
        raise HTTPException(status_code=422, detail="Scoring form weights must be positive.")

    aggregate = 0.0
    for item in criteria:
        name = item.get("name")
        weight = float(item.get("weight", 0))
        min_value = float(item.get("min", 0))
        max_value = float(item.get("max", 5))
        if name not in criterion_scores:
            raise HTTPException(status_code=422, detail=f"Missing criterion score: {name}")
        value = float(criterion_scores[name])
        if value < min_value or value > max_value:
            raise HTTPException(status_code=422, detail=f"Score out of range for criterion: {name}")
        aggregate += value * weight

    return round(aggregate / total_weight, 4)


def _evaluate_outliers(db: Session, round_id: int, student_id: int) -> None:
    score_rows = (
        db.query(Score)
        .join(ReviewerAssignment, Score.assignment_id == ReviewerAssignment.id)
        .filter(ReviewerAssignment.round_id == round_id, ReviewerAssignment.student_id == student_id)
        .all()
    )
    if len(score_rows) < 2:
        return
    totals = [row.total_score for row in score_rows]
    med = float(median(totals))
    for score_row in score_rows:
        deviation = abs(score_row.total_score - med)
        if deviation >= 2.0:
            exists = db.query(OutlierFlag).filter(OutlierFlag.score_id == score_row.id, OutlierFlag.resolved.is_(False)).first()
            if exists is None:
                db.add(
                    OutlierFlag(
                        round_id=round_id,
                        student_id=student_id,
                        score_id=score_row.id,
                        median_score=med,
                        deviation=deviation,
                        resolved=False,
                    )
                )


def mask_assignment_for_view(mode: IdentityMode, assignment: ReviewerAssignment, requester: User) -> dict:
    student_id = assignment.student_id
    student_ref = None
    if requester.role == UserRole.reviewer:
        if mode == IdentityMode.blind:
            student_id = None
        elif mode == IdentityMode.semi_blind:
            student_id = None
            canonical = f"{assignment.round_id}:{assignment.student_id}:{settings.secret_key}"
            student_ref = f"SR-{hashlib.sha256(canonical.encode('utf-8')).hexdigest()[:8].upper()}"
    return {
        "id": assignment.id,
        "round_id": assignment.round_id,
        "reviewer_id": assignment.reviewer_id,
        "student_id": student_id,
        "student_ref": student_ref,
        "section_id": assignment.section_id,
        "assigned_manually": assignment.assigned_manually,
    }


def export_round_scores(db: Session, round_id: int, export_format: str) -> str:
    rows = (
        db.query(Score, ReviewerAssignment)
        .join(ReviewerAssignment, Score.assignment_id == ReviewerAssignment.id)
        .filter(ReviewerAssignment.round_id == round_id)
        .all()
    )
    payload = [
        {
            "score_id": score.id,
            "assignment_id": assignment.id,
            "reviewer_id": assignment.reviewer_id,
            "student_id": assignment.student_id,
            "total_score": score.total_score,
            "submitted_at": score.submitted_at.isoformat() if score.submitted_at else None,
            "criterion_scores": score.criterion_scores,
            "comment": score.comment,
        }
        for score, assignment in rows
    ]
    if export_format == "json":
        import json

        return json.dumps(payload, default=str)
    if export_format == "csv":
        buf = io.StringIO()
        writer = csv.DictWriter(
            buf,
            fieldnames=["score_id", "assignment_id", "reviewer_id", "student_id", "total_score", "submitted_at", "comment"],
        )
        writer.writeheader()
        for item in payload:
            writer.writerow({k: item[k] for k in writer.fieldnames})
        return buf.getvalue()
    raise HTTPException(status_code=422, detail="Unsupported export format.")


def ensure_round_closable(db: Session, round_obj: ReviewRound) -> None:
    unresolved = db.query(OutlierFlag).filter(OutlierFlag.round_id == round_obj.id, OutlierFlag.resolved.is_(False)).count()
    if unresolved > 0:
        raise HTTPException(status_code=409, detail="Cannot close round with unresolved outlier flags.")


def now_utc() -> datetime:
    return datetime.now(timezone.utc)
