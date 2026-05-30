"""Initial SaaS schema."""

from alembic import op
import sqlalchemy as sa

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("tenants", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("name", sa.String(), nullable=False), sa.Column("plan", sa.String(), nullable=False), sa.Column("created_at", sa.DateTime(), nullable=False))
    op.create_index("ix_tenants_name", "tenants", ["name"])
    op.create_table("users", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False), sa.Column("email", sa.String(), nullable=False), sa.Column("hashed_password", sa.String(), nullable=False), sa.Column("role", sa.String(), nullable=False), sa.Column("created_at", sa.DateTime(), nullable=False))
    op.create_index("ix_users_tenant_id", "users", ["tenant_id"])
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_table("companies", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False), sa.Column("name", sa.String(), nullable=False), sa.Column("tax_id", sa.String(), nullable=False), sa.Column("country", sa.String(), nullable=False), sa.UniqueConstraint("tenant_id", "tax_id", "country", name="uq_company_tenant_tax_country"))
    op.create_index("ix_companies_tenant_id", "companies", ["tenant_id"])
    op.create_index("ix_companies_name", "companies", ["name"])
    op.create_index("ix_companies_tax_id", "companies", ["tax_id"])
    op.create_table("financial_documents", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False), sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False), sa.Column("document_type", sa.String(), nullable=False), sa.Column("supplier", sa.String(), nullable=False), sa.Column("amount", sa.Numeric(12, 2), nullable=False), sa.Column("vat_amount", sa.Numeric(12, 2), nullable=False), sa.Column("currency", sa.String(length=3), nullable=False), sa.Column("issue_date", sa.Date(), nullable=False), sa.Column("description", sa.String(), nullable=False), sa.Column("status", sa.String(), nullable=False), sa.Column("category", sa.String(), nullable=True), sa.Column("confidence_score", sa.Numeric(5, 2), nullable=True))
    op.create_index("ix_financial_documents_tenant_id", "financial_documents", ["tenant_id"])
    op.create_index("ix_financial_documents_company_id", "financial_documents", ["company_id"])
    op.create_table("audit_logs", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=True), sa.Column("action", sa.String(), nullable=False), sa.Column("entity_type", sa.String(), nullable=False), sa.Column("entity_id", sa.Integer(), nullable=True), sa.Column("details", sa.String(), nullable=True), sa.Column("created_at", sa.DateTime(), nullable=False))
    op.create_index("ix_audit_logs_tenant_id", "audit_logs", ["tenant_id"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("financial_documents")
    op.drop_table("companies")
    op.drop_table("users")
    op.drop_table("tenants")
