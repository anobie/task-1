from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.access import ScopeGrant, ScopeType
from app.models.admin import Course, Organization, RegistrationRound, Section, Term
from app.models.registration import AddDropRequest, Enrollment, EnrollmentStatus
from app.models.user import User, UserRole


def _create_user(db: Session, username: str, role: UserRole, password: str, org_id: int | None = None) -> User:
    user = User(username=username, password_hash=hash_password(password), role=role, is_active=True, org_id=org_id)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _login(client, username: str, password: str) -> dict[str, str]:
    response = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['token']}"}


def _seed_catalog(db: Session, with_active_round: bool = True, org_code: str = "ORG1") -> tuple[int, int, int, int, int]:
    organization = Organization(name=f"Org {org_code}", code=org_code, is_active=True)
    db.add(organization)
    db.flush()
    term = Term(organization_id=organization.id, name="Fall 2026", starts_on="2026-09-01", ends_on="2026-12-20", is_active=True)
    db.add(term)
    db.flush()
    prereq_course = Course(organization_id=organization.id, code="MATH100", title="Math", credits=3, prerequisites=[])
    target_course = Course(organization_id=organization.id, code="CS200", title="Systems", credits=3, prerequisites=["MATH100"])
    db.add(prereq_course)
    db.add(target_course)
    db.flush()
    prereq_section = Section(course_id=prereq_course.id, term_id=term.id, code="P1", instructor_id=None, capacity=30)
    target_section = Section(course_id=target_course.id, term_id=term.id, code="S1", instructor_id=None, capacity=1)
    db.add(prereq_section)
    db.add(target_section)
    if with_active_round:
        db.add(
            RegistrationRound(
                term_id=term.id,
                name="Primary",
                starts_at=datetime.now(timezone.utc) - timedelta(hours=1),
                ends_at=datetime.now(timezone.utc) + timedelta(hours=3),
                is_active=True,
            )
        )
    db.commit()
    return organization.id, prereq_course.id, target_course.id, prereq_section.id, target_section.id


def _grant_org_scope(db: Session, user_id: int, org_id: int) -> None:
    db.add(ScopeGrant(user_id=user_id, scope_type=ScopeType.organization, scope_id=org_id))
    db.commit()


