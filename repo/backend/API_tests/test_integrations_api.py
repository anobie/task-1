from datetime import datetime, timezone
import hashlib
import hmac
import json

from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.integration import IntegrationClient
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


def _sign(secret: str, method: str, path: str, timestamp: str, nonce: str, body: bytes) -> str:
    body_hash = hashlib.sha256(body).hexdigest()
    canonical = f"{method.upper()}\n{path}\n{timestamp}\n{nonce}\n{body_hash}"
    return hmac.new(secret.encode("utf-8"), canonical.encode("utf-8"), hashlib.sha256).hexdigest()


def test_client_registration_and_hmac_flows(client, db_session: Session) -> None:
    _create_user(db_session, "int_admin", UserRole.admin, "AdminPass1!")
    admin_headers = _login(client, "int_admin", "AdminPass1!")

    create = client.post("/api/v1/integrations/clients", json={"name": "SIS Connector", "rate_limit_rpm": 5}, headers=admin_headers)
    assert create.status_code == 200
    client_id = create.json()["client_id"]
    secret = create.json()["client_secret"]

    stored_client = db_session.query(IntegrationClient).filter(IntegrationClient.client_id == client_id).first()
    assert stored_client is not None
    assert secret not in stored_client.secret_ciphertext

    path = "/api/v1/integrations/sis/students"
    payload = {"students": [{"id": "S1"}, {"id": "S2"}]}
    body = json.dumps(payload).encode("utf-8")
    ts = str(int(datetime.now(timezone.utc).timestamp()))
    nonce = "nonce-1"
    sig = _sign(secret, "POST", path, ts, nonce, body)
    headers = {
        "X-Client-ID": client_id,
        "X-Signature-256": sig,
        "X-Nonce": nonce,
        "X-Timestamp": ts,
        "Content-Type": "application/json",
    }
    ok = client.post(path, data=body, headers=headers)
    assert ok.status_code == 200
    assert ok.json()["synced"] == 2

    replay = client.post(path, data=body, headers=headers)
    assert replay.status_code == 409

    bad_sig_headers = {**headers, "X-Nonce": "nonce-2", "X-Signature-256": "deadbeef"}
    bad_sig = client.post(path, data=body, headers=bad_sig_headers)
    assert bad_sig.status_code == 401

    rotate = client.post(f"/api/v1/integrations/clients/{client_id}/rotate-secret", headers=admin_headers)
    assert rotate.status_code == 200
    rotated_secret = rotate.json()["client_secret"]

    old_nonce = "nonce-old-after-rotate"
    old_sig = _sign(secret, "POST", path, ts, old_nonce, body)
    old_headers = {
        "X-Client-ID": client_id,
        "X-Signature-256": old_sig,
        "X-Nonce": old_nonce,
        "X-Timestamp": ts,
        "Content-Type": "application/json",
    }
    old_attempt = client.post(path, data=body, headers=old_headers)
    assert old_attempt.status_code == 401

    new_nonce = "nonce-new-after-rotate"
    new_sig = _sign(rotated_secret, "POST", path, ts, new_nonce, body)
    new_headers = {
        "X-Client-ID": client_id,
        "X-Signature-256": new_sig,
        "X-Nonce": new_nonce,
        "X-Timestamp": ts,
        "Content-Type": "application/json",
    }
    new_attempt = client.post(path, data=body, headers=new_headers)
    assert new_attempt.status_code == 200


def test_rate_limit_and_qbank_import(client, db_session: Session) -> None:
    _create_user(db_session, "int_admin2", UserRole.admin, "AdminPass1!")
    admin_headers = _login(client, "int_admin2", "AdminPass1!")

    create = client.post("/api/v1/integrations/clients", json={"name": "QBank Connector", "rate_limit_rpm": 2}, headers=admin_headers)
    client_id = create.json()["client_id"]
    secret = create.json()["client_secret"]

    path = "/api/v1/integrations/qbank/forms"
    body = json.dumps({"forms": [{"id": 1}]}).encode("utf-8")
    base_ts = int(datetime.now(timezone.utc).timestamp())

    for idx in range(2):
        ts = str(base_ts + idx)
        nonce = f"rnonce-{idx}"
        sig = _sign(secret, "POST", path, ts, nonce, body)
        headers = {
            "X-Client-ID": client_id,
            "X-Signature-256": sig,
            "X-Nonce": nonce,
            "X-Timestamp": ts,
            "Content-Type": "application/json",
        }
        response = client.post(path, data=body, headers=headers)
        assert response.status_code == 200

    ts = str(base_ts + 3)
    nonce = "rnonce-over"
    sig = _sign(secret, "POST", path, ts, nonce, body)
    over_headers = {
        "X-Client-ID": client_id,
        "X-Signature-256": sig,
        "X-Nonce": nonce,
        "X-Timestamp": ts,
        "Content-Type": "application/json",
    }
    over = client.post(path, data=body, headers=over_headers)
    assert over.status_code == 429
