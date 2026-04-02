from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.admin import Course, Organization, Section, Term
from app.models.user import User, UserRole


def _create_user(db: Session, username: str, role: UserRole, password: str) -> User:
    user = User(username=username, password_hash=hash_password(password), role=role, is_active=True)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _login(client, username: str, password: str) -> dict[str, str]:
    response = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['token']}"}


def _seed_round_context(db: Session) -> tuple[int, int]:
    organization = Organization(name="Review Org", code="RORG", is_active=True)
    db.add(organization)
    db.flush()
    term = Term(organization_id=organization.id, name="Spring 2027", starts_on="2027-01-10", ends_on="2027-05-10", is_active=True)
    db.add(term)
    db.flush()
    course = Course(organization_id=organization.id, code="RVW100", title="Review Course", credits=3, prerequisites=[])
    db.add(course)
    db.flush()
    section = Section(course_id=course.id, term_id=term.id, code="R1", instructor_id=None, capacity=40)
    db.add(section)
    db.commit()
    return term.id, section.id


def test_review_round_end_to_end(client, db_session: Session) -> None:
    instructor = _create_user(db_session, "inst1", UserRole.instructor, "InstructorPass1!")
    reviewer_1 = _create_user(db_session, "rev1", UserRole.reviewer, "ReviewerPass1!")
    reviewer_2 = _create_user(db_session, "rev2", UserRole.reviewer, "ReviewerPass1!")
    student = _create_user(db_session, "student1", UserRole.student, "StudentPass1!")
    term_id, section_id = _seed_round_context(db_session)

    instructor_headers = _login(client, "inst1", "InstructorPass1!")
    reviewer_headers = _login(client, "rev1", "ReviewerPass1!")

    form = client.post(
        "/api/v1/reviews/forms",
        json={
            "name": "Default Form",
            "criteria": [
                {"name": "Quality", "weight": 0.5, "min": 0, "max": 5},
                {"name": "Completeness", "weight": 0.5, "min": 0, "max": 5},
            ],
        },
        headers=instructor_headers,
    )
    assert form.status_code == 200
    form_id = form.json()["id"]

    round_response = client.post(
        "/api/v1/reviews/rounds",
        json={
            "name": "Round 1",
            "term_id": term_id,
            "section_id": section_id,
            "scoring_form_id": form_id,
            "identity_mode": "BLIND",
        },
        headers=instructor_headers,
    )
    assert round_response.status_code == 200
    round_id = round_response.json()["id"]

    manual_1 = client.post(
        f"/api/v1/reviews/rounds/{round_id}/assignments/manual",
        json={"reviewer_id": reviewer_1.id, "student_id": student.id},
        headers=instructor_headers,
    )
    assert manual_1.status_code == 200

    manual_2 = client.post(
        f"/api/v1/reviews/rounds/{round_id}/assignments/manual",
        json={"reviewer_id": reviewer_2.id, "student_id": student.id},
        headers=instructor_headers,
    )
    assert manual_2.status_code == 200

    assignments_for_reviewer = client.get(f"/api/v1/reviews/rounds/{round_id}/assignments", headers=reviewer_headers)
    assert assignments_for_reviewer.status_code == 200
    assert assignments_for_reviewer.json()[0]["student_id"] is None

    score_1 = client.post(
        "/api/v1/reviews/scores",
        json={"assignment_id": manual_1.json()["id"], "criterion_scores": {"Quality": 5, "Completeness": 5}, "comment": "Strong"},
        headers=reviewer_headers,
    )
    assert score_1.status_code == 200

    reviewer_2_headers = _login(client, "rev2", "ReviewerPass1!")
    score_2 = client.post(
        "/api/v1/reviews/scores",
        json={"assignment_id": manual_2.json()["id"], "criterion_scores": {"Quality": 1, "Completeness": 1}, "comment": "Weak"},
        headers=reviewer_2_headers,
    )
    assert score_2.status_code == 200

    outliers = client.get(f"/api/v1/reviews/rounds/{round_id}/outliers", headers=instructor_headers)
    assert outliers.status_code == 200
    assert len(outliers.json()) >= 1

    blocked_close = client.post(f"/api/v1/reviews/rounds/{round_id}/close", headers=instructor_headers)
    assert blocked_close.status_code == 409

    for flag in outliers.json():
        resolve = client.post(f"/api/v1/reviews/rounds/{round_id}/outliers/{flag['id']}/resolve", headers=instructor_headers)
        assert resolve.status_code == 200

    close = client.post(f"/api/v1/reviews/rounds/{round_id}/close", headers=instructor_headers)
    assert close.status_code == 200

    export_json = client.get(f"/api/v1/reviews/rounds/{round_id}/export?format=json", headers=instructor_headers)
    assert export_json.status_code == 200

    export_csv = client.get(f"/api/v1/reviews/rounds/{round_id}/export?format=csv", headers=instructor_headers)
    assert export_csv.status_code == 200


def test_recheck_and_auto_assignment_and_rbac(client, db_session: Session) -> None:
    instructor = _create_user(db_session, "inst2", UserRole.instructor, "InstructorPass1!")
    reviewer = _create_user(db_session, "rev3", UserRole.reviewer, "ReviewerPass1!")
    student = _create_user(db_session, "student2", UserRole.student, "StudentPass1!")
    term_id, section_id = _seed_round_context(db_session)

    instructor_headers = _login(client, "inst2", "InstructorPass1!")
    student_headers = _login(client, "student2", "StudentPass1!")

    form = client.post(
        "/api/v1/reviews/forms",
        json={"name": "Form2", "criteria": [{"name": "Q", "weight": 1, "min": 0, "max": 5}]},
        headers=instructor_headers,
    )
    round_response = client.post(
        "/api/v1/reviews/rounds",
        json={"name": "Round 2", "term_id": term_id, "section_id": section_id, "scoring_form_id": form.json()["id"], "identity_mode": "OPEN"},
        headers=instructor_headers,
    )
    round_id = round_response.json()["id"]

    auto_assign = client.post(
        f"/api/v1/reviews/rounds/{round_id}/assignments/auto",
        json={"student_ids": [student.id], "reviewers_per_student": 1},
        headers=instructor_headers,
    )
    assert auto_assign.status_code == 200

    recheck = client.post(
        "/api/v1/reviews/rechecks",
        json={"round_id": round_id, "student_id": student.id, "section_id": section_id, "reason": "Please verify score"},
        headers=student_headers,
    )
    assert recheck.status_code == 200

    assign = client.post(
        f"/api/v1/reviews/rechecks/{recheck.json()['id']}/assign",
        json={"reviewer_id": reviewer.id},
        headers=instructor_headers,
    )
    assert assign.status_code == 200

    rbac_denied = client.post(
        "/api/v1/reviews/forms",
        json={"name": "Denied", "criteria": [{"name": "Q", "weight": 1, "min": 0, "max": 5}]},
        headers=student_headers,
    )
    assert rbac_denied.status_code == 403
