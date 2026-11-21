
import logging
import os
from dotenv import load_dotenv

load_dotenv()
from typing import Literal
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import jwt

from fastapi import FastAPI, Depends, HTTPException, UploadFile, File
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from pydantic import BaseModel, Field
from pwdlib import PasswordHash

from app.database import get_db
from app.models import (
    Product,
    Warehouse,
    Inventory,
    InventoryTransaction,
    Order,
    OrderItem,
    OrderInventoryAllocation,
    User
)


# -------------------------
# APPLICATION SETUP
# -------------------------

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Inventory Order Management System"
)

password_hasher = PasswordHash.recommended()


# -------------------------
# JWT CONFIGURATION
# -------------------------

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")

if not JWT_SECRET_KEY:
    raise RuntimeError("JWT_SECRET_KEY environment variable is missing")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")


# -------------------------
# PYDANTIC SCHEMAS
# -------------------------

class ProductCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    sku: str = Field(min_length=3, max_length=50)
    category: str = Field(min_length=2, max_length=100)
    price: float = Field(gt=0)
    stock_quantity: int = Field(default=0, ge=0)


class WarehouseCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    location: str = Field(min_length=2, max_length=200)


class InventoryCreate(BaseModel):
    product_id: int = Field(gt=0)
    warehouse_id: int = Field(gt=0)
    quantity: int = Field(ge=0)


class InventoryLocationUpdate(BaseModel):
    product_id: int = Field(gt=0)
    warehouse_id: int = Field(gt=0)


class StockMovement(BaseModel):
    inventory_id: int = Field(gt=0)
    transaction_type: Literal["STOCK_IN", "STOCK_OUT"]
    quantity: int = Field(gt=0)


class OrderItemCreate(BaseModel):
    product_id: int = Field(gt=0)
    quantity: int = Field(gt=0)


class OrderCreate(BaseModel):
    items: list[OrderItemCreate]


class UserRegister(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: str = Field(min_length=5, max_length=150)
    password: str = Field(min_length=8, max_length=128)


# -------------------------
# USER REGISTRATION API
# -------------------------

@app.post("/register", status_code=201)
def register_user(
    data: UserRegister,
    db: Session = Depends(get_db)
):
    email = data.email.strip().lower()
    name = data.name.strip()

    if not name:
        raise HTTPException(
            status_code=400,
            detail="Name cannot be empty"
        )

    if "@" not in email or "." not in email.split("@")[-1]:
        raise HTTPException(
            status_code=400,
            detail="Invalid email address"
        )

    try:
        existing_user = db.query(User).filter(
            User.email == email
        ).first()

        if existing_user:
            raise HTTPException(
                status_code=409,
                detail="Email already registered"
            )

        hashed_password = password_hasher.hash(data.password)

        new_user = User(
            name=name,
            email=email,
            hashed_password=hashed_password,
            role="STAFF"
        )

        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        return {
            "message": "User registered successfully",
            "user": {
                "id": new_user.id,
                "name": new_user.name,
                "email": new_user.email,
                "role": new_user.role
            }
        }

    except HTTPException:
        db.rollback()
        raise

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Email already registered"
        )

    except SQLAlchemyError:
        db.rollback()
        logger.exception("Database error during user registration")
        raise HTTPException(
            status_code=500,
            detail="Registration failed due to a database error"
        )

    except Exception:
        db.rollback()
        logger.exception("Unexpected error during user registration")
        raise HTTPException(
            status_code=500,
            detail="User registration failed"
        )


# -------------------------
# LOGIN API
# -------------------------

@app.post("/login")
def login_user(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    email = form_data.username.strip().lower()

    user = db.query(User).filter(
        User.email == email
    ).first()

    if user is None or not password_hasher.verify(
        form_data.password,
        user.hashed_password
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"}
        )

    if not user.is_active:
        raise HTTPException(
            status_code=403,
            detail="User account is inactive"
        )

    expire_time = datetime.now(timezone.utc) + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )

    payload = {
        "sub": str(user.id),
        "role": user.role,
        "exp": expire_time
    }

    access_token = jwt.encode(
        payload,
        JWT_SECRET_KEY,
        algorithm=ALGORITHM
    )

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }


