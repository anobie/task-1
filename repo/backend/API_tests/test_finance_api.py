from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.finance import EntryType, LedgerAccount, LedgerEntry
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


def test_payment_refund_arrears_reconciliation(client, db_session: Session) -> None:
    finance = _create_user(db_session, "finance1", UserRole.finance_clerk, "FinancePass1!")
    student = _create_user(db_session, "finance_student", UserRole.student, "StudentPass1!")
    headers = _login(client, "finance1", "FinancePass1!")

    payment = client.post(
        "/api/v1/finance/payments",
        json={
            "student_id": student.id,
            "amount": 200.0,
            "instrument": "CASH",
            "description": "Prepayment",
            "entry_date": date.today().isoformat(),
        },
        headers=headers,
    )
    assert payment.status_code == 200
    payment_id = payment.json()["id"]

    refund = client.post(
        "/api/v1/finance/refunds",
        json={
            "student_id": student.id,
            "amount": 50.0,
            "reference_entry_id": payment_id,
            "description": "Partial refund",
            "entry_date": date.today().isoformat(),
        },
        headers=headers,
    )
    assert refund.status_code == 200

    over_refund = client.post(
        "/api/v1/finance/refunds",
        json={
            "student_id": student.id,
            "amount": 300.0,
            "reference_entry_id": payment_id,
            "description": "Too much",
            "entry_date": date.today().isoformat(),
        },
        headers=headers,
    )
    assert over_refund.status_code == 422

    account = client.get(f"/api/v1/finance/accounts/{student.id}", headers=headers)
    assert account.status_code == 200
    assert len(account.json()["entries"]) >= 2

    account_row = db_session.query(LedgerAccount).filter(LedgerAccount.student_id == student.id).first()
    db_session.add(
        LedgerEntry(
            account_id=account_row.id,
            student_id=student.id,
            entry_type=EntryType.charge,
            amount=500.0,
            description="Monthly billing",
            entry_date=date.today() - timedelta(days=20),
        )
    )
    db_session.commit()

    arrears = client.get("/api/v1/finance/arrears", headers=headers)
    assert arrears.status_code == 200
    assert any(item["student_id"] == student.id for item in arrears.json())

    csv_content = "student_id,amount,statement_date\n" f"{student.id},200.00,{date.today().isoformat()}\n" f"{student.id},999.00,{date.today().isoformat()}\n"
    import_response = client.post(
        "/api/v1/finance/reconciliation/import",
        headers=headers,
        files={"file": ("statement.csv", csv_content, "text/csv")},
    )
    assert import_response.status_code == 200
    import_id = import_response.json()["import_id"]

    report = client.get(f"/api/v1/finance/reconciliation/{import_id}/report", headers=headers)
    assert report.status_code == 200
    assert report.json()["matched_total"] >= 200.0


def test_finance_rbac_denied_for_student(client, db_session: Session) -> None:
    _create_user(db_session, "student_no_fin", UserRole.student, "StudentPass1!")
    headers = _login(client, "student_no_fin", "StudentPass1!")

    response = client.get("/api/v1/finance/arrears", headers=headers)
    assert response.status_code == 403
