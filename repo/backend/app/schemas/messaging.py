from datetime import datetime

from pydantic import BaseModel, Field


class TriggerDispatchIn(BaseModel):
    trigger_type: str
    title: str = Field(min_length=3, max_length=200)
    message: str = Field(min_length=1)
    recipient_ids: list[int] = Field(min_length=1)
    metadata: dict | None = None


class NotificationOut(BaseModel):
    id: int
    trigger_type: str
    title: str
    message: str
    read: bool
    delivered_at: datetime
    read_at: datetime | None


class NotificationListOut(BaseModel):
    unread_count: int
    notifications: list[NotificationOut]


class TriggerConfigOut(BaseModel):
    trigger_type: str
    enabled: bool
    lead_hours: int | None


class TriggerConfigUpdateIn(BaseModel):
    enabled: bool
    lead_hours: int | None = Field(default=None, ge=1, le=168)


class ProcessDueOut(BaseModel):
    processed: int