# -------------------------
# GET CURRENT AUTHENTICATED USER
# -------------------------

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    credentials_error = HTTPException(
        status_code=401,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"}
    )

    try:
        payload = jwt.decode(
            token,
            JWT_SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        user_id = int(payload.get("sub"))

    except (jwt.InvalidTokenError, TypeError, ValueError):
        raise credentials_error

    user = db.query(User).filter(
        User.id == user_id
    ).first()

    if user is None or not user.is_active:
        raise credentials_error

    return user


# -------------------------
# PROTECTED PROFILE API
# -------------------------

@app.get("/me")
def get_my_profile(
    current_user: User = Depends(get_current_user)
):
    return {
        "id": current_user.id,
        "name": current_user.name,
        "email": current_user.email,
        "role": current_user.role
    }


# -------------------------
# HOME API
# -------------------------

@app.get("/")
def home():
    return {
        "message": "Inventory Order Management System"
    }


# -------------------------
# PRODUCT APIs
# -------------------------

@app.post("/products")
def create_product(
    product: ProductCreate,
    db: Session = Depends(get_db)
):
    new_product = Product(
        name=product.name,
        sku=product.sku,
        category=product.category,
        price=product.price,
        stock_quantity=product.stock_quantity
    )

    try:
        db.add(new_product)
        db.commit()
        db.refresh(new_product)

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="SKU already exists. Please use a unique SKU."
        )

    return {
        "message": "Product created successfully",
        "id": new_product.id,
        "name": new_product.name,
        "sku": new_product.sku,
        "category": new_product.category,
        "price": float(new_product.price),
        "stock_quantity": new_product.stock_quantity
    }


@app.get("/products")
def get_products(db: Session = Depends(get_db)):
    products = db.query(Product).all()

    return {
        "products": [
            {
                "id": p.id,
                "name": p.name,
                "sku": p.sku,
                "category": p.category,
                "price": float(p.price),
                "stock_quantity": p.stock_quantity
            }
            for p in products
        ]
    }


@app.get("/products/{product_id}")
def get_product(
    product_id: int,
    db: Session = Depends(get_db)
):
    product = db.query(Product).filter(
        Product.id == product_id
    ).first()

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found"
        )

    return {
        "id": product.id,
        "name": product.name,
        "sku": product.sku,
        "category": product.category,
        "price": float(product.price),
        "stock_quantity": product.stock_quantity
    }


@app.put("/products/{product_id}")
def update_product(
    product_id: int,
    product: ProductCreate,
    db: Session = Depends(get_db)
):
    existing_product = db.query(Product).filter(
        Product.id == product_id
    ).first()

    if existing_product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found"
        )

    existing_product.name = product.name
    existing_product.sku = product.sku
    existing_product.category = product.category
    existing_product.price = product.price
    existing_product.stock_quantity = product.stock_quantity

    try:
        db.commit()
        db.refresh(existing_product)

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="SKU already exists. Please use a unique SKU."
        )

    return {
        "message": "Product updated successfully",
        "id": existing_product.id,
        "name": existing_product.name,
        "sku": existing_product.sku,
        "category": existing_product.category,
        "price": float(existing_product.price),
        "stock_quantity": existing_product.stock_quantity
    }


@app.delete("/products/{product_id}")
def delete_product(
    product_id: int,
    db: Session = Depends(get_db)
):
    product = db.query(Product).filter(
        Product.id == product_id
    ).first()

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found"
        )

    inventory_exists = db.query(Inventory).filter(
        Inventory.product_id == product_id
    ).first()

    if inventory_exists:
        raise HTTPException(
            status_code=409,
            detail="Cannot delete product because inventory records exist"
        )

    db.delete(product)
    db.commit()

    return {
        "message": "Product deleted successfully"
    }


# -------------------------
# WAREHOUSE APIs
# -------------------------

@app.post("/warehouses")
def create_warehouse(
    warehouse: WarehouseCreate,
    db: Session = Depends(get_db)
):
    new_warehouse = Warehouse(
        name=warehouse.name,
        location=warehouse.location
    )

    db.add(new_warehouse)
    db.commit()
    db.refresh(new_warehouse)

    return {
        "message": "Warehouse created successfully",
        "warehouse": {
            "id": new_warehouse.id,
            "name": new_warehouse.name,
            "location": new_warehouse.location,
            "is_active": new_warehouse.is_active
        }
    }


