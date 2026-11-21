from sqlalchemy import Column, Integer, String, Numeric, Boolean,ForeignKey,UniqueConstraint
from app.database import Base
from sqlalchemy import DateTime
from datetime import datetime



class Product(Base):

    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String(100), nullable=False)

    sku = Column(String(50), unique=True, nullable=False)

    category = Column(String(100), nullable=False)

    price = Column(Numeric(10, 2), nullable=False)

    stock_quantity = Column(Integer, nullable=False, default=0)

class Warehouse(Base):

    __tablename__ = "warehouses"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String(100), nullable=False)

    location = Column(String(200), nullable=False)

    is_active = Column(Boolean, default=True, nullable=False)   
class Inventory(Base):

    __tablename__ = "inventory"

    __table_args__ = (
        UniqueConstraint(
            "product_id",
            "warehouse_id",
            name="uq_product_warehouse"
        ),
    )

    id = Column(Integer, primary_key=True, index=True)

    product_id = Column(
        Integer,
        ForeignKey("products.id"),
        nullable=False
    )

    warehouse_id = Column(
        Integer,
        ForeignKey("warehouses.id"),
        nullable=False
    )

    quantity = Column(Integer, nullable=False, default=0)

class InventoryTransaction(Base):
    __tablename__ = "inventory_transactions"

    id = Column(Integer, primary_key=True, index=True)

    inventory_id = Column(
        Integer,
        ForeignKey("inventory.id"),
        nullable=False
    )

    transaction_type = Column(
        String(20),
        nullable=False
    )

    quantity = Column(Integer, nullable=False)

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

# -------------------------
# ORDER MODEL
# -------------------------

class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True
    )

    order_number = Column(
        String(50),
        unique=True,
        nullable=False
    )

    status = Column(
        String(30),
        default="PENDING",
        nullable=False
    )

    total_amount = Column(
        Numeric(10, 2),
        default=0,
        nullable=False
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )


# -------------------------
# ORDER ITEM MODEL
# -------------------------

class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)

    order_id = Column(
        Integer,
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False
    )

    product_id = Column(
        Integer,
        ForeignKey("products.id"),
        nullable=False
    )

    quantity = Column(
        Integer,
        nullable=False
    )

    unit_price = Column(
        Numeric(10, 2),
        nullable=False
    )

    subtotal = Column(
        Numeric(10, 2),
        nullable=False
    )

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(20), default="STAFF", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class Payment(Base):
    __tablename__ = "payments"
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, index=True)
    razorpay_order_id = Column(String(100), unique=True, nullable=False, index=True)
    razorpay_payment_id = Column(String(100), unique=True, nullable=True, index=True)
    amount_paise = Column(Integer, nullable=False)
    currency = Column(String(3), nullable=False, default="INR")
    status = Column(String(20), nullable=False, default="CREATED")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class OrderInventoryAllocation(Base):
    """Exact inventory quantities reserved by an order; used for safe cancellation."""
    __tablename__ = "order_inventory_allocations"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    inventory_id = Column(Integer, ForeignKey("inventory.id"), nullable=False, index=True)
    quantity = Column(Integer, nullable=False)
