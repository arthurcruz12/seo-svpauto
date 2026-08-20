from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, Date, DateTime, Float, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database import Base


class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    plan = Column(String, nullable=False, default="free")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    users = relationship("User", back_populates="tenant")
    companies = relationship("Company", back_populates="tenant")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    email = Column(String, nullable=False, unique=True, index=True)
    hashed_password = Column(String, nullable=False)
    role = Column(String, nullable=False, default="admin")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    tenant = relationship("Tenant", back_populates="users")


class Company(Base):
    __tablename__ = "companies"
    __table_args__ = (UniqueConstraint("tenant_id", "tax_id", "country", name="uq_company_tenant_tax_country"),)

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    name = Column(String, nullable=False, index=True)
    tax_id = Column(String, nullable=False, index=True)
    country = Column(String, default="PT", nullable=False)

    tenant = relationship("Tenant", back_populates="companies")
    documents = relationship(
        "FinancialDocument",
        back_populates="company",
        cascade="all, delete-orphan",
    )


class FinancialDocument(Base):
    __tablename__ = "financial_documents"
    __table_args__ = (
        UniqueConstraint("tenant_id", "company_id", "document_number", name="uq_document_tenant_company_number"),
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    document_type = Column(String, nullable=False)
    document_number = Column(String, nullable=True, index=True)
    supplier = Column(String, nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    net_amount = Column(Numeric(12, 2), nullable=False, default=0)
    vat_amount = Column(Numeric(12, 2), default=0, nullable=False)
    original_amount = Column(Numeric(12, 2), nullable=False, default=0)
    currency = Column(String(3), default="EUR", nullable=False)
    issue_date = Column(Date, nullable=False)
    due_date = Column(Date, nullable=True)
    payment_method = Column(String, nullable=True)
    is_paid = Column(Boolean, nullable=False, default=False)
    description = Column(String, nullable=False)
    status = Column(String, default="uploaded", nullable=False)
    category = Column(String, nullable=True)
    confidence_score = Column(Numeric(5, 2), nullable=True)

    company = relationship("Company", back_populates="documents")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True, index=True)
    action = Column(String, nullable=False, index=True)
    entity_type = Column(String, nullable=False)
    entity_id = Column(Integer, nullable=True)
    details = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)


class AgentTask(Base):
    __tablename__ = "agent_tasks"

    id = Column(String(36), primary_key=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True, index=True)
    agent_type = Column(String(50), nullable=False, default="manager", index=True)
    task_type = Column(String(50), nullable=False, index=True)
    status = Column(String(24), nullable=False, default="PENDING", index=True)
    progress = Column(Integer, nullable=False, default=0)
    instruction = Column(Text, nullable=False)
    source_filename = Column(String(255), nullable=True)
    records_processed = Column(Integer, nullable=False, default=0)
    records_rejected = Column(Integer, nullable=False, default=0)
    approval_required = Column(Boolean, nullable=False, default=False)
    confidence = Column(Float, nullable=False, default=0.0)
    audit_json = Column(Text, nullable=True)
    error_code = Column(String(100), nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)

    executions = relationship("AgentExecution", back_populates="task", cascade="all, delete-orphan")
    artifacts = relationship("AgentArtifact", back_populates="task", cascade="all, delete-orphan")


class AgentExecution(Base):
    __tablename__ = "agent_executions"

    id = Column(String(36), primary_key=True)
    task_id = Column(String(36), ForeignKey("agent_tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    agent_name = Column(String(100), nullable=False, index=True)
    status = Column(String(24), nullable=False, index=True)
    started_at = Column(DateTime, nullable=False)
    finished_at = Column(DateTime, nullable=True)
    input_summary = Column(Text, nullable=True)
    output_summary = Column(Text, nullable=True)
    confidence = Column(Float, nullable=False, default=0.0)
    error_message = Column(Text, nullable=True)

    task = relationship("AgentTask", back_populates="executions")


class AgentArtifact(Base):
    __tablename__ = "agent_artifacts"

    id = Column(String(36), primary_key=True)
    task_id = Column(String(36), ForeignKey("agent_tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    content_type = Column(String(150), nullable=False)
    size = Column(Integer, nullable=False)
    sha256 = Column(String(64), nullable=False, index=True)
    role = Column(String(24), nullable=False, index=True)
    storage_provider = Column(String(50), nullable=False, default="local")
    storage_reference = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    task = relationship("AgentTask", back_populates="artifacts")
