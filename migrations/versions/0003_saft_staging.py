"""Add isolated read-only SAF-T staging tables."""

from alembic import op
import sqlalchemy as sa

revision = "0003_saft_staging"
down_revision = "0002_document_financial_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "saft_imports",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("filename", sa.String(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("schema_version", sa.String(), nullable=True),
        sa.Column("namespace", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="staged"),
        sa.Column("source", sa.String(), nullable=False, server_default="upload"),
        sa.Column("company_tax_id", sa.String(), nullable=True),
        sa.Column("source_company_name", sa.String(), nullable=True),
        sa.Column("fiscal_year", sa.String(), nullable=True),
        sa.Column("start_date", sa.String(), nullable=True),
        sa.Column("end_date", sa.String(), nullable=True),
        sa.Column("currency_code", sa.String(length=3), nullable=False, server_default="EUR"),
        sa.Column("validation_errors", sa.Text(), nullable=True),
        sa.Column("validation_warnings", sa.Text(), nullable=True),
        sa.Column("raw_file_reference", sa.String(), nullable=True),
        sa.Column("created_by", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("tenant_id", "company_id", "sha256", name="uq_saft_import_tenant_company_sha256"),
    )
    op.create_index("ix_saft_imports_tenant_id", "saft_imports", ["tenant_id"])
    op.create_index("ix_saft_imports_company_id", "saft_imports", ["company_id"])
    op.create_index("ix_saft_imports_sha256", "saft_imports", ["sha256"])
    op.create_index("ix_saft_imports_status", "saft_imports", ["status"])

    op.create_table(
        "saft_staged_documents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("saft_import_id", sa.Integer(), sa.ForeignKey("saft_imports.id"), nullable=False),
        sa.Column("document_number", sa.String(), nullable=True),
        sa.Column("document_type", sa.String(), nullable=False),
        sa.Column("document_status", sa.String(), nullable=True),
        sa.Column("invoice_date", sa.Date(), nullable=True),
        sa.Column("customer_id", sa.String(), nullable=True),
        sa.Column("net_total", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("tax_payable", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("gross_total", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("raw_gross_total", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("stage_status", sa.String(), nullable=False, server_default="read_only"),
        sa.UniqueConstraint("saft_import_id", "document_number", name="uq_saft_staged_import_document"),
    )
    op.create_index("ix_saft_staged_documents_tenant_id", "saft_staged_documents", ["tenant_id"])
    op.create_index("ix_saft_staged_documents_company_id", "saft_staged_documents", ["company_id"])
    op.create_index("ix_saft_staged_documents_saft_import_id", "saft_staged_documents", ["saft_import_id"])

    op.create_table(
        "saft_anomalies",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("saft_import_id", sa.Integer(), sa.ForeignKey("saft_imports.id"), nullable=False),
        sa.Column("code", sa.String(), nullable=False),
        sa.Column("severity", sa.String(), nullable=False, server_default="warning"),
        sa.Column("document_number", sa.String(), nullable=True),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_saft_anomalies_tenant_id", "saft_anomalies", ["tenant_id"])
    op.create_index("ix_saft_anomalies_company_id", "saft_anomalies", ["company_id"])
    op.create_index("ix_saft_anomalies_saft_import_id", "saft_anomalies", ["saft_import_id"])
    op.create_index("ix_saft_anomalies_code", "saft_anomalies", ["code"])
    op.create_index("ix_saft_anomalies_severity", "saft_anomalies", ["severity"])


def downgrade() -> None:
    op.drop_table("saft_anomalies")
    op.drop_table("saft_staged_documents")
    op.drop_table("saft_imports")