@app.get("/warehouses")
def get_warehouses(db: Session = Depends(get_db)):
    warehouses = db.query(Warehouse).all()

    return {
        "warehouses": [
            {
                "id": w.id,
                "name": w.name,
                "location": w.location,
                "is_active": w.is_active
            }
            for w in warehouses
        ]
    }


@app.get("/warehouses/{warehouse_id}")
def get_warehouse(
    warehouse_id: int,
    db: Session = Depends(get_db)
):
    warehouse = db.query(Warehouse).filter(
        Warehouse.id == warehouse_id
    ).first()

    if warehouse is None:
        raise HTTPException(
            status_code=404,
            detail="Warehouse not found"
        )

    return {
        "id": warehouse.id,
        "name": warehouse.name,
        "location": warehouse.location,
        "is_active": warehouse.is_active
    }


@app.put("/warehouses/{warehouse_id}")
def update_warehouse(
    warehouse_id: int,
    warehouse: WarehouseCreate,
    db: Session = Depends(get_db)
):
    existing_warehouse = db.query(Warehouse).filter(
        Warehouse.id == warehouse_id
    ).first()

    if existing_warehouse is None:
        raise HTTPException(
            status_code=404,
            detail="Warehouse not found"
        )

    existing_warehouse.name = warehouse.name
    existing_warehouse.location = warehouse.location

    db.commit()
    db.refresh(existing_warehouse)

    return {
        "message": "Warehouse updated successfully",
        "id": existing_warehouse.id,
        "name": existing_warehouse.name,
        "location": existing_warehouse.location,
        "is_active": existing_warehouse.is_active
    }


@app.delete("/warehouses/{warehouse_id}")
def delete_warehouse(
    warehouse_id: int,
    db: Session = Depends(get_db)
):
    warehouse = db.query(Warehouse).filter(
        Warehouse.id == warehouse_id
    ).first()

    if warehouse is None:
        raise HTTPException(
            status_code=404,
            detail="Warehouse not found"
        )

    inventory_exists = db.query(Inventory).filter(
        Inventory.warehouse_id == warehouse_id
    ).first()

    if inventory_exists:
        raise HTTPException(
            status_code=409,
            detail="Cannot delete warehouse because inventory records exist"
        )

    db.delete(warehouse)
    db.commit()

    return {
        "message": "Warehouse deleted successfully"
    }


# -------------------------
# INVENTORY APIs
# -------------------------

@app.post("/inventory")
def create_inventory(
    inventory: InventoryCreate,
    db: Session = Depends(get_db)
):
    product = db.query(Product).filter(
        Product.id == inventory.product_id
    ).first()

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found"
        )

    warehouse = db.query(Warehouse).filter(
        Warehouse.id == inventory.warehouse_id
    ).first()

    if warehouse is None:
        raise HTTPException(
            status_code=404,
            detail="Warehouse not found"
        )

    new_inventory = Inventory(
        product_id=inventory.product_id,
        warehouse_id=inventory.warehouse_id,
        quantity=inventory.quantity
    )

    try:
        db.add(new_inventory)
        db.commit()
        db.refresh(new_inventory)

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Inventory already exists for this product and warehouse"
        )

    return {
        "message": "Inventory created successfully",
        "id": new_inventory.id,
        "product_id": new_inventory.product_id,
        "warehouse_id": new_inventory.warehouse_id,
        "quantity": new_inventory.quantity
    }


@app.get("/inventory")
def get_inventory(db: Session = Depends(get_db)):
    inventories = db.query(Inventory).all()

    return {
        "inventory": [
            {
                "id": item.id,
                "product_id": item.product_id,
                "warehouse_id": item.warehouse_id,
                "quantity": item.quantity
            }
            for item in inventories
        ]
    }


@app.get("/inventory/{inventory_id}")
def get_single_inventory(
    inventory_id: int,
    db: Session = Depends(get_db)
):
    item = db.query(Inventory).filter(
        Inventory.id == inventory_id
    ).first()

    if item is None:
        raise HTTPException(
            status_code=404,
            detail="Inventory not found"
        )

    return {
        "id": item.id,
        "product_id": item.product_id,
        "warehouse_id": item.warehouse_id,
        "quantity": item.quantity
    }


