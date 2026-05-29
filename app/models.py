from sqlalchemy import Column, Date, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.database import Base


class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    tax_id = Column(String, nullable=False, unique=True, index=True)
    country = Column(String, default="Portugal")

    documents = relationship(
        "FinancialDocument",
        back_populates="company",
        cascade="all, delete-orphan",
    )


class FinancialDocument(Base):
    __tablename__ = "financial_documents"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    document_type = Column(String, nullable=False)
    supplier = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    vat_amount = Column(Float, default=0.0)
    currency = Column(String, default="EUR")
    issue_date = Column(Date, nullable=False)
    description = Column(String, nullable=False)
    status = Column(String, default="uploaded")
    category = Column(String, nullable=True)
    confidence_score = Column(Float, nullable=True)

    company = relationship("Company", back_populates="documents")
