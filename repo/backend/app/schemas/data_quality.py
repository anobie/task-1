from datetime import datetime

from pydantic import BaseModel, Field


class ValidateWriteIn(BaseModel):
    entity_type: str = Field(min_length=2, max_length=80)
    payload: dict
    required_fields: list[str] = Field(default_factory=list)
    ranges: dict[str, dict[str, float]] = Field(default_factory=dict)
    unique_keys: list[str] = Field(default_factory=list)


class ValidateWriteOut(BaseModel):
    accepted: bool
    quality_score: int
    reasons: list[str]
    quarantine_id: int | None = None


class QuarantineOut(BaseModel):
    id: int
    entity_type: str
    rejection_reason: str
    quality_score: int
    status: str
    created_at: datetime
    resolved_at: datetime | None


class ResolveIn(BaseModel):
    action: str


class QualityReportOut(BaseModel):
    entity_type: str
    total_records: int
    quarantined: int
    open_items: int
    avg_quality_score: float
