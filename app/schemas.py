from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    role: Literal["admin", "accountant", "manager", "employee"] = "admin"


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tenant_id: int
    email: EmailStr
    role: str


class CompanyCreate(BaseModel):
    name: str = Field(..., min_length=2)
    tax_id: str = Field(..., min_length=3)
    country: str = Field("PT", min_length=2, max_length=2)


class CompanyRead(CompanyCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tenant_id: int


class FinancialDocumentCreate(BaseModel):
    company_id: int
    document_type: Literal["invoice", "invoice_receipt", "credit_note", "debit_note", "receipt"]
    document_number: Optional[str] = None
    supplier: str = Field(..., min_length=2)
    amount: Decimal
    net_amount: Optional[Decimal] = None
    vat_amount: Decimal = Decimal("0.00")
    currency: Literal["EUR", "USD", "GBP", "BRL"] = "EUR"
    issue_date: date
    due_date: Optional[date] = None
    payment_method: Optional[Literal["direct_debit", "bank_transfer", "card", "cash", "other", "unknown"]] = "unknown"
    is_paid: bool = False
    description: str = Field(..., min_length=3)


class FinancialDocumentRead(FinancialDocumentCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tenant_id: int
    status: str
    category: Optional[str] = None
    confidence_score: Optional[Decimal] = None
    original_amount: Decimal


class NeuroAIResult(BaseModel):
    category: str
    confidence_score: float
    reasoning: str


class DocumentCreateResponse(BaseModel):
    document: FinancialDocumentRead
    neuro_ai: NeuroAIResult


class DashboardResponse(BaseModel):
    company_id: int
    company_name: str
    documents: int
    total_expenses: Decimal
    efficiency_score: float
    neuro_analysis: dict[str, Any]


class AuditLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tenant_id: Optional[int] = None
    action: str
    entity_type: str
    entity_id: Optional[int] = None
    details: Optional[str] = None
    created_at: datetime