@app.put("/inventory/{inventory_id}")
def update_inventory(
    inventory_id: int,
    inventory: InventoryLocationUpdate,
    db: Session = Depends(get_db)
):
    existing_inventory = db.query(Inventory).filter(
        Inventory.id == inventory_id
    ).first()

    if existing_inventory is None:
        raise HTTPException(
            status_code=404,
            detail="Inventory not found"
        )

    product = db.query(Product).filter(
        Product.id == inventory.product_id
    ).first()

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found"
        )

    warehouse = db.query(Warehouse).filter(
        Warehouse.id == inventory.warehouse_id
    ).first()

    if warehouse is None:
        raise HTTPException(
            status_code=404,
            detail="Warehouse not found"
        )

    existing_inventory.product_id = inventory.product_id
    existing_inventory.warehouse_id = inventory.warehouse_id

    try:
        db.commit()
        db.refresh(existing_inventory)

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Inventory already exists for this product and warehouse"
        )

    return {
        "message": "Inventory updated successfully",
        "id": existing_inventory.id,
        "product_id": existing_inventory.product_id,
        "warehouse_id": existing_inventory.warehouse_id,
        "quantity": existing_inventory.quantity
    }


@app.delete("/inventory/{inventory_id}")
def delete_inventory(
    inventory_id: int,
    db: Session = Depends(get_db)
):
    inventory = db.query(Inventory).filter(
        Inventory.id == inventory_id
    ).first()

    if inventory is None:
        raise HTTPException(
            status_code=404,
            detail="Inventory not found"
        )

    transaction_exists = db.query(InventoryTransaction).filter(
        InventoryTransaction.inventory_id == inventory_id
    ).first()

    if transaction_exists:
        raise HTTPException(
            status_code=409,
            detail="Cannot delete inventory because transaction history exists"
        )

    db.delete(inventory)
    db.commit()

    return {
        "message": "Inventory deleted successfully"
    }


# -------------------------
# CREATE ORDER API
# -------------------------

