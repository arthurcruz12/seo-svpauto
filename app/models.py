from sqlalchemy import Column, Integer, String, Float
from app.database import Base


class Company(Base):
    __tablename__ = 'companies'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    tax_id = Column(String, nullable=False)
    country = Column(String, default='Portugal')


class FinancialDocument(Base):
    __tablename__ = 'financial_documents'

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer)
    document_type = Column(String)
    supplier = Column(String)
    amount = Column(Float)
    vat_amount = Column(Float)
    currency = Column(String, default='EUR')
    issue_date = Column(String)
    description = Column(String)
    status = Column(String, default='uploaded')
    category = Column(String, nullable=True)
