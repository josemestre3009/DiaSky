"""add structured customer details"""

from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("orders", sa.Column("customer_document", sa.String(32), nullable=True))
    op.add_column("orders", sa.Column("address", sa.Text(), nullable=True))
    op.add_column("orders", sa.Column("phones", sa.JSON(), nullable=True))
    op.add_column("orders", sa.Column("email", sa.String(255), nullable=True))
    op.add_column("orders", sa.Column("plan", sa.String(128), nullable=True))
    op.add_column("orders", sa.Column("installation_value", sa.String(64), nullable=True))


def downgrade() -> None:
    for column in ("installation_value", "plan", "email", "phones", "address", "customer_document"):
        op.drop_column("orders", column)