@app.post("/orders")
def create_order(
    data: OrderCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    
    if not data.items:
        raise HTTPException(
            status_code=400,
            detail="Order must contain at least one item"
        )

    try:
        total_amount = Decimal("0.00")
        order_items_data = []
        requested_quantities = {}

        for item in data.items:
            requested_quantities[item.product_id] = (
                requested_quantities.get(item.product_id, 0)
                + item.quantity
            )

        inventory_rows = {}
        products = {}

        for product_id, required_quantity in requested_quantities.items():

            product = db.query(Product).filter(
                Product.id == product_id
            ).first()

            if product is None:
                raise HTTPException(
                    status_code=404,
                    detail=f"Product {product_id} not found"
                )

            products[product_id] = product

            inventories = db.query(Inventory).filter(
                Inventory.product_id == product_id
            ).order_by(
                Inventory.id
            ).with_for_update().all()

            available_quantity = sum(
                row.quantity for row in inventories
            )

            if available_quantity < required_quantity:
                raise HTTPException(
                    status_code=400,
                    detail=f"Insufficient stock for product {product_id}"
                )

            inventory_rows[product_id] = inventories

        for item in data.items:
            product = products[item.product_id]

            subtotal = product.price * item.quantity
            total_amount += subtotal

            order_items_data.append({
                "product_id": product.id,
                "quantity": item.quantity,
                "unit_price": product.price,
                "subtotal": subtotal
            })

        order = Order(
        order_number=f"ORD-{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
        user_id=current_user.id,
        total_amount=total_amount,
        status="PENDING"
    )
        
        db.add(order)
        db.flush()

        for product_id, required_quantity in requested_quantities.items():

            remaining_quantity = required_quantity

            for inventory in inventory_rows[product_id]:

                if remaining_quantity <= 0:
                    break

                deducted_quantity = min(
                    inventory.quantity,
                    remaining_quantity
                )

                if deducted_quantity == 0:
                    continue

                inventory.quantity -= deducted_quantity
                remaining_quantity -= deducted_quantity

                db.add(
                    InventoryTransaction(
                        inventory_id=inventory.id,
                        transaction_type="STOCK_OUT",
                        quantity=deducted_quantity
                    )
                )
                db.add(
                    OrderInventoryAllocation(
                        order_id=order.id,
                        inventory_id=inventory.id,
                        quantity=deducted_quantity
                    )
                )

        for item_data in order_items_data:
            db.add(
                OrderItem(
                    order_id=order.id,
                    **item_data
                )
            )

        db.commit()
        db.refresh(order)

        return {
            "message": "Order created successfully",
            "order_id": order.id,
            "order_number": order.order_number,
            "status": order.status,
            "total_amount": float(order.total_amount),
            "items": [
                {
                    "product_id": item["product_id"],
                    "quantity": item["quantity"],
                    "unit_price": float(item["unit_price"]),
                    "subtotal": float(item["subtotal"])
                }
                for item in order_items_data
            ]
        }

    except HTTPException:
        db.rollback()
        raise

    except SQLAlchemyError:
        db.rollback()
        logger.exception("Order creation database error")
        raise HTTPException(
            status_code=500,
            detail="Order creation failed"
        )


# -------------------------
# GET ALL ORDERS
# -------------------------

@app.get("/orders")
def get_all_orders(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    orders = db.query(Order).filter(
        Order.user_id == current_user.id
    ).order_by(
        Order.id.desc()
    ).all()

    return {
        "total_orders": len(orders),
        "orders": [
            {
                "order_id": order.id,
                "order_number": order.order_number,
                "status": order.status,
                "total_amount": float(order.total_amount),
                "created_at": order.created_at.isoformat()
            }
            for order in orders
        ]
    }


# -------------------------
# GET SINGLE ORDER DETAILS
# -------------------------
@app.get("/orders/{order_id}")
def get_order_details(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    order = db.query(Order).filter(
        Order.id == order_id,
        Order.user_id == current_user.id
    ).first()

    if order is None:
        raise HTTPException(
            status_code=404,
            detail="Order not found"
        )

    items = db.query(OrderItem).filter(
        OrderItem.order_id == order_id
    ).all()

    return {
        "order_id": order.id,
        "order_number": order.order_number,
        "status": order.status,
        "total_amount": float(order.total_amount),
        "created_at": order.created_at.isoformat(),
        "items": [
            {
                "product_id": item.product_id,
                "quantity": item.quantity,
                "unit_price": float(item.unit_price),
                "subtotal": float(item.subtotal)
            }
            for item in items
        ]
    }

     
# -------------------------
# CANCEL ORDER API
# -------------------------
@app.post("/orders/{order_id}/cancel")
def cancel_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        order = db.query(Order).filter(
            Order.id == order_id,
            Order.user_id == current_user.id
        ).with_for_update().first()

        if order is None:
            raise HTTPException(
                status_code=404,
                detail="Order not found"
            )

        if order.status != "PENDING":
            raise HTTPException(
                status_code=409,
                detail="Only PENDING orders can be cancelled"
            )

        allocations = db.query(OrderInventoryAllocation).filter(
            OrderInventoryAllocation.order_id == order_id
        ).with_for_update().all()

        if not allocations:
            raise HTTPException(
                status_code=409,
                detail="No reservation records found"
            )

        restored_stock = 0

        for allocation in allocations:
            inventory = db.query(Inventory).filter(
                Inventory.id == allocation.inventory_id
            ).with_for_update().first()

            if inventory is None:
                raise HTTPException(
                    status_code=409,
                    detail="Inventory record no longer exists"
                )

            inventory.quantity += allocation.quantity
            restored_stock += allocation.quantity

            db.add(
                InventoryTransaction(
                    inventory_id=inventory.id,
                    transaction_type="STOCK_IN",
                    quantity=allocation.quantity
                )
            )

        order.status = "CANCELLED"

        db.commit()
        db.refresh(order)

        return {
            "message": "Order cancelled successfully",
            "order_id": order.id,
            "status": order.status,
            "restored_stock_units": restored_stock
        }

    except HTTPException:
        db.rollback()
        raise

    except SQLAlchemyError:
        db.rollback()
        logger.exception("Order cancellation failed")
        raise HTTPException(
            status_code=500,
            detail="Order cancellation failed"
        )


# -------------------------
# STOCK MOVEMENT API
# -------------------------

@app.post("/inventory/movement")
def stock_movement(
    data: StockMovement,
    db: Session = Depends(get_db)
):
    try:
        inventory = db.query(Inventory).filter(
            Inventory.id == data.inventory_id
        ).with_for_update().first()

        if inventory is None:
            raise HTTPException(
                status_code=404,
                detail="Inventory not found"
            )

        if data.transaction_type == "STOCK_OUT":

            if inventory.quantity < data.quantity:
                raise HTTPException(
                    status_code=400,
                    detail="Insufficient stock"
                )

            inventory.quantity -= data.quantity

        elif data.transaction_type == "STOCK_IN":
            inventory.quantity += data.quantity

        transaction = InventoryTransaction(
            inventory_id=inventory.id,
            transaction_type=data.transaction_type,
            quantity=data.quantity
        )

        db.add(transaction)
        db.commit()

        db.refresh(inventory)
        db.refresh(transaction)

        return {
            "message": "Stock movement successful",
            "inventory_id": inventory.id,
            "transaction_type": transaction.transaction_type,
            "quantity_changed": transaction.quantity,
            "current_stock": inventory.quantity
        }

    except HTTPException:
        db.rollback()
        raise

    except SQLAlchemyError:
        db.rollback()
        logger.exception("Stock movement database error")
        raise HTTPException(
            status_code=500,
            detail="Stock movement failed"
        )


# -------------------------
# INVENTORY TRANSACTION HISTORY
# -------------------------

@app.get("/inventory/{inventory_id}/transactions")
def get_inventory_transactions(
    inventory_id: int,
    db: Session = Depends(get_db)
):
    inventory = db.query(Inventory).filter(
        Inventory.id == inventory_id
    ).first()

    if inventory is None:
        raise HTTPException(
            status_code=404,
            detail="Inventory not found"
        )

    transactions = db.query(InventoryTransaction).filter(
        InventoryTransaction.inventory_id == inventory_id
    ).order_by(
        InventoryTransaction.created_at.desc(),
        InventoryTransaction.id.desc()
    ).all()

    return {
        "inventory_id": inventory_id,
        "current_stock": inventory.quantity,
        "total_transactions": len(transactions),
        "transactions": [
            {
                "id": transaction.id,
                "transaction_type": transaction.transaction_type,
                "quantity": transaction.quantity,
                "created_at": transaction.created_at.isoformat()
            }
            for transaction in transactions
        ]
    }


# -------------------------
# RAZORPAY PAYMENTS (TEST/LIVE KEYS VIA ENV)
# -------------------------
import json
from app.payment_security import verify_checkout_signature, verify_webhook_signature
from fastapi import Request, Header
from app.models import Payment
from app.storage import upload_private_file, create_private_download_url

class PaymentVerify(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str

@app.post("/orders/{order_id}/payments/razorpay", status_code=201)
def create_razorpay_payment(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    key_id = os.getenv("RAZORPAY_KEY_ID")
    key_secret = os.getenv("RAZORPAY_KEY_SECRET")

    if not key_id or not key_secret:
        raise HTTPException(
            status_code=503,
            detail="Razorpay keys are not configured"
        )

    try:
        order = (
            db.query(Order)
            .filter(
                Order.id == order_id,
                Order.user_id == current_user.id
            )
            .with_for_update()
            .first()
        )

        if not order:
            raise HTTPException(
                status_code=404,
                detail="Order not found"
            )

        if order.status != "PENDING":
            raise HTTPException(
                status_code=409,
                detail="Only pending orders can be paid"
            )

        existing = (
            db.query(Payment)
            .filter(
                Payment.order_id == order.id,
                Payment.status == "CREATED"
            )
            .first()
        )

        if existing:
            return {
                "razorpay_key_id": key_id,
                "razorpay_order_id": existing.razorpay_order_id,
                "amount": existing.amount_paise,
                "currency": existing.currency,
                "payment_id": existing.id
            }

        import razorpay

        client = razorpay.Client(
            auth=(key_id, key_secret)
        )

        amount = int(Decimal(str(order.total_amount)) * 100)

        if amount <= 0:
            raise HTTPException(
                status_code=400,
                detail="Invalid order amount"
            )

        razorpay_order = client.order.create({
            "amount": amount,
            "currency": "INR",
            "receipt": order.order_number,
            "notes": {
                "internal_order_id": str(order.id),
                "user_id": str(current_user.id)
            }
        })

        payment = Payment(
            order_id=order.id,
            razorpay_order_id=razorpay_order["id"],
            amount_paise=amount,
            currency="INR",
            status="CREATED"
        )

        db.add(payment)
        db.commit()
        db.refresh(payment)

        return {
            "razorpay_key_id": key_id,
            "razorpay_order_id": razorpay_order["id"],
            "amount": amount,
            "currency": "INR",
            "payment_id": payment.id
        }

    except HTTPException:
        db.rollback()
        raise

    except Exception:
        db.rollback()
        logger.exception("Razorpay order creation failed")

        raise HTTPException(
            status_code=502,
            detail="Unable to create Razorpay order"
        )

@app.post("/payments/razorpay/verify")
def verify_razorpay_payment(
    data: PaymentVerify,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    key_id = os.getenv("RAZORPAY_KEY_ID")
    key_secret = os.getenv("RAZORPAY_KEY_SECRET")

    if not key_id or not key_secret:
        raise HTTPException(
            status_code=503,
            detail="Razorpay is not configured"
        )

    try:
        # 1. Verify checkout signature
        if not verify_checkout_signature(
            data.razorpay_order_id,
            data.razorpay_payment_id,
            data.razorpay_signature,
            key_secret
        ):
            raise HTTPException(
                status_code=400,
                detail="Invalid payment signature"
            )

        # 2. Find and lock payment
        payment = (
            db.query(Payment)
            .filter(
                Payment.razorpay_order_id == data.razorpay_order_id
            )
            .with_for_update()
            .first()
        )

        if not payment:
            raise HTTPException(
                status_code=404,
                detail="Payment order not found"
            )

        # 3. Find and lock associated order
        order = (
            db.query(Order)
            .filter(
                Order.id == payment.order_id,
                Order.user_id == current_user.id
            )
            .with_for_update()
            .first()
        )

        if not order:
            raise HTTPException(
                status_code=404,
                detail="Order not found"
            )

        # 4. Prevent payment ID mismatch
        if (
            payment.razorpay_payment_id
            and payment.razorpay_payment_id != data.razorpay_payment_id
        ):
            raise HTTPException(
                status_code=409,
                detail="Payment already linked to another payment ID"
            )

        # 5. Idempotency check
        if payment.status == "PAID" and order.status == "PAID":
            return {
                "message": "Payment already verified",
                "payment_status": payment.status,
                "order_status": order.status
            }

        if payment.status != "CREATED":
            raise HTTPException(
                status_code=409,
                detail="Payment is not in CREATED state"
            )

        if order.status != "PENDING":
            raise HTTPException(
                status_code=409,
                detail="Order is not in PENDING state"
            )

        # 6. Fetch actual payment from Razorpay
        import razorpay

        client = razorpay.Client(
            auth=(key_id, key_secret)
        )

        razorpay_payment = client.payment.fetch(
            data.razorpay_payment_id
        )

        # 7. Validate Razorpay payment details
        if razorpay_payment.get("order_id") != payment.razorpay_order_id:
            raise HTTPException(
                status_code=400,
                detail="Razorpay order ID mismatch"
            )

        if int(razorpay_payment.get("amount", 0)) != payment.amount_paise:
            raise HTTPException(
                status_code=400,
                detail="Payment amount mismatch"
            )

        if razorpay_payment.get("currency") != payment.currency:
            raise HTTPException(
                status_code=400,
                detail="Payment currency mismatch"
            )

        if razorpay_payment.get("status") != "captured":
            raise HTTPException(
                status_code=400,
                detail="Payment has not been captured"
            )

        # 8. Update payment and order
        payment.razorpay_payment_id = data.razorpay_payment_id
        payment.status = "PAID"
        order.status = "PAID"

        db.commit()

        return {
            "message": "Payment verified successfully",
            "payment_status": payment.status,
            "order_status": order.status
        }

    except HTTPException:
        db.rollback()
        raise

    except Exception:
        db.rollback()
        logger.exception("Razorpay payment verification failed")

        raise HTTPException(
            status_code=502,
            detail="Unable to verify Razorpay payment"
        )

@app.post("/webhooks/razorpay")
async def razorpay_webhook(
    request: Request,
    x_razorpay_signature: str = Header(default=""),
    db: Session = Depends(get_db)
):
    secret = os.getenv("RAZORPAY_WEBHOOK_SECRET")

    if not secret:
        raise HTTPException(
            status_code=503,
            detail="Webhook secret is not configured"
        )

    body = await request.body()

    # 1. Verify webhook signature
    if not verify_webhook_signature(
        body,
        x_razorpay_signature,
        secret
    ):
        raise HTTPException(
            status_code=400,
            detail="Invalid webhook signature"
        )

    # 2. Parse JSON
    try:
        event = json.loads(body)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=400,
            detail="Invalid webhook JSON"
        )

    event_type = event.get("event")

    # Ignore events we do not process
    if event_type not in ("payment.captured", "payment.failed"):
        return {"received": True, "message": "Event ignored"}

    try:
        entity = (
            event.get("payload", {})
            .get("payment", {})
            .get("entity", {})
        )

        if not isinstance(entity, dict):
            raise HTTPException(
                status_code=400,
                detail="Invalid payment entity"
            )

        razorpay_order_id = entity.get("order_id")
        razorpay_payment_id = entity.get("id")

        if not razorpay_order_id or not razorpay_payment_id:
            raise HTTPException(
                status_code=400,
                detail="Missing Razorpay payment identifiers"
            )

        # 3. Lock payment record
        payment = (
            db.query(Payment)
            .filter(
                Payment.razorpay_order_id == razorpay_order_id
            )
            .with_for_update()
            .first()
        )

        if not payment:
            raise HTTPException(
                status_code=404,
                detail="Payment record not found"
            )

        # 4. Prevent payment ID mismatch
        if (
            payment.razorpay_payment_id
            and payment.razorpay_payment_id != razorpay_payment_id
        ):
            raise HTTPException(
                status_code=409,
                detail="Payment ID mismatch"
            )

        # 5. Lock associated order
        order = (
            db.query(Order)
            .filter(Order.id == payment.order_id)
            .with_for_update()
            .first()
        )

        if not order:
            raise HTTPException(
                status_code=404,
                detail="Associated order not found"
            )

        # 6. Handle captured payment
        if event_type == "payment.captured":

            if entity.get("status") != "captured":
                raise HTTPException(
                    status_code=400,
                    detail="Payment is not captured"
                )

            if int(entity.get("amount", -1)) != payment.amount_paise:
                raise HTTPException(
                    status_code=400,
                    detail="Payment amount mismatch"
                )

            if entity.get("currency") != payment.currency:
                raise HTTPException(
                    status_code=400,
                    detail="Payment currency mismatch"
                )

            # Idempotency
            if payment.status == "PAID" and order.status == "PAID":
                db.rollback()
                return {
                    "received": True,
                    "message": "Payment already processed"
                }

            if payment.status != "CREATED":
                raise HTTPException(
                    status_code=409,
                    detail="Payment is not in CREATED state"
                )

            if order.status != "PENDING":
                raise HTTPException(
                    status_code=409,
                    detail="Order is not in PENDING state"
                )

            payment.razorpay_payment_id = razorpay_payment_id
            payment.status = "PAID"
            order.status = "PAID"

        # 7. Handle failed payment
        elif event_type == "payment.failed":

            if payment.status == "PAID":
                db.rollback()
                return {
                    "received": True,
                    "message": "Already paid; failure event ignored"
                }

            if payment.status == "CREATED":
                payment.razorpay_payment_id = razorpay_payment_id
                payment.status = "FAILED"

        db.commit()

        return {
            "received": True,
            "event": event_type,
            "payment_status": payment.status,
            "order_status": order.status
        }

    except HTTPException:
        db.rollback()
        raise

    except Exception:
        db.rollback()
        logger.exception("Razorpay webhook processing failed")

        raise HTTPException(
            status_code=500,
            detail="Webhook processing failed"
        )


# -------------------------
# OPTIONAL PRIVATE AWS S3 TESTING (NO APP DEPLOYMENT)
# -------------------------
@app.post("/files/s3", status_code=201)
async def upload_file_to_s3(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    return await upload_private_file(file, current_user.id)

@app.get("/files/s3/download-url")
def get_s3_download_url(
    key: str,
    current_user: User = Depends(get_current_user),
):
    return create_private_download_url(key, current_user.id)
