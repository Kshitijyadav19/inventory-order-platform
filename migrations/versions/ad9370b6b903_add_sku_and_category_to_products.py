from alembic import op
import sqlalchemy as sa


revision = 'ad9370b6b903'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:

    op.add_column(
        'products',
        sa.Column('sku', sa.String(50), nullable=False, server_default='OLD-PRODUCT')
    )

    op.add_column(
        'products',
        sa.Column('category', sa.String(100), nullable=False, server_default='General')
    )

    # Existing products ko unique SKU dena
    op.execute("""
        UPDATE products
        SET sku = 'OLD-' || id
    """)

    op.create_unique_constraint(
        'uq_products_sku',
        'products',
        ['sku']
    )


def downgrade() -> None:

    op.drop_constraint(
        'uq_products_sku',
        'products',
        type_='unique'
    )

    op.drop_column('products', 'category')
    op.drop_column('products', 'sku')