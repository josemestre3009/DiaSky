"""add structured customer details"""

from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("orders")}
    additions = (
        ("customer_document", sa.String(32)),
        ("address", sa.Text()),
        ("phones", sa.JSON()),
        ("email", sa.String(255)),
        ("plan", sa.String(128)),
        ("installation_value", sa.String(64)),
    )
    for name, column_type in additions:
        if name not in columns:
            op.add_column("orders", sa.Column(name, column_type, nullable=True))


def downgrade() -> None:
    for column in ("installation_value", "plan", "email", "phones", "address", "customer_document"):
        op.drop_column("orders", column)
