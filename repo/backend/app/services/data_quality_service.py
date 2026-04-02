from datetime import datetime, timezone
import hashlib
import json
from difflib import SequenceMatcher

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.data_quality import QuarantineEntry, QuarantineStatus


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _fingerprint(payload: dict) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def evaluate_payload(
    db: Session,
    *,
    entity_type: str,
    payload: dict,
    required_fields: list[str],
    ranges: dict[str, dict[str, float]],
    unique_keys: list[str],
) -> tuple[bool, int, list[str], str]:
    reasons: list[str] = []
    score = 100

    for field in required_fields:
        value = payload.get(field)
        if value is None or (isinstance(value, str) and not value.strip()):
            reasons.append(f"Missing required field: {field}")
            score -= 20

    for field, bounds in ranges.items():
        if field not in payload:
            continue
        try:
            value = float(payload[field])
        except (TypeError, ValueError):
            reasons.append(f"Range validation failed for {field}: non-numeric")
            score -= 15
            continue
        min_value = bounds.get("min")
        max_value = bounds.get("max")
        if min_value is not None and value < min_value:
            reasons.append(f"Range validation failed for {field}: below minimum")
            score -= 15
        if max_value is not None and value > max_value:
            reasons.append(f"Range validation failed for {field}: above maximum")
            score -= 15

    fingerprint = _fingerprint(payload)
    existing_fingerprint = (
        db.query(QuarantineEntry)
        .filter(QuarantineEntry.entity_type == entity_type, QuarantineEntry.fingerprint == fingerprint)
        .first()
    )
    if existing_fingerprint is not None:
        reasons.append("Duplicate fingerprint detected")
        score -= 20

    for key in unique_keys:
        if key not in payload:
            continue
        value = str(payload[key])
        similar_rows = (
            db.query(QuarantineEntry)
            .filter(QuarantineEntry.entity_type == entity_type)
            .order_by(QuarantineEntry.id.desc())
            .limit(50)
            .all()
        )
        for row in similar_rows:
            try:
                row_payload = json.loads(row.payload_json)
            except json.JSONDecodeError:
                continue
            candidate = str(row_payload.get(key, ""))
            if candidate and _similarity(value.lower(), candidate.lower()) >= settings.dedup_threshold:
                reasons.append(f"Potential duplicate by similarity on '{key}'")
                score -= 15
                break

    score = max(0, min(100, score))
    accepted = len(reasons) == 0
    return accepted, score, reasons, fingerprint


def quarantine_write(
    db: Session,
    *,
    entity_type: str,
    payload: dict,
    reasons: list[str],
    quality_score: int,
    fingerprint: str,
) -> QuarantineEntry:
    entry = QuarantineEntry(
        entity_type=entity_type,
        payload_json=json.dumps(payload, sort_keys=True, default=str),
        rejection_reason="; ".join(reasons),
        quality_score=quality_score,
        fingerprint=fingerprint,
        status=QuarantineStatus.open,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def list_quarantine(db: Session, status: str | None, limit: int, offset: int) -> list[QuarantineEntry]:
    query = db.query(QuarantineEntry)
    if status:
        try:
            parsed = QuarantineStatus(status)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="Invalid status filter") from exc
        query = query.filter(QuarantineEntry.status == parsed)
    return query.order_by(QuarantineEntry.id.desc()).offset(offset).limit(limit).all()


def resolve_quarantine(db: Session, entry_id: int, action: str, resolver_id: int) -> QuarantineEntry:
    entry = db.query(QuarantineEntry).filter(QuarantineEntry.id == entry_id).first()
    if entry is None:
        raise HTTPException(status_code=404, detail="Quarantine entry not found")
    action_upper = action.upper()
    if action_upper not in {"ACCEPT", "DISCARD"}:
        raise HTTPException(status_code=422, detail="Action must be ACCEPT or DISCARD")
    entry.status = QuarantineStatus.accepted if action_upper == "ACCEPT" else QuarantineStatus.discarded
    entry.resolved_at = _utcnow()
    entry.resolved_by = resolver_id
    db.commit()
    db.refresh(entry)
    return entry


def quality_report(db: Session) -> list[dict]:
    entity_types = [row[0] for row in db.query(QuarantineEntry.entity_type).distinct().all()]
    result: list[dict] = []
    for entity_type in entity_types:
        total = db.query(func.count(QuarantineEntry.id)).filter(QuarantineEntry.entity_type == entity_type).scalar() or 0
        open_items = (
            db.query(func.count(QuarantineEntry.id))
            .filter(QuarantineEntry.entity_type == entity_type, QuarantineEntry.status == QuarantineStatus.open)
            .scalar()
            or 0
        )
        avg_score = (
            db.query(func.avg(QuarantineEntry.quality_score))
            .filter(QuarantineEntry.entity_type == entity_type)
            .scalar()
        )
        result.append(
            {
                "entity_type": entity_type,
                "total_records": int(total),
                "quarantined": int(total),
                "open_items": int(open_items),
                "avg_quality_score": round(float(avg_score or 0.0), 2),
            }
        )
    return result
