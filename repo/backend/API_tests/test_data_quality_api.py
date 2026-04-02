from sqlalchemy.orm import Session

from app.core.security import hash_password
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


def test_quarantine_and_resolution_and_report(client, db_session: Session) -> None:
    _create_user(db_session, "dq_admin", UserRole.admin, "AdminPass1!")
    headers = _login(client, "dq_admin", "AdminPass1!")

    validate = client.post(
        "/api/v1/data-quality/validate-write",
        json={
            "entity_type": "StudentRecord",
            "payload": {"name": "", "age": 200, "student_code": "A-001"},
            "required_fields": ["name", "student_code"],
            "ranges": {"age": {"min": 10, "max": 100}},
            "unique_keys": ["student_code"],
        },
        headers=headers,
    )
    assert validate.status_code == 202
    assert validate.json()["accepted"] is False
    quarantine_id = validate.json()["quarantine_id"]
    assert quarantine_id is not None

    listing = client.get("/api/v1/data-quality/quarantine", headers=headers)
    assert listing.status_code == 200
    assert len(listing.json()) >= 1

    resolve = client.patch(
        f"/api/v1/data-quality/quarantine/{quarantine_id}/resolve",
        json={"action": "ACCEPT"},
        headers=headers,
    )
    assert resolve.status_code == 200
    assert resolve.json()["status"] == "ACCEPTED"

    report = client.get("/api/v1/data-quality/report", headers=headers)
    assert report.status_code == 200
    assert any(item["entity_type"] == "StudentRecord" for item in report.json())


def test_data_quality_rbac_denied_for_student(client, db_session: Session) -> None:
    _create_user(db_session, "dq_student", UserRole.student, "StudentPass1!")
    headers = _login(client, "dq_student", "StudentPass1!")

    response = client.get("/api/v1/data-quality/quarantine", headers=headers)
    assert response.status_code == 403
