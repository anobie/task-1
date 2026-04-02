from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.access import ScopeGrant, ScopeType
from app.models.admin import Course, Section
from app.models.user import User, UserRole


def has_scope_grant(db: Session, user_id: int, scope_type: ScopeType, scope_id: int) -> bool:
    grant = (
        db.query(ScopeGrant)
        .filter(ScopeGrant.user_id == user_id, ScopeGrant.scope_type == scope_type, ScopeGrant.scope_id == scope_id)
        .first()
    )
    return grant is not None


def _section_org_id(db: Session, section_id: int) -> int | None:
    row = (
        db.query(Course.organization_id)
        .join(Section, Section.course_id == Course.id)
        .filter(Section.id == section_id)
        .first()
    )
    if row is None:
        return None
    return int(row[0])


def can_access_section(db: Session, user: User, section_id: int) -> bool:
    if user.role == UserRole.admin:
        return True
    if has_scope_grant(db, user.id, ScopeType.section, section_id):
        return True

    org_id = _section_org_id(db, section_id)
    if org_id is None:
        return False
    if user.org_id is not None and user.org_id == org_id:
        return True
    if has_scope_grant(db, user.id, ScopeType.organization, org_id):
        return True
    return False


def require_section_access(db: Session, user: User, section_id: int) -> None:
    if not can_access_section(db, user, section_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied for requested section.")


def can_access_student(db: Session, user: User, student_id: int) -> bool:
    if user.role == UserRole.admin:
        return True
    student = db.query(User).filter(User.id == student_id).first()
    if student is None or student.org_id is None:
        return False
    return has_scope_grant(db, user.id, ScopeType.organization, student.org_id)


def require_student_access(db: Session, user: User, student_id: int) -> None:
    if not can_access_student(db, user, student_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied for requested student account.")
