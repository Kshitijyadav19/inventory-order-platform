
"""add user ownership to orders

Revision ID: e7f8a9b0c1d2
Revises: ab12cd34ef56
"""
from alembic import op
import sqlalchemy as sa

revision = "e7f8a9b0c1d2"
down_revision = "ab12cd34ef56"
branch_labels = None
depends_on = None


def upgrade():
    # Add nullable column first to preserve existing orders.
    op.add_column(
        "orders",
        sa.Column("user_id", sa.Integer(), nullable=True)
    )

    # Assign existing orders to the confirmed test user.
    op.execute(
        "UPDATE orders SET user_id = 1 WHERE user_id IS NULL"
    )

    # Enforce ownership for all existing and future orders.
    op.alter_column(
        "orders",
        "user_id",
        existing_type=sa.Integer(),
        nullable=False
    )

    op.create_foreign_key(
        "fk_orders_user_id_users",
        "orders",
        "users",
        ["user_id"],
        ["id"]
    )

    op.create_index(
        "ix_orders_user_id",
        "orders",
        ["user_id"]
    )


def downgrade():
    op.drop_index("ix_orders_user_id", table_name="orders")
    op.drop_constraint(
        "fk_orders_user_id_users",
        "orders",
        type_="foreignkey"
    )
    op.drop_column("orders", "user_id")