def test_course_discovery_and_eligibility(client, db_session: Session) -> None:
    org_id, _, target_course_id, prereq_section_id, target_section_id = _seed_catalog(db_session)
    student = _create_user(db_session, "stu1", UserRole.student, "StudentPass123!", org_id=org_id)
    db_session.add(Enrollment(student_id=student.id, section_id=prereq_section_id, status=EnrollmentStatus.completed))
    db_session.commit()

    headers = _login(client, "stu1", "StudentPass123!")
    courses = client.get("/api/v1/courses", headers=headers)
    assert courses.status_code == 200
    assert len(courses.json()) >= 1

    detail = client.get(f"/api/v1/courses/{target_course_id}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["code"] == "CS200"

    eligibility = client.get(f"/api/v1/courses/{target_course_id}/sections/{target_section_id}/eligibility", headers=headers)
    assert eligibility.status_code == 200
    assert eligibility.json()["eligible"] is True


def test_enroll_idempotency_and_conflict(client, db_session: Session) -> None:
    org_id, _, target_course_id, prereq_section_id, target_section_id = _seed_catalog(db_session)
    student = _create_user(db_session, "stu2", UserRole.student, "StudentPass123!", org_id=org_id)
    db_session.add(Enrollment(student_id=student.id, section_id=prereq_section_id, status=EnrollmentStatus.completed))
    db_session.commit()

    headers = _login(client, "stu2", "StudentPass123!")
    enroll_headers = {**headers, "Idempotency-Key": "enroll-key-1"}
    first = client.post("/api/v1/registration/enroll", json={"section_id": target_section_id}, headers=enroll_headers)
    assert first.status_code == 200
    assert first.json()["status"] in {"enrolled", "already_enrolled"}

    replay = client.post("/api/v1/registration/enroll", json={"section_id": target_section_id}, headers=enroll_headers)
    assert replay.status_code == 200
    assert replay.json() == first.json()

    bad_reuse = client.post("/api/v1/registration/enroll", json={"section_id": target_section_id + 999}, headers=enroll_headers)
    assert bad_reuse.status_code == 403

    another_student = _create_user(db_session, "stu3", UserRole.student, "StudentPass123!", org_id=org_id)
    db_session.add(Enrollment(student_id=another_student.id, section_id=prereq_section_id, status=EnrollmentStatus.completed))
    db_session.commit()
    headers_2 = _login(client, "stu3", "StudentPass123!")
    full = client.post(
        "/api/v1/registration/enroll",
        json={"section_id": target_section_id},
        headers={**headers_2, "Idempotency-Key": "enroll-key-2"},
    )
    assert full.status_code == 409


def test_waitlist_drop_backfill_status_history(client, db_session: Session) -> None:
    org_id, _, _, prereq_section_id, target_section_id = _seed_catalog(db_session)
    student_a = _create_user(db_session, "stu4", UserRole.student, "StudentPass123!", org_id=org_id)
    student_b = _create_user(db_session, "stu5", UserRole.student, "StudentPass123!", org_id=org_id)
    db_session.add(Enrollment(student_id=student_a.id, section_id=prereq_section_id, status=EnrollmentStatus.completed))
    db_session.add(Enrollment(student_id=student_b.id, section_id=prereq_section_id, status=EnrollmentStatus.completed))
    db_session.commit()

    headers_a = _login(client, "stu4", "StudentPass123!")
    headers_b = _login(client, "stu5", "StudentPass123!")

    enroll_a = client.post(
        "/api/v1/registration/enroll",
        json={"section_id": target_section_id},
        headers={**headers_a, "Idempotency-Key": "drop-path-a"},
    )
    assert enroll_a.status_code == 200

    wait_b = client.post("/api/v1/registration/waitlist", json={"section_id": target_section_id}, headers=headers_b)
    assert wait_b.status_code == 200
    assert wait_b.json()["status"] in {"waitlisted", "already_waitlisted"}

    db_session.commit()
    drop_a = client.post(
        "/api/v1/registration/drop",
        json={"section_id": target_section_id},
        headers={**headers_a, "Idempotency-Key": "drop-key-a"},
    )
    assert drop_a.status_code == 200
    db_session.expire_all()

    status_b = client.get("/api/v1/registration/status", headers=headers_b)
    assert status_b.status_code == 200
    assert any(item["section_id"] == target_section_id and item["status"] == "ENROLLED" for item in status_b.json())

    history_b = client.get("/api/v1/registration/history", headers=headers_b)
    assert history_b.status_code == 200
    assert len(history_b.json()) > 0


def test_idempotency_key_expires_after_24h(client, db_session: Session) -> None:
    org_id, _, _, prereq_section_id, target_section_id = _seed_catalog(db_session)
    student_a = _create_user(db_session, "stu_idm_a", UserRole.student, "StudentPass123!", org_id=org_id)
    student_b = _create_user(db_session, "stu_idm_b", UserRole.student, "StudentPass123!", org_id=org_id)
    db_session.add(Enrollment(student_id=student_a.id, section_id=prereq_section_id, status=EnrollmentStatus.completed))
    db_session.add(Enrollment(student_id=student_b.id, section_id=prereq_section_id, status=EnrollmentStatus.completed))
    db_session.commit()

    headers_a = _login(client, "stu_idm_a", "StudentPass123!")
    headers_b = _login(client, "stu_idm_b", "StudentPass123!")

    first_enroll = client.post(
        "/api/v1/registration/enroll",
        json={"section_id": target_section_id},
        headers={**headers_a, "Idempotency-Key": "seat-holder"},
    )
    assert first_enroll.status_code == 200

    key = "window-key"
    full_attempt = client.post(
        "/api/v1/registration/enroll",
        json={"section_id": target_section_id},
        headers={**headers_b, "Idempotency-Key": key},
    )
    assert full_attempt.status_code == 409

    stored = (
        db_session.query(AddDropRequest)
        .filter(
            AddDropRequest.actor_id == student_b.id,
            AddDropRequest.operation == "ENROLL",
            AddDropRequest.idempotency_key == key,
        )
        .first()
    )
    assert stored is not None
    stored.created_at = datetime.now(timezone.utc) - timedelta(hours=25)
    db_session.commit()

    drop_holder = client.post(
        "/api/v1/registration/drop",
        json={"section_id": target_section_id},
        headers={**headers_a, "Idempotency-Key": "drop-seat-holder"},
    )
    assert drop_holder.status_code == 200

    reused_after_window = client.post(
        "/api/v1/registration/enroll",
        json={"section_id": target_section_id},
        headers={**headers_b, "Idempotency-Key": key},
    )
    assert reused_after_window.status_code == 200
    assert reused_after_window.json()["status"] == "enrolled"


def test_eligibility_missing_prereq_and_missing_idempotency(client, db_session: Session) -> None:
    org_id, _, target_course_id, _, target_section_id = _seed_catalog(db_session)
    _create_user(db_session, "stu6", UserRole.student, "StudentPass123!", org_id=org_id)
    headers = _login(client, "stu6", "StudentPass123!")

    eligibility = client.get(f"/api/v1/courses/{target_course_id}/sections/{target_section_id}/eligibility", headers=headers)
    assert eligibility.status_code == 200
    assert eligibility.json()["eligible"] is False

    enroll_missing_header = client.post("/api/v1/registration/enroll", json={"section_id": target_section_id}, headers=headers)
    assert enroll_missing_header.status_code == 400


def test_course_discovery_requires_auth(client, db_session: Session) -> None:
    _, _, target_course_id, _, _ = _seed_catalog(db_session, org_code="ORGAUTH")
    courses = client.get("/api/v1/courses")
    assert courses.status_code == 401
    details = client.get(f"/api/v1/courses/{target_course_id}")
    assert details.status_code == 401


def test_registration_writes_forbidden_for_non_student_roles(client, db_session: Session) -> None:
    org_id, _, _, _, target_section_id = _seed_catalog(db_session, org_code="ORGROLE")

    actor_specs = [
        ("reg_admin", UserRole.admin, "AdminPass123!"),
        ("reg_instructor", UserRole.instructor, "InstructorPass123!"),
        ("reg_finance", UserRole.finance_clerk, "FinancePass123!"),
    ]

    for username, role, password in actor_specs:
        _create_user(db_session, username, role, password, org_id=org_id)
        headers = _login(client, username, password)

        enroll_response = client.post(
            "/api/v1/registration/enroll",
            json={"section_id": target_section_id},
            headers={**headers, "Idempotency-Key": f"enroll-{role.value}"},
        )
        assert enroll_response.status_code == 403

        waitlist_response = client.post(
            "/api/v1/registration/waitlist",
            json={"section_id": target_section_id},
            headers=headers,
        )
        assert waitlist_response.status_code == 403

        drop_response = client.post(
            "/api/v1/registration/drop",
            json={"section_id": target_section_id},
            headers={**headers, "Idempotency-Key": f"drop-{role.value}"},
        )
        assert drop_response.status_code == 403


def test_registration_scope_denies_cross_org_enrollment(client, db_session: Session) -> None:
    org1_id, _, _, prereq_section_id, target_section_id = _seed_catalog(db_session, org_code="ORG-A")
    org2_id, _, _, _, _ = _seed_catalog(db_session, org_code="ORG-B")
    student = _create_user(db_session, "scope_stu", UserRole.student, "StudentPass123!", org_id=org2_id)
    db_session.add(Enrollment(student_id=student.id, section_id=prereq_section_id, status=EnrollmentStatus.completed))
    db_session.commit()

    headers = _login(client, "scope_stu", "StudentPass123!")
    denied = client.post(
        "/api/v1/registration/enroll",
        json={"section_id": target_section_id},
        headers={**headers, "Idempotency-Key": "scope-denied"},
    )
    assert denied.status_code == 403

    finance_clerk = _create_user(db_session, "reg_clerk", UserRole.finance_clerk, "FinancePass1!", org_id=org2_id)
    _grant_org_scope(db_session, finance_clerk.id, org1_id)
    clerk_headers = _login(client, "reg_clerk", "FinancePass1!")
    allowed_courses = client.get("/api/v1/courses", headers=clerk_headers)
    assert allowed_courses.status_code == 200
    assert len(allowed_courses.json()) >= 1
