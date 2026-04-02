from pydantic import BaseModel, Field


class IntegrationClientCreateIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    rate_limit_rpm: int | None = Field(default=None, ge=1, le=2000)


class IntegrationClientCreateOut(BaseModel):
    client_id: str
    client_secret: str
    rate_limit_rpm: int


class IntegrationClientRotateOut(BaseModel):
    client_id: str
    client_secret: str


class SISStudentsSyncIn(BaseModel):
    students: list[dict]


class QbankFormsImportIn(BaseModel):
    forms: list[dict]
