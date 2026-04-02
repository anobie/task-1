from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import secrets

from fastapi import HTTPException, Request
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import get_logger
from app.core.security import decrypt_integration_secret, encrypt_integration_secret
from app.models.integration import IntegrationClient, NonceLog


logger = get_logger("app.integrations")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _hash_secret(secret: str) -> str:
    return _sha256_hex(secret.encode("utf-8"))


def _integration_secret_key_material() -> str:
    return settings.integration_secret_enc_key or settings.secret_key


def create_client(db: Session, name: str, rate_limit_rpm: int | None) -> tuple[IntegrationClient, str]:
    raw_secret = secrets.token_urlsafe(36)
    client_id = f"cli_{secrets.token_hex(8)}"
    client = IntegrationClient(
        client_id=client_id,
        name=name,
        secret_ciphertext=encrypt_integration_secret(raw_secret, _integration_secret_key_material()),
        secret_hash=_hash_secret(raw_secret),
        rate_limit_rpm=rate_limit_rpm or settings.rate_limit_rpm,
        is_active=True,
    )
    db.add(client)
    db.commit()
    db.refresh(client)
    return client, raw_secret


def _canonical_string(method: str, path: str, timestamp: str, nonce: str, body_hash: str) -> str:
    return f"{method.upper()}\n{path}\n{timestamp}\n{nonce}\n{body_hash}"


def verify_request_signature(
    *,
    request: Request,
    body: bytes,
    client: IntegrationClient,
    timestamp: str,
    nonce: str,
    signature: str,
) -> None:
    body_hash = _sha256_hex(body)
    canonical = _canonical_string(request.method, request.url.path, timestamp, nonce, body_hash)
    client_secret = decrypt_integration_secret(client.secret_ciphertext, _integration_secret_key_material())
    expected = hmac.new(
        key=client_secret.encode("utf-8"),
        msg=canonical.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(signature.lower(), expected.lower()):
        logger.info(
            "integration_signature_invalid",
            extra={"event": "integrations.auth.signature_invalid", "fields": {"client_id": client.client_id, "path": request.url.path}},
        )
        raise HTTPException(status_code=401, detail="Invalid signature.")


def enforce_timestamp(timestamp: str) -> datetime:
    try:
        ts_int = int(timestamp)
    except ValueError as exc:
        logger.info("integration_timestamp_invalid", extra={"event": "integrations.auth.timestamp_invalid"})
        raise HTTPException(status_code=401, detail="Invalid timestamp header.") from exc
    requested_at = datetime.fromtimestamp(ts_int, tz=timezone.utc)
    now = _utcnow()
    tolerance = timedelta(seconds=settings.hmac_timestamp_tolerance)
    if requested_at < (now - tolerance) or requested_at > (now + tolerance):
        logger.info("integration_timestamp_outside_window", extra={"event": "integrations.auth.timestamp_outside_window"})
        raise HTTPException(status_code=401, detail="Request timestamp outside allowed window.")
    return requested_at


def enforce_rate_limit(db: Session, client: IntegrationClient, requested_at: datetime) -> None:
    window_start = requested_at - timedelta(minutes=1)
    count = (
        db.query(func.count(NonceLog.id))
        .filter(NonceLog.client_id == client.client_id, NonceLog.requested_at >= window_start)
        .scalar()
    )
    if int(count or 0) >= client.rate_limit_rpm:
        logger.info(
            "integration_rate_limit_exceeded",
            extra={"event": "integrations.auth.rate_limited", "fields": {"client_id": client.client_id}},
        )
        raise HTTPException(status_code=429, detail="Rate limit exceeded.")


def enforce_nonce(db: Session, client_id: str, nonce: str, requested_at: datetime, body: bytes, path: str) -> None:
    try:
        db.add(
            NonceLog(
                client_id=client_id,
                nonce=nonce,
                requested_at=requested_at,
                body_hash=_sha256_hex(body),
                path=path,
            )
        )
        db.flush()
    except IntegrityError as exc:
        logger.info(
            "integration_nonce_reuse",
            extra={"event": "integrations.auth.nonce_reused", "fields": {"client_id": client_id}},
        )
        raise HTTPException(status_code=409, detail="Nonce has already been used.") from exc


def authenticate_integration_request(db: Session, request: Request, body: bytes) -> IntegrationClient:
    client_id = request.headers.get("X-Client-ID")
    signature = request.headers.get("X-Signature-256")
    nonce = request.headers.get("X-Nonce")
    timestamp = request.headers.get("X-Timestamp")
    if not client_id or not signature or not nonce or not timestamp:
        logger.info("integration_headers_missing", extra={"event": "integrations.auth.headers_missing"})
        raise HTTPException(status_code=401, detail="Missing integration authentication headers.")

    client = db.query(IntegrationClient).filter(IntegrationClient.client_id == client_id, IntegrationClient.is_active.is_(True)).first()
    if client is None:
        logger.info("integration_client_unknown", extra={"event": "integrations.auth.client_unknown", "fields": {"client_id": client_id}})
        raise HTTPException(status_code=401, detail="Unknown integration client.")

    requested_at = enforce_timestamp(timestamp)
    enforce_rate_limit(db, client, requested_at)
    verify_request_signature(
        request=request,
        body=body,
        client=client,
        timestamp=timestamp,
        nonce=nonce,
        signature=signature,
    )
    enforce_nonce(db, client_id, nonce, requested_at, body, request.url.path)
    db.commit()
    logger.info(
        "integration_auth_succeeded",
        extra={"event": "integrations.auth.success", "fields": {"client_id": client.client_id, "path": request.url.path}},
    )
    return client


def rotate_client_secret(db: Session, client_id: str) -> tuple[IntegrationClient, str]:
    client = db.query(IntegrationClient).filter(IntegrationClient.client_id == client_id).first()
    if client is None:
        raise HTTPException(status_code=404, detail="Integration client not found.")

    raw_secret = secrets.token_urlsafe(36)
    client.secret_ciphertext = encrypt_integration_secret(raw_secret, _integration_secret_key_material())
    client.secret_hash = _hash_secret(raw_secret)
    db.commit()
    db.refresh(client)
    return client, raw_secret
