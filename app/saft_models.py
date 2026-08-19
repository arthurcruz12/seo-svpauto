from datetime import datetime, timezone

from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint

from app.ai_database import AIBase


class SaftImport(AIBase):
    __tablename__ = "saft_imports"
    __table_args__ = (
        UniqueConstraint("tenant_id", "company_id", "sha256", name="uq_saft_import_tenant_company_sha256"),
    )

    id = Column(Integer, primary_key=True, index=True)
    # tenant_id/company_id are references to the operational database. They are
    # deliberately not cross-database foreign keys, keeping Neon isolated.
    tenant_id = Column(Integer, nullable=False, index=True)
    company_id = Column(Integer, nullable=False, index=True)
    filename = Column(String, nullable=False)
    sha256 = Column(String(64), nullable=False, index=True)
    schema_version = Column(String, nullable=True)
    namespace = Column(String, nullable=True)
    status = Column(String, nullable=False, default="staged", index=True)
    source = Column(String, nullable=False, default="upload")
    company_tax_id = Column(String, nullable=True, index=True)
    source_company_name = Column(String, nullable=True)
    fiscal_year = Column(String, nullable=True)
    start_date = Column(String, nullable=True)
    end_date = Column(String, nullable=True)
    currency_code = Column(String(3), nullable=False, default="EUR")
    validation_errors = Column(Text, nullable=True)
    validation_warnings = Column(Text, nullable=True)
    raw_file_reference = Column(String, nullable=True)
    created_by = Column(String, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)


class SaftStagedDocument(AIBase):
    __tablename__ = "saft_staged_documents"
    __table_args__ = (
        UniqueConstraint("saft_import_id", "document_number", name="uq_saft_staged_import_document"),
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, nullable=False, index=True)
    company_id = Column(Integer, nullable=False, index=True)
    saft_import_id = Column(Integer, ForeignKey("saft_imports.id", ondelete="CASCADE"), nullable=False, index=True)
    document_number = Column(String, nullable=True, index=True)
    document_type = Column(String, nullable=False)
    document_status = Column(String, nullable=True)
    invoice_date = Column(Date, nullable=True)
    customer_id = Column(String, nullable=True, index=True)
    net_total = Column(Numeric(14, 2), nullable=False, default=0)
    tax_payable = Column(Numeric(14, 2), nullable=False, default=0)
    gross_total = Column(Numeric(14, 2), nullable=False, default=0)
    raw_gross_total = Column(Numeric(14, 2), nullable=False, default=0)
    stage_status = Column(String, nullable=False, default="read_only")


class SaftAnomaly(AIBase):
    __tablename__ = "saft_anomalies"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, nullable=False, index=True)
    company_id = Column(Integer, nullable=False, index=True)
    saft_import_id = Column(Integer, ForeignKey("saft_imports.id", ondelete="CASCADE"), nullable=False, index=True)
    code = Column(String, nullable=False, index=True)
    severity = Column(String, nullable=False, default="warning", index=True)
    document_number = Column(String, nullable=True, index=True)
    details = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
