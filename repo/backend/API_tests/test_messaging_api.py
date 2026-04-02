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


def test_dispatch_list_unread_and_mark_read(client, db_session: Session) -> None:
    instructor = _create_user(db_session, "msg_instructor", UserRole.instructor, "InstructorPass1!")
    student = _create_user(db_session, "msg_student", UserRole.student, "StudentPass1!")

    instructor_headers = _login(client, "msg_instructor", "InstructorPass1!")
    student_headers = _login(client, "msg_student", "StudentPass1!")

    dispatch = client.post(
        "/api/v1/messaging/dispatch",
        json={
            "trigger_type": "ASSIGNMENT_POSTED",
            "title": "New Assignment",
            "message": "Please review submission package.",
            "recipient_ids": [student.id],
            "metadata": {"round": 1},
        },
        headers=instructor_headers,
    )
    assert dispatch.status_code == 200
    assert dispatch.json()["created"] == 1

    listing = client.get("/api/v1/messaging/notifications", headers=student_headers)
    assert listing.status_code == 200
    assert listing.json()["unread_count"] == 1
    notification_id = listing.json()["notifications"][0]["id"]

    mark_read = client.patch(f"/api/v1/messaging/notifications/{notification_id}/read", headers=student_headers)
    assert mark_read.status_code == 200
    assert mark_read.json()["read"] is True

    listing_after = client.get("/api/v1/messaging/notifications", headers=student_headers)
    assert listing_after.status_code == 200
    assert listing_after.json()["unread_count"] == 0


def test_mark_read_denied_for_non_owner_and_dispatch_rbac(client, db_session: Session) -> None:
    instructor = _create_user(db_session, "msg_instructor2", UserRole.instructor, "InstructorPass1!")
    student_a = _create_user(db_session, "msg_student_a", UserRole.student, "StudentPass1!")
    student_b = _create_user(db_session, "msg_student_b", UserRole.student, "StudentPass1!")

    instructor_headers = _login(client, "msg_instructor2", "InstructorPass1!")
    student_a_headers = _login(client, "msg_student_a", "StudentPass1!")
    student_b_headers = _login(client, "msg_student_b", "StudentPass1!")

    dispatch = client.post(
        "/api/v1/messaging/dispatch",
        json={
            "trigger_type": "GRADING_COMPLETED",
            "title": "Grades Ready",
            "message": "Your grading cycle is complete.",
            "recipient_ids": [student_a.id],
        },
        headers=instructor_headers,
    )
    assert dispatch.status_code == 200

    listing = client.get("/api/v1/messaging/notifications", headers=student_a_headers)
    notification_id = listing.json()["notifications"][0]["id"]

    forbidden_read = client.patch(f"/api/v1/messaging/notifications/{notification_id}/read", headers=student_b_headers)
    assert forbidden_read.status_code == 404

    forbidden_dispatch = client.post(
        "/api/v1/messaging/dispatch",
        json={
            "trigger_type": "DEADLINE_24H",
            "title": "Reminder",
            "message": "24 hour reminder.",
            "recipient_ids": [student_b.id],
        },
        headers=student_a_headers,
    )
    assert forbidden_dispatch.status_code == 403
