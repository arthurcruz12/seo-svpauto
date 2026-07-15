"""Add invoice lifecycle and normalized financial fields."""

from alembic import op
import sqlalchemy as sa

revision = "0002_document_financial_fields"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("financial_documents", sa.Column("document_number", sa.String(), nullable=True))
    op.add_column("financial_documents", sa.Column("net_amount", sa.Numeric(12, 2), nullable=False, server_default="0"))
    op.add_column("financial_documents", sa.Column("original_amount", sa.Numeric(12, 2), nullable=False, server_default="0"))
    op.add_column("financial_documents", sa.Column("due_date", sa.Date(), nullable=True))
    op.add_column("financial_documents", sa.Column("payment_method", sa.String(), nullable=True))
    op.add_column("financial_documents", sa.Column("is_paid", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.create_index("ix_financial_documents_document_number", "financial_documents", ["document_number"])
    op.create_unique_constraint(
        "uq_document_tenant_company_number",
        "financial_documents",
        ["tenant_id", "company_id", "document_number"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_document_tenant_company_number", "financial_documents", type_="unique")
    op.drop_index("ix_financial_documents_document_number", table_name="financial_documents")
    for column in ("is_paid", "payment_method", "due_date", "original_amount", "net_amount", "document_number"):
        op.drop_column("financial_documents", column)
