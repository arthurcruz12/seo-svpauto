from datetime import date
from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=8)


class RegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=8, max_length=128)
    company_name: str | None = Field(default=None, max_length=160)


class MfaRequest(BaseModel):
    challenge_id: str
    code: str = Field(min_length=6, max_length=6)


class AccountProfile(BaseModel):
    id: str
    company_id: str
    company_name: str
    name: str
    email: str
    role: str
    permissions: list[str]


class TokenResponse(BaseModel):
    access_token: str
    account: AccountProfile
    token_type: str = "bearer"


class ChallengeResponse(BaseModel):
    challenge_id: str
    expires_in_seconds: int
    delivery_hint: str
    development_code: str | None = None


class AuditEvent(BaseModel):
    actor: str
    action: str
    details: str


class AiQuestionRequest(BaseModel):
    question: str = Field(min_length=2, max_length=500)
    conversation_id: str | None = Field(default=None, max_length=80)
    analysis_level: str = Field(default="Elevado", pattern="^(Rápido|Elevado|Auditoria)$")


class SnapshotCreateRequest(BaseModel):
    period: str = Field(default="daily", pattern="^(daily|weekly|monthly|quarterly|annual)$")
    label: str | None = Field(default=None, max_length=120)
    report_date: date | None = None


class BillingCheckoutRequest(BaseModel):
    plan: str = Field(default="professional", pattern="^(starter|professional|business)$")


class StrategyFitRequest(BaseModel):
    signals: list[str] = Field(default_factory=list, max_length=12)


class MovementClassification(BaseModel):
    date: str
    description: str
    entity: str
    amount: float
    account_code: str
    account_name: str
    confidence: int
