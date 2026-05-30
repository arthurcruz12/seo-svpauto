from datetime import date, datetime
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    role: Literal["admin", "accountant", "manager", "employee"] = "admin"


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserRead(BaseModel):
    id: int
    email: EmailStr
    role: str

    class Config:
        from_attributes = True


class CompanyCreate(BaseModel):
    name: str = Field(..., min_length=2)
    tax_id: str = Field(..., min_length=3)
    country: str = Field("PT", min_length=2, max_length=2)


class CompanyRead(CompanyCreate):
    id: int

    class Config:
        from_attributes = True


class FinancialDocumentCreate(BaseModel):
    company_id: int
    document_type: str = Field(..., min_length=2)
    supplier: str = Field(..., min_length=2)
    amount: Decimal = Field(..., ge=0)
    vat_amount: Decimal = Field(Decimal("0.00"), ge=0)
    currency: Literal["EUR", "USD", "GBP", "BRL"] = "EUR"
    issue_date: date
    description: str = Field(..., min_length=3)


class FinancialDocumentRead(FinancialDocumentCreate):
    id: int
    status: str
    category: Optional[str] = None
    confidence_score: Optional[Decimal] = None

    class Config:
        from_attributes = True


class AuditLogRead(BaseModel):
    id: int
    action: str
    entity_type: str
    entity_id: Optional[int] = None
    details: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
