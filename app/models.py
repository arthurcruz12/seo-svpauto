from datetime import datetime, timezone

from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, nullable=False, unique=True, index=True)
    hashed_password = Column(String, nullable=False)
    role = Column(String, nullable=False, default="admin")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)


class Company(Base):
    __tablename__ = "companies"
    __table_args__ = (UniqueConstraint("tax_id", "country", name="uq_company_tax_country"),)

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    tax_id = Column(String, nullable=False, index=True)
    country = Column(String, default="PT", nullable=False)

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
    amount = Column(Numeric(12, 2), nullable=False)
    vat_amount = Column(Numeric(12, 2), default=0, nullable=False)
    currency = Column(String(3), default="EUR", nullable=False)
    issue_date = Column(Date, nullable=False)
    description = Column(String, nullable=False)
    status = Column(String, default="uploaded", nullable=False)
    category = Column(String, nullable=True)
    confidence_score = Column(Numeric(5, 2), nullable=True)

    company = relationship("Company", back_populates="documents")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    action = Column(String, nullable=False, index=True)
    entity_type = Column(String, nullable=False)
    entity_id = Column(Integer, nullable=True)
    details = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
