from datetime import date
from typing import Optional

from pydantic import BaseModel, Field


class CompanyCreate(BaseModel):
    name: str = Field(..., min_length=2)
    tax_id: str = Field(..., min_length=3)
    country: str = "Portugal"


class CompanyRead(CompanyCreate):
    id: int

    class Config:
        from_attributes = True


class FinancialDocumentCreate(BaseModel):
    company_id: int
    document_type: str = Field(..., min_length=2)
    supplier: str = Field(..., min_length=2)
    amount: float = Field(..., ge=0)
    vat_amount: float = Field(0, ge=0)
    currency: str = "EUR"
    issue_date: date
    description: str = Field(..., min_length=3)


class FinancialDocumentRead(FinancialDocumentCreate):
    id: int
    status: str
    category: Optional[str] = None
    confidence_score: Optional[float] = None

    class Config:
        from_attributes = True
