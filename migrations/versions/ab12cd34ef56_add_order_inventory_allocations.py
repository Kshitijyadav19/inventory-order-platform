"""add exact per-order inventory allocations

Revision ID: ab12cd34ef56
Revises: f1a2b3c4d5e6
"""
from alembic import op
import sqlalchemy as sa

revision = "ab12cd34ef56"
down_revision = "f1a2b3c4d5e6"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "order_inventory_allocations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("inventory_id", sa.Integer(), sa.ForeignKey("inventory.id"), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.CheckConstraint("quantity > 0", name="ck_order_inventory_allocations_quantity_positive"),
    )
    op.create_index("ix_order_inventory_allocations_order_id", "order_inventory_allocations", ["order_id"])
    op.create_index("ix_order_inventory_allocations_inventory_id", "order_inventory_allocations", ["inventory_id"])

def downgrade():
    op.drop_index("ix_order_inventory_allocations_inventory_id", table_name="order_inventory_allocations")
    op.drop_index("ix_order_inventory_allocations_order_id", table_name="order_inventory_allocations")
    op.drop_table("order_inventory_allocations")
