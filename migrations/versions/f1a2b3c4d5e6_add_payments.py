from alembic import op
import sqlalchemy as sa
revision = "f1a2b3c4d5e6"
down_revision = "db5d734b16ac"
branch_labels = None
depends_on = None
def upgrade():
    op.create_table("payments", sa.Column("id",sa.Integer(),primary_key=True), sa.Column("order_id",sa.Integer(),sa.ForeignKey("orders.id"),nullable=False), sa.Column("razorpay_order_id",sa.String(100),nullable=False), sa.Column("razorpay_payment_id",sa.String(100),nullable=True), sa.Column("amount_paise",sa.Integer(),nullable=False), sa.Column("currency",sa.String(3),nullable=False,server_default="INR"), sa.Column("status",sa.String(20),nullable=False,server_default="CREATED"), sa.Column("created_at",sa.DateTime(),nullable=False))
    op.create_index("ix_payments_order_id","payments",["order_id"])
    op.create_index("ix_payments_razorpay_order_id","payments",["razorpay_order_id"],unique=True)
    op.create_index("ix_payments_razorpay_payment_id","payments",["razorpay_payment_id"],unique=True)
def downgrade():
    op.drop_table("payments")
