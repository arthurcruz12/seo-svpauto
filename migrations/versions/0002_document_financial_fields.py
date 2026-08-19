"""Add invoice lifecycle and normalized financial fields."""

from alembic import op
import sqlalchemy as sa

revision = "0002_document_financial_fields"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # batch_alter_table uses SQLite's copy-and-move strategy when ALTER TABLE
    # cannot express an operation (for example adding a unique constraint),
    # while remaining compatible with PostgreSQL.
    with op.batch_alter_table("financial_documents") as batch_op:
        batch_op.add_column(sa.Column("document_number", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("net_amount", sa.Numeric(12, 2), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("original_amount", sa.Numeric(12, 2), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("due_date", sa.Date(), nullable=True))
        batch_op.add_column(sa.Column("payment_method", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("is_paid", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch_op.create_index("ix_financial_documents_document_number", ["document_number"])
        batch_op.create_unique_constraint(
            "uq_document_tenant_company_number",
            ["tenant_id", "company_id", "document_number"],
        )


def downgrade() -> None:
    with op.batch_alter_table("financial_documents") as batch_op:
        batch_op.drop_constraint("uq_document_tenant_company_number", type_="unique")
        batch_op.drop_index("ix_financial_documents_document_number")
        for column in ("is_paid", "payment_method", "due_date", "original_amount", "net_amount", "document_number"):
            batch_op.drop_column(column)
