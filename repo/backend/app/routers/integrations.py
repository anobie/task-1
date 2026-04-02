import json

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.audit import write_audit_log
from app.core.auth import require_admin
from app.core.database import get_db
from app.models.user import User
from app.schemas.integration import (
    IntegrationClientCreateIn,
    IntegrationClientCreateOut,
    QbankFormsImportIn,
    SISStudentsSyncIn,
)
from app.services import integration_service

router = APIRouter(prefix="/integrations", tags=["integrations"])


@router.post("/clients", response_model=IntegrationClientCreateOut)
def create_client(payload: IntegrationClientCreateIn, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    client, raw_secret = integration_service.create_client(db, payload.name, payload.rate_limit_rpm)
    write_audit_log(
        db,
        actor_id=admin.id,
        action="integrations.client.create",
        entity_name="IntegrationClient",
        entity_id=client.id,
        before=None,
        after={"client_id": client.client_id, "name": client.name, "rate_limit_rpm": client.rate_limit_rpm},
    )
    db.commit()
    return IntegrationClientCreateOut(client_id=client.client_id, client_secret=raw_secret, rate_limit_rpm=client.rate_limit_rpm)


def _auth_integration(request: Request, db: Session) -> None:
    body = request.scope.get("_cached_body")
    if body is None:
        raise HTTPException(status_code=400, detail="Request body unavailable")
    integration_service.authenticate_integration_request(db, request, body)


@router.post("/sis/students")
async def sis_students_sync(request: Request, db: Session = Depends(get_db)):
    body = await request.body()
    request.scope["_cached_body"] = body
    _auth_integration(request, db)
    payload = SISStudentsSyncIn(**json.loads(body.decode("utf-8") or "{}"))
    return {"synced": len(payload.students)}


@router.post("/qbank/forms")
async def qbank_forms_import(request: Request, db: Session = Depends(get_db)):
    body = await request.body()
    request.scope["_cached_body"] = body
    _auth_integration(request, db)
    payload = QbankFormsImportIn(**json.loads(body.decode("utf-8") or "{}"))
    return {"imported": len(payload.forms)}
