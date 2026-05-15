from datetime import datetime, timedelta
from extensions import db

def now():
    return datetime.utcnow()

class Role(db.Model):
    __tablename__ = "roles"

    role_id     = db.Column("role_id", db.Integer, primary_key=True)
    role_name   = db.Column("role_name", db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(255))
    permissions = db.Column(db.JSON, nullable=False, default=dict)
    created_at  = db.Column(db.DateTime, default=now)

    users = db.relationship("User", back_populates="role", lazy="dynamic")

    def has_permission(self, permission: str) -> bool:
        perms = self.permissions or {}
        return perms.get(permission, False)

    def to_dict(self):
        return {"id": self.role_id, "name": self.role_name,
                "description": self.description, "permissions": self.permissions}

class User(db.Model):
    __tablename__ = "users"

    user_id         = db.Column("user_id", db.BigInteger, primary_key=True)
    username        = db.Column("username", db.String(50), unique=True, nullable=False)
    email           = db.Column("email", db.String(120), unique=True, nullable=False)
    password_hash   = db.Column("password_hash", db.String(255), nullable=False)
    full_name       = db.Column("full_name", db.String(100), nullable=False)
    phone           = db.Column("phone", db.String(20))
    role_id         = db.Column("role_id", db.Integer, db.ForeignKey("roles.role_id"), nullable=False)
    is_active       = db.Column("is_active", db.Boolean, default=True, nullable=False)
    last_login      = db.Column("last_login", db.DateTime)
    failed_attempts = db.Column("failed_attempts", db.SmallInteger, default=0)
    locked_until    = db.Column("locked_until", db.DateTime)
    created_at      = db.Column(db.DateTime, default=now)
    updated_at      = db.Column(db.DateTime, default=now, onupdate=now)
    deleted_at      = db.Column("deleted_at", db.DateTime)

    role          = db.relationship("Role", back_populates="users")
    notifications = db.relationship("Notification", back_populates="user", lazy="dynamic")

    @classmethod
    def active(cls):
        return cls.query.filter(cls.deleted_at.is_(None), cls.is_active == True)

    def soft_delete(self):
        self.deleted_at = now()
        self.is_active  = False

    def is_locked(self):
        return self.locked_until is not None and datetime.utcnow() < self.locked_until

    def register_failed_login(self, max_attempts, lockout_minutes):
        self.failed_attempts += 1
        if self.failed_attempts >= max_attempts:
            self.locked_until    = datetime.utcnow() + timedelta(minutes=lockout_minutes)
            self.failed_attempts = 0

    def clear_login_failures(self):
        self.failed_attempts = 0
        self.locked_until    = None
        self.last_login      = now()

    def to_dict(self):
        return {
            "id":        self.user_id,
            "username":  self.username,
            "role_id":   self.role_id,
            "role":      self.role.role_name if self.role else None,
            "full_name": self.full_name,
            "email":     self.email,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

class TokenBlocklist(db.Model):
    __tablename__ = "token_blocklist"

    jti        = db.Column("jti", db.String(36), primary_key=True)
    user_id    = db.Column("user_id", db.BigInteger, db.ForeignKey("users.user_id"), nullable=False)
    expires_at = db.Column("expires_at", db.DateTime, nullable=False)
    revoked_at = db.Column("revoked_at", db.DateTime, default=now)

class Warehouse(db.Model):
    __tablename__ = "warehouses"

    warehouse_id   = db.Column("warehouse_id", db.Integer, primary_key=True)
    code           = db.Column("code", db.String(20), unique=True, nullable=False)
    name           = db.Column("name", db.String(100), nullable=False)
    address        = db.Column("address", db.String(255))
    city           = db.Column("city", db.String(60))
    country        = db.Column("country", db.String(60), default="Pakistan")
    capacity_units = db.Column("capacity_units", db.Integer, default=10000)
    manager_id     = db.Column("manager_id", db.BigInteger, db.ForeignKey("users.user_id", ondelete="SET NULL"))
    is_active      = db.Column("is_active", db.Boolean, default=True)
    created_at     = db.Column(db.DateTime, default=now)
    updated_at     = db.Column(db.DateTime, default=now, onupdate=now)
    deleted_at     = db.Column("deleted_at", db.DateTime)

    manager   = db.relationship("User", foreign_keys=[manager_id])
    inventory = db.relationship("Inventory", back_populates="warehouse", lazy="dynamic")

    @classmethod
    def active(cls):
        return cls.query.filter(cls.deleted_at.is_(None))

    def soft_delete(self):
        self.deleted_at = now()

    def to_dict(self):
        return {"id": self.warehouse_id, "code": self.code, "name": self.name,
                "city": self.city, "capacity": self.capacity_units, "manager_id": self.manager_id}

class Category(db.Model):
    __tablename__ = "categories"

    category_id = db.Column("category_id", db.Integer, primary_key=True)
    name        = db.Column("name", db.String(80), nullable=False)
    description = db.Column("description", db.String(255))
    parent_id   = db.Column("parent_id", db.Integer, db.ForeignKey("categories.category_id", ondelete="SET NULL"))
    created_at  = db.Column(db.DateTime, default=now)
    deleted_at  = db.Column("deleted_at", db.DateTime)

    parent   = db.relationship("Category", remote_side=[category_id])
    products = db.relationship("Product", back_populates="category", lazy="dynamic")

    @classmethod
    def active(cls):
        return cls.query.filter(cls.deleted_at.is_(None))

    def to_dict(self):
        return {"id": self.category_id, "name": self.name, "parent_id": self.parent_id}

class Supplier(db.Model):
    __tablename__ = "suppliers"

    supplier_id    = db.Column("supplier_id", db.Integer, primary_key=True)
    code           = db.Column("code", db.String(20), unique=True, nullable=False)
    name           = db.Column("name", db.String(120), nullable=False)
    contact_person = db.Column("contact_person", db.String(100))
    email          = db.Column("email", db.String(120))
    phone          = db.Column("phone", db.String(20))
    address        = db.Column("address", db.String(255))
    city           = db.Column("city", db.String(60))
    rating         = db.Column("rating", db.Numeric(3, 2), default=0.00)
    total_orders   = db.Column("total_orders", db.Integer, default=0)
    on_time_orders = db.Column("on_time_orders", db.Integer, default=0)
    is_active      = db.Column("is_active", db.Boolean, default=True)
    created_at     = db.Column(db.DateTime, default=now)
    updated_at     = db.Column(db.DateTime, default=now, onupdate=now)
    deleted_at     = db.Column("deleted_at", db.DateTime)

    purchase_orders = db.relationship("SupplierOrder", back_populates="supplier", lazy="dynamic")

    @classmethod
    def active(cls):
        return cls.query.filter(cls.deleted_at.is_(None))

    def soft_delete(self):
        self.deleted_at = now()

    def on_time_rate(self):
        if not self.total_orders:
            return 0.0
        return round(self.on_time_orders / self.total_orders * 100, 2)

    def to_dict(self):
        return {
            "id": self.supplier_id, "code": self.code, "name": self.name,
            "contact_person": self.contact_person, "email": self.email, "phone": self.phone,
            "rating": float(self.rating or 0),
            "total_orders": self.total_orders, "on_time_orders": self.on_time_orders,
            "on_time_rate": self.on_time_rate(),
        }

class Product(db.Model):
    __tablename__ = "products"

    product_id          = db.Column("product_id", db.BigInteger, primary_key=True)
    sku                 = db.Column("sku", db.String(40), unique=True, nullable=False)
    barcode             = db.Column("barcode", db.String(50), unique=True)
    name                = db.Column("name", db.String(150), nullable=False)
    description         = db.Column("description", db.Text)
    category_id         = db.Column("category_id", db.Integer, db.ForeignKey("categories.category_id"))
    primary_supplier_id = db.Column("primary_supplier_id", db.Integer, db.ForeignKey("suppliers.supplier_id"))
    unit_price          = db.Column("unit_price", db.Numeric(12, 2), nullable=False)
    cost_price          = db.Column("cost_price", db.Numeric(12, 2), nullable=False, default=0)
    reorder_level       = db.Column("reorder_level", db.Integer, default=10)
    reorder_quantity    = db.Column("reorder_quantity", db.Integer, default=50)
    is_active           = db.Column("is_active", db.Boolean, default=True)
    created_at          = db.Column(db.DateTime, default=now)
    updated_at          = db.Column(db.DateTime, default=now, onupdate=now)
    deleted_at          = db.Column("deleted_at", db.DateTime)

    category  = db.relationship("Category", back_populates="products")
    supplier  = db.relationship("Supplier", foreign_keys=[primary_supplier_id])
    inventory = db.relationship("Inventory", back_populates="product", lazy="dynamic")
    order_items = db.relationship("OrderItem", back_populates="product", lazy="dynamic")

    @classmethod
    def active(cls):
        return cls.query.filter(cls.deleted_at.is_(None))

    def soft_delete(self):
        self.deleted_at = now()

    def total_stock(self):
        result = db.session.query(db.func.sum(Inventory.quantity)).filter_by(product_id=self.product_id).scalar()
        return int(result or 0)

    def to_dict(self, include_stock=False):
        d = {
            "id": self.product_id, "sku": self.sku, "barcode": self.barcode,
            "name": self.name, "description": self.description,
            "unit_price": float(self.unit_price),
            "cost_price": float(self.cost_price or 0),
            "reorder_level": self.reorder_level,
            "category_id": self.category_id,
            "category": self.category.name if self.category else None,
            "supplier_id": self.primary_supplier_id,
            "supplier": self.supplier.name if self.supplier else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        if include_stock:
            d["total_stock"] = self.total_stock()
        return d

class Inventory(db.Model):
    __tablename__ = "inventory"
    __table_args__ = (
        db.UniqueConstraint("product_id", "warehouse_id", name="uq_product_warehouse"),
    )

    inventory_id   = db.Column("inventory_id", db.BigInteger, primary_key=True)
    product_id     = db.Column("product_id", db.BigInteger, db.ForeignKey("products.product_id"), nullable=False)
    warehouse_id   = db.Column("warehouse_id", db.Integer, db.ForeignKey("warehouses.warehouse_id"), nullable=False)
    quantity       = db.Column("quantity", db.Integer, default=0, nullable=False)
    reserved_qty   = db.Column("reserved_qty", db.Integer, default=0, nullable=False)
    last_restocked = db.Column("last_restocked", db.DateTime)
    updated_at     = db.Column(db.DateTime, default=now, onupdate=now)

    product   = db.relationship("Product", back_populates="inventory")
    warehouse = db.relationship("Warehouse", back_populates="inventory")

    @property
    def available(self):
        return max(0, self.quantity - self.reserved_qty)

    def to_dict(self):
        return {
            "id": self.inventory_id,
            "product_id": self.product_id,
            "product_name": self.product.name if self.product else None,
            "sku": self.product.sku if self.product else None,
            "warehouse_id": self.warehouse_id,
            "warehouse_name": self.warehouse.name if self.warehouse else None,
            "quantity": self.quantity,
            "reserved_qty": self.reserved_qty,
            "available": self.available,
            "reorder_level": self.product.reorder_level if self.product else 0,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

class StockMovement(db.Model):
    __tablename__ = "stock_movements"

    TYPES = ("IN", "OUT", "TRANSFER", "ADJUSTMENT", "RESERVE", "RELEASE")

    movement_id    = db.Column("movement_id", db.BigInteger, primary_key=True)
    product_id     = db.Column("product_id", db.BigInteger, db.ForeignKey("products.product_id"), nullable=False)
    warehouse_id   = db.Column("warehouse_id", db.Integer, db.ForeignKey("warehouses.warehouse_id"), nullable=False)
    movement_type  = db.Column("movement_type", db.Enum(*TYPES), nullable=False)
    quantity       = db.Column("quantity", db.Integer, nullable=False)
    reference_type = db.Column("reference_type", db.String(30))
    reference_id   = db.Column("reference_id", db.BigInteger)
    notes          = db.Column("notes", db.String(255))
    performed_by   = db.Column("performed_by", db.BigInteger, db.ForeignKey("users.user_id"), nullable=False)
    created_at     = db.Column(db.DateTime, default=now)

    product   = db.relationship("Product")
    warehouse = db.relationship("Warehouse")
    user      = db.relationship("User", foreign_keys=[performed_by])

    def to_dict(self):
        return {
            "id": self.movement_id,
            "product_id": self.product_id,
            "product": self.product.name if self.product else None,
            "warehouse_id": self.warehouse_id,
            "warehouse": self.warehouse.name if self.warehouse else None,
            "movement_type": self.movement_type,
            "quantity": self.quantity,
            "notes": self.notes,
            "performed_by": self.performed_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

class Customer(db.Model):
    __tablename__ = "customers"

    customer_id = db.Column("customer_id", db.BigInteger, primary_key=True)
    code        = db.Column("code", db.String(20), unique=True, nullable=False)
    name        = db.Column("name", db.String(120), nullable=False)
    email       = db.Column("email", db.String(120))
    phone       = db.Column("phone", db.String(20))
    address     = db.Column("address", db.String(255))
    city        = db.Column("city", db.String(60))
    created_at  = db.Column(db.DateTime, default=now)
    deleted_at  = db.Column("deleted_at", db.DateTime)

    orders = db.relationship("Order", back_populates="customer", lazy="dynamic")

    @classmethod
    def active(cls):
        return cls.query.filter(cls.deleted_at.is_(None))

    def to_dict(self):
        return {"id": self.customer_id, "code": self.code, "name": self.name,
                "email": self.email, "phone": self.phone, "city": self.city}

class Order(db.Model):
    __tablename__ = "orders"

    STATUSES = ("PENDING", "APPROVED", "PROCESSING", "SHIPPED", "DELIVERED", "CANCELLED", "RETURNED")
    CANCELLABLE_BEFORE = {"PENDING", "APPROVED", "PROCESSING"}

    order_id     = db.Column("order_id", db.BigInteger, primary_key=True)
    order_number = db.Column("order_number", db.String(30), unique=True)
    customer_id  = db.Column("customer_id", db.BigInteger, db.ForeignKey("customers.customer_id"), nullable=False)
    status       = db.Column("status", db.Enum(*STATUSES), default="PENDING", nullable=False)
    total_amount = db.Column("total_amount", db.Numeric(14, 2), default=0)
    grand_total  = db.Column("grand_total", db.Numeric(14, 2), default=0)
    notes        = db.Column("notes", db.Text)
    placed_by    = db.Column("placed_by", db.BigInteger, db.ForeignKey("users.user_id"))
    approved_by  = db.Column("approved_by", db.BigInteger, db.ForeignKey("users.user_id"))
    placed_at    = db.Column("placed_at", db.DateTime, default=now)
    approved_at  = db.Column("approved_at", db.DateTime)
    cancelled_at = db.Column("cancelled_at", db.DateTime)
    cancel_reason= db.Column("cancel_reason", db.String(255))
    deleted_at   = db.Column("deleted_at", db.DateTime)

    customer  = db.relationship("Customer", back_populates="orders")
    approver  = db.relationship("User", foreign_keys=[approved_by])
    creator   = db.relationship("User", foreign_keys=[placed_by])
    items     = db.relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    shipments = db.relationship("Shipment", back_populates="order", lazy="dynamic")

    @classmethod
    def active(cls):
        return cls.query.filter(cls.deleted_at.is_(None))

    def soft_delete(self):
        self.deleted_at = now()

    def can_cancel(self):
        return self.status in self.CANCELLABLE_BEFORE

    def total(self):
        return float(self.grand_total or self.total_amount or 0)

    def to_dict(self, include_items=False):
        d = {
            "id": self.order_id,
            "order_number": self.order_number,
            "customer_id": self.customer_id,
            "customer": self.customer.name if self.customer else None,
            "status": self.status,
            "notes": self.notes,
            "approved_by": self.approved_by,
            "total_amount": self.total(),
            "created_at": self.placed_at.isoformat() if self.placed_at else None,
        }
        if include_items:
            d["items"] = [i.to_dict() for i in self.items]
        return d

class OrderItem(db.Model):
    __tablename__ = "order_items"

    item_id      = db.Column("item_id", db.BigInteger, primary_key=True)
    order_id     = db.Column("order_id", db.BigInteger, db.ForeignKey("orders.order_id", ondelete="CASCADE"), nullable=False)
    product_id   = db.Column("product_id", db.BigInteger, db.ForeignKey("products.product_id"), nullable=False)
    warehouse_id = db.Column("warehouse_id", db.Integer, db.ForeignKey("warehouses.warehouse_id"))
    quantity     = db.Column("quantity", db.Integer, nullable=False)
    unit_price   = db.Column("unit_price", db.Numeric(12, 2), nullable=False)
    line_total   = db.Column("line_total", db.Numeric(14, 2), db.Computed("quantity * unit_price"), nullable=True)

    order     = db.relationship("Order", back_populates="items")
    product   = db.relationship("Product", back_populates="order_items")
    warehouse = db.relationship("Warehouse")

    def calculate_line_total(self):
        self.line_total = self.quantity * float(self.unit_price)
        return self.line_total

    def to_dict(self):
        return {
            "id": self.item_id,
            "product_id": self.product_id,
            "product_name": self.product.name if self.product else None,
            "sku": self.product.sku if self.product else None,
            "warehouse_id": self.warehouse_id,
            "warehouse_name": self.warehouse.name if self.warehouse else None,
            "quantity": self.quantity,
            "unit_price": float(self.unit_price),
            "line_total": float(self.line_total or 0),
        }

class Shipment(db.Model):
    __tablename__ = "shipments"

    STATUSES = ("PREPARING", "PICKED", "IN_TRANSIT", "OUT_FOR_DELIVERY", "DELIVERED", "FAILED", "RETURNED")

    shipment_id       = db.Column("shipment_id", db.BigInteger, primary_key=True)
    tracking_number   = db.Column("tracking_number", db.String(40), unique=True)
    order_id          = db.Column("order_id", db.BigInteger, db.ForeignKey("orders.order_id"), nullable=False)
    warehouse_id      = db.Column("warehouse_id", db.Integer, db.ForeignKey("warehouses.warehouse_id"))
    assigned_employee = db.Column("assigned_employee", db.BigInteger, db.ForeignKey("users.user_id"))
    carrier           = db.Column("carrier", db.String(60))
    status            = db.Column("status", db.Enum(*STATUSES), default="PREPARING", nullable=False)
    expected_delivery = db.Column("expected_delivery", db.Date)
    shipped_at        = db.Column("shipped_at", db.DateTime)
    delivered_at      = db.Column("delivered_at", db.DateTime)
    notes             = db.Column("notes", db.Text)
    created_at        = db.Column(db.DateTime, default=now)
    updated_at        = db.Column(db.DateTime, default=now, onupdate=now)

    order    = db.relationship("Order", back_populates="shipments")
    employee = db.relationship("User", foreign_keys=[assigned_employee])
    warehouse= db.relationship("Warehouse", foreign_keys=[warehouse_id])

    def to_dict(self):
        return {
            "id": self.shipment_id,
            "order_id": self.order_id,
            "order_number": self.order.order_number if self.order else None,
            "tracking_number": self.tracking_number,
            "status": self.status,
            "assigned_to": self.assigned_employee,
            "employee_name": self.employee.full_name if self.employee else None,
            "shipped_at": self.shipped_at.isoformat() if self.shipped_at else None,
            "delivered_at": self.delivered_at.isoformat() if self.delivered_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

class SupplierOrder(db.Model):
    __tablename__ = "supplier_orders"

    STATUSES = ("DRAFT", "SENT", "ACKNOWLEDGED", "RECEIVED", "CANCELLED")

    po_id             = db.Column("po_id", db.BigInteger, primary_key=True)
    po_number         = db.Column("po_number", db.String(30), unique=True)
    supplier_id       = db.Column("supplier_id", db.Integer, db.ForeignKey("suppliers.supplier_id"), nullable=False)
    warehouse_id      = db.Column("warehouse_id", db.Integer, db.ForeignKey("warehouses.warehouse_id"))
    status            = db.Column("status", db.Enum(*STATUSES), default="DRAFT", nullable=False)
    total_amount      = db.Column("total_amount", db.Numeric(14, 2), default=0)
    expected_delivery = db.Column("expected_delivery", db.Date)
    actual_delivery   = db.Column("actual_delivery", db.Date)
    placed_by         = db.Column("placed_by", db.BigInteger, db.ForeignKey("users.user_id"))
    placed_at         = db.Column("placed_at", db.DateTime, default=now)
    received_at       = db.Column("received_at", db.DateTime)
    notes             = db.Column("notes", db.Text)

    supplier = db.relationship("Supplier", back_populates="purchase_orders")
    items    = db.relationship("SupplierOrderItem", back_populates="po", cascade="all, delete-orphan")

    def to_dict(self, include_items=False):
        d = {
            "id": self.po_id, "po_number": self.po_number,
            "supplier_id": self.supplier_id,
            "supplier": self.supplier.name if self.supplier else None,
            "status": self.status,
            "expected_date": self.expected_delivery.isoformat() if self.expected_delivery else None,
            "received_date": self.actual_delivery.isoformat() if self.actual_delivery else None,
            "created_at": self.placed_at.isoformat() if self.placed_at else None,
        }
        if include_items:
            d["items"] = [i.to_dict() for i in self.items]
        return d

class SupplierOrderItem(db.Model):
    __tablename__ = "supplier_order_items"

    poi_id       = db.Column("poi_id", db.BigInteger, primary_key=True)
    po_id        = db.Column("po_id", db.BigInteger, db.ForeignKey("supplier_orders.po_id", ondelete="CASCADE"), nullable=False)
    product_id   = db.Column("product_id", db.BigInteger, db.ForeignKey("products.product_id"), nullable=False)
    quantity     = db.Column("quantity", db.Integer, nullable=False)
    unit_cost    = db.Column("unit_cost", db.Numeric(12, 2))
    received_qty = db.Column("received_qty", db.Integer, default=0)
    line_total    = db.Column("line_total", db.Numeric(14, 2), db.Computed("quantity * unit_cost"), nullable=True)

    po      = db.relationship("SupplierOrder", back_populates="items")
    product = db.relationship("Product")

    def to_dict(self):
        return {
            "id": self.poi_id, "po_id": self.po_id,
            "product_id": self.product_id,
            "product_name": self.product.name if self.product else None,
            "ordered_qty": self.quantity,
            "received_qty": self.received_qty,
            "unit_cost": float(self.unit_cost or 0),
        }

class Notification(db.Model):
    __tablename__ = "notifications"

    TYPES      = ("LOW_STOCK", "ORDER", "SHIPMENT", "SUPPLIER", "SYSTEM", "APPROVAL")
    SEVERITIES = ("INFO", "WARNING", "CRITICAL")

    notification_id = db.Column("notification_id", db.BigInteger, primary_key=True)
    user_id         = db.Column("user_id", db.BigInteger, db.ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    title           = db.Column("title", db.String(150), nullable=False)
    message         = db.Column("message", db.String(500))
    type            = db.Column("type", db.Enum(*TYPES), nullable=False)
    severity        = db.Column("severity", db.Enum(*SEVERITIES), default="INFO")
    is_read         = db.Column("is_read", db.Boolean, default=False)
    link            = db.Column("link", db.String(255))
    meta            = db.Column("metadata", db.JSON)
    created_at      = db.Column(db.DateTime, default=now)
    read_at         = db.Column("read_at", db.DateTime)

    user = db.relationship("User", back_populates="notifications")

    def to_dict(self):
        return {
            "id": self.notification_id, "user_id": self.user_id,
            "type": self.type, "severity": self.severity,
            "title": self.title, "message": self.message,
            "link": self.link, "is_read": self.is_read,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

class AuditLog(db.Model):
    __tablename__ = "audit_logs"

    log_id      = db.Column("log_id", db.BigInteger, primary_key=True)
    user_id     = db.Column("user_id", db.BigInteger, db.ForeignKey("users.user_id", ondelete="SET NULL"))
    action      = db.Column("action", db.String(80), nullable=False)
    entity_type = db.Column("entity_type", db.String(50), nullable=False)
    entity_id   = db.Column("entity_id", db.BigInteger)
    old_value   = db.Column("old_value", db.JSON)
    new_value   = db.Column("new_value", db.JSON)
    ip_address  = db.Column("ip_address", db.String(45))
    user_agent  = db.Column("user_agent", db.String(255))
    created_at  = db.Column(db.DateTime, default=now)

    user = db.relationship("User")

    def to_dict(self):
        return {
            "id": self.log_id, "user_id": self.user_id,
            "action": self.action, "entity_type": self.entity_type,
            "entity_id": self.entity_id, "old_value": self.old_value,
            "new_value": self.new_value, "ip_address": self.ip_address,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

class ActivityTimeline(db.Model):
    __tablename__ = "activity_timeline"

    activity_id = db.Column("activity_id", db.BigInteger, primary_key=True)
    entity_type = db.Column("entity_type", db.String(50), nullable=False)
    entity_id   = db.Column("entity_id", db.BigInteger)
    user_id     = db.Column("user_id", db.BigInteger, db.ForeignKey("users.user_id", ondelete="SET NULL"))
    icon        = db.Column("icon", db.String(40))
    title       = db.Column("title", db.String(150), nullable=False)
    description = db.Column("description", db.String(500))
    created_at  = db.Column(db.DateTime, default=now)

    user = db.relationship("User")

    def to_dict(self):
        return {
            "id": self.activity_id, "user_id": self.user_id,
            "entity_type": self.entity_type, "entity_id": self.entity_id,
            "action": self.title, "description": self.description,
            "user_name": self.user.full_name if self.user else "System",
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

class DemandHistory(db.Model):
    __tablename__ = "demand_history"

    history_id   = db.Column("history_id", db.BigInteger, primary_key=True)
    product_id   = db.Column("product_id", db.BigInteger, db.ForeignKey("products.product_id"), nullable=False)
    warehouse_id = db.Column("warehouse_id", db.Integer, db.ForeignKey("warehouses.warehouse_id"))
    period_start = db.Column("period_start", db.Date, nullable=False)
    period_end   = db.Column("period_end", db.Date, nullable=False)
    units_sold   = db.Column("units_sold", db.Integer, default=0)
    avg_daily    = db.Column("avg_daily", db.Numeric(10, 3), default=0)

    product   = db.relationship("Product")
    warehouse = db.relationship("Warehouse")
