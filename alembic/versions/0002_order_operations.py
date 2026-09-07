"""add order operations metadata"""

from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    op.execute("ALTER TYPE orderstatus ADD VALUE IF NOT EXISTS 'COMPLETADA_PARCIAL'")
    columns = {column["name"] for column in inspector.get_columns("orders")}
    if "availability_note" not in columns:
        op.add_column("orders", sa.Column("availability_note", sa.Text(), nullable=True))
    if "requires_customer_confirmation" not in columns:
        op.add_column("orders", sa.Column("requires_customer_confirmation", sa.Boolean(), nullable=False, server_default=sa.false()))
    if "safety_risk" not in columns:
        op.add_column("orders", sa.Column("safety_risk", sa.Boolean(), nullable=False, server_default=sa.false()))
    if "order_assignments" in inspector.get_table_names():
        return
    op.create_table("order_assignments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id"), nullable=False),
        sa.Column("technician_name", sa.String(128), nullable=False),
        sa.Column("source_message_id", sa.String(255), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("order_id", "technician_name", "source_message_id"),
    )
    op.create_index("ix_order_assignments_order_id", "order_assignments", ["order_id"])


def downgrade() -> None:
    op.drop_index("ix_order_assignments_order_id", table_name="order_assignments")
    op.drop_table("order_assignments")
    op.drop_column("orders", "safety_risk")
    op.drop_column("orders", "requires_customer_confirmation")
    op.drop_column("orders", "availability_note")
