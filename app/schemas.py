from pydantic import BaseModel


class CompanyCreate(BaseModel):
    name: str
    tax_id: str
    country: str = 'Portugal'


class FinancialDocumentCreate(BaseModel):
    company_id: int
    document_type: str
    supplier: str
    amount: float
    vat_amount: float
    currency: str = 'EUR'
    issue_date: str
    description: str
