DROP DATABASE IF EXISTS smart_warehouse;
CREATE DATABASE smart_warehouse
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE smart_warehouse;

SET FOREIGN_KEY_CHECKS = 0;

CREATE TABLE roles (
    role_id        INT UNSIGNED  AUTO_INCREMENT PRIMARY KEY,
    role_name      VARCHAR(50)   NOT NULL UNIQUE,
    description    VARCHAR(255),
    permissions    JSON          NOT NULL,
    created_at     TIMESTAMP     DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_role_name (role_name)
) ENGINE=InnoDB;

CREATE TABLE users (
    user_id          BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    username         VARCHAR(50)     NOT NULL UNIQUE,
    email            VARCHAR(120)    NOT NULL UNIQUE,
    password_hash    VARCHAR(255)    NOT NULL,
    full_name        VARCHAR(100)    NOT NULL,
    phone            VARCHAR(20),
    role_id          INT UNSIGNED    NOT NULL,
    is_active        BOOLEAN         NOT NULL DEFAULT TRUE,
    last_login       DATETIME        NULL,
    failed_attempts  TINYINT         NOT NULL DEFAULT 0,
    locked_until     DATETIME        NULL,
    created_at       TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    updated_at       TIMESTAMP       DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted_at       DATETIME        NULL,
    CONSTRAINT fk_user_role
        FOREIGN KEY (role_id) REFERENCES roles(role_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    INDEX idx_user_email      (email),
    INDEX idx_user_username   (username),
    INDEX idx_user_role       (role_id),
    INDEX idx_user_deleted    (deleted_at)
) ENGINE=InnoDB;

CREATE TABLE warehouses (
    warehouse_id    INT UNSIGNED   AUTO_INCREMENT PRIMARY KEY,
    code            VARCHAR(20)    NOT NULL UNIQUE,
    name            VARCHAR(100)   NOT NULL,
    address         VARCHAR(255)   NOT NULL,
    city            VARCHAR(60)    NOT NULL,
    country         VARCHAR(60)    NOT NULL DEFAULT 'Pakistan',
    capacity_units  INT UNSIGNED   NOT NULL DEFAULT 10000,
    manager_id      BIGINT UNSIGNED NULL,
    is_active       BOOLEAN        NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMP      DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP      DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted_at      DATETIME       NULL,
    CONSTRAINT fk_wh_manager
        FOREIGN KEY (manager_id) REFERENCES users(user_id)
        ON UPDATE CASCADE ON DELETE SET NULL,
    INDEX idx_wh_code     (code),
    INDEX idx_wh_city     (city),
    INDEX idx_wh_deleted  (deleted_at)
) ENGINE=InnoDB;

CREATE TABLE categories (
    category_id   INT UNSIGNED  AUTO_INCREMENT PRIMARY KEY,
    name          VARCHAR(80)   NOT NULL UNIQUE,
    description   VARCHAR(255),
    parent_id     INT UNSIGNED  NULL,
    created_at    TIMESTAMP     DEFAULT CURRENT_TIMESTAMP,
    deleted_at    DATETIME      NULL,
    CONSTRAINT fk_cat_parent
        FOREIGN KEY (parent_id) REFERENCES categories(category_id)
        ON UPDATE CASCADE ON DELETE SET NULL,
    INDEX idx_cat_parent  (parent_id),
    INDEX idx_cat_deleted (deleted_at)
) ENGINE=InnoDB;

CREATE TABLE suppliers (
    supplier_id      INT UNSIGNED  AUTO_INCREMENT PRIMARY KEY,
    code             VARCHAR(20)   NOT NULL UNIQUE,
    name             VARCHAR(120)  NOT NULL,
    contact_person   VARCHAR(100),
    email            VARCHAR(120)  NOT NULL,
    phone            VARCHAR(20),
    address          VARCHAR(255),
    city             VARCHAR(60),
    country          VARCHAR(60),
    rating           DECIMAL(3,2)  NOT NULL DEFAULT 0.00,
    total_orders     INT UNSIGNED  NOT NULL DEFAULT 0,
    on_time_orders   INT UNSIGNED  NOT NULL DEFAULT 0,
    is_active        BOOLEAN       NOT NULL DEFAULT TRUE,
    created_at       TIMESTAMP     DEFAULT CURRENT_TIMESTAMP,
    updated_at       TIMESTAMP     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted_at       DATETIME      NULL,
    INDEX idx_sup_code     (code),
    INDEX idx_sup_email    (email),
    INDEX idx_sup_rating   (rating DESC),
    INDEX idx_sup_deleted  (deleted_at)
) ENGINE=InnoDB;

CREATE TABLE products (
    product_id        BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    sku               VARCHAR(40)     NOT NULL UNIQUE,
    barcode           VARCHAR(50)     UNIQUE,
    name              VARCHAR(150)    NOT NULL,
    description       TEXT,
    category_id       INT UNSIGNED    NOT NULL,
    primary_supplier_id INT UNSIGNED  NULL,
    unit_price        DECIMAL(12,2)   NOT NULL,
    cost_price        DECIMAL(12,2)   NOT NULL,
    unit_of_measure   VARCHAR(20)     NOT NULL DEFAULT 'pcs',
    weight_kg         DECIMAL(8,3),
    reorder_level     INT UNSIGNED    NOT NULL DEFAULT 10,
    reorder_quantity  INT UNSIGNED    NOT NULL DEFAULT 50,
    is_active         BOOLEAN         NOT NULL DEFAULT TRUE,
    created_at        TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    updated_at        TIMESTAMP       DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted_at        DATETIME        NULL,
    CONSTRAINT fk_prod_category
        FOREIGN KEY (category_id) REFERENCES categories(category_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_prod_supplier
        FOREIGN KEY (primary_supplier_id) REFERENCES suppliers(supplier_id)
        ON UPDATE CASCADE ON DELETE SET NULL,
    CONSTRAINT chk_prices CHECK (unit_price >= 0 AND cost_price >= 0),
    INDEX idx_prod_sku       (sku),
    INDEX idx_prod_barcode   (barcode),
    INDEX idx_prod_category  (category_id),
    INDEX idx_prod_supplier  (primary_supplier_id),
    INDEX idx_prod_name      (name),
    INDEX idx_prod_deleted   (deleted_at),
    FULLTEXT INDEX ft_prod_search (name, description)
) ENGINE=InnoDB;

CREATE TABLE inventory (
    inventory_id   BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    product_id     BIGINT UNSIGNED NOT NULL,
    warehouse_id   INT UNSIGNED    NOT NULL,
    quantity       INT             NOT NULL DEFAULT 0,
    reserved_qty   INT             NOT NULL DEFAULT 0,
    last_restocked DATETIME        NULL,
    last_counted   DATETIME        NULL,
    updated_at     TIMESTAMP       DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_inv_product
        FOREIGN KEY (product_id) REFERENCES products(product_id)
        ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT fk_inv_warehouse
        FOREIGN KEY (warehouse_id) REFERENCES warehouses(warehouse_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT uq_product_warehouse UNIQUE (product_id, warehouse_id),
    CONSTRAINT chk_non_negative_qty   CHECK (quantity >= 0),
    CONSTRAINT chk_non_negative_resv  CHECK (reserved_qty >= 0),
    CONSTRAINT chk_reserved_lte_qty   CHECK (reserved_qty <= quantity),
    INDEX idx_inv_product   (product_id),
    INDEX idx_inv_warehouse (warehouse_id),
    INDEX idx_inv_low_stock (quantity)
) ENGINE=InnoDB;

CREATE TABLE stock_movements (
    movement_id    BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    product_id     BIGINT UNSIGNED NOT NULL,
    warehouse_id   INT UNSIGNED    NOT NULL,
    movement_type  ENUM('IN','OUT','TRANSFER','ADJUSTMENT','RESERVE','RELEASE') NOT NULL,
    quantity       INT             NOT NULL,
    reference_type VARCHAR(30),
    reference_id   BIGINT UNSIGNED,
    notes          VARCHAR(255),
    performed_by   BIGINT UNSIGNED NOT NULL,
    created_at     TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_mov_product
        FOREIGN KEY (product_id) REFERENCES products(product_id),
    CONSTRAINT fk_mov_warehouse
        FOREIGN KEY (warehouse_id) REFERENCES warehouses(warehouse_id),
    CONSTRAINT fk_mov_user
        FOREIGN KEY (performed_by) REFERENCES users(user_id),
    INDEX idx_mov_product     (product_id),
    INDEX idx_mov_warehouse   (warehouse_id),
    INDEX idx_mov_reference   (reference_type, reference_id),
    INDEX idx_mov_created     (created_at DESC)
) ENGINE=InnoDB;

CREATE TABLE customers (
    customer_id   BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    code          VARCHAR(20)     NOT NULL UNIQUE,
    name          VARCHAR(120)    NOT NULL,
    email         VARCHAR(120)    NOT NULL,
    phone         VARCHAR(20),
    address       VARCHAR(255)    NOT NULL,
    city          VARCHAR(60)     NOT NULL,
    country       VARCHAR(60)     NOT NULL DEFAULT 'Pakistan',
    created_at    TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    deleted_at    DATETIME        NULL,
    INDEX idx_cust_email   (email),
    INDEX idx_cust_deleted (deleted_at)
) ENGINE=InnoDB;

CREATE TABLE orders (
    order_id        BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    order_number    VARCHAR(30)     NOT NULL UNIQUE,
    customer_id     BIGINT UNSIGNED NOT NULL,
    status          ENUM('PENDING','APPROVED','PROCESSING','SHIPPED','DELIVERED','CANCELLED','RETURNED')
                    NOT NULL DEFAULT 'PENDING',
    total_amount    DECIMAL(14,2)   NOT NULL DEFAULT 0,
    discount        DECIMAL(12,2)   NOT NULL DEFAULT 0,
    tax_amount      DECIMAL(12,2)   NOT NULL DEFAULT 0,
    grand_total     DECIMAL(14,2)   NOT NULL DEFAULT 0,
    notes           TEXT,
    placed_by       BIGINT UNSIGNED NOT NULL,
    approved_by     BIGINT UNSIGNED NULL,
    placed_at       TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    approved_at     DATETIME        NULL,
    cancelled_at    DATETIME        NULL,
    cancel_reason   VARCHAR(255),
    deleted_at      DATETIME        NULL,
    CONSTRAINT fk_ord_customer
        FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_ord_placed_by
        FOREIGN KEY (placed_by) REFERENCES users(user_id),
    CONSTRAINT fk_ord_approved_by
        FOREIGN KEY (approved_by) REFERENCES users(user_id),
    CONSTRAINT chk_grand_total CHECK (grand_total >= 0),
    INDEX idx_ord_number    (order_number),
    INDEX idx_ord_customer  (customer_id),
    INDEX idx_ord_status    (status),
    INDEX idx_ord_placed    (placed_at DESC),
    INDEX idx_ord_deleted   (deleted_at)
) ENGINE=InnoDB;

CREATE TABLE order_items (
    item_id        BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    order_id       BIGINT UNSIGNED NOT NULL,
    product_id     BIGINT UNSIGNED NOT NULL,
    warehouse_id   INT UNSIGNED    NOT NULL,
    quantity       INT UNSIGNED    NOT NULL,
    unit_price     DECIMAL(12,2)   NOT NULL,
    line_total     DECIMAL(14,2)   AS (quantity * unit_price) STORED,
    CONSTRAINT fk_oi_order
        FOREIGN KEY (order_id) REFERENCES orders(order_id)
        ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT fk_oi_product
        FOREIGN KEY (product_id) REFERENCES products(product_id),
    CONSTRAINT fk_oi_warehouse
        FOREIGN KEY (warehouse_id) REFERENCES warehouses(warehouse_id),
    CONSTRAINT chk_oi_qty CHECK (quantity > 0),
    INDEX idx_oi_order     (order_id),
    INDEX idx_oi_product   (product_id),
    INDEX idx_oi_warehouse (warehouse_id)
) ENGINE=InnoDB;

CREATE TABLE shipments (
    shipment_id        BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    tracking_number    VARCHAR(40)     NOT NULL UNIQUE,
    order_id           BIGINT UNSIGNED NOT NULL,
    warehouse_id       INT UNSIGNED    NOT NULL,
    assigned_employee  BIGINT UNSIGNED NOT NULL,
    carrier            VARCHAR(60),
    status             ENUM('PREPARING','PICKED','IN_TRANSIT','OUT_FOR_DELIVERY','DELIVERED','FAILED','RETURNED')
                       NOT NULL DEFAULT 'PREPARING',
    expected_delivery  DATE            NULL,
    actual_delivery    DATETIME        NULL,
    shipped_at         DATETIME        NULL,
    delivered_at       DATETIME        NULL,
    notes              TEXT,
    created_at         TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    updated_at         TIMESTAMP       DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_ship_order
        FOREIGN KEY (order_id) REFERENCES orders(order_id)
        ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT fk_ship_warehouse
        FOREIGN KEY (warehouse_id) REFERENCES warehouses(warehouse_id),
    CONSTRAINT fk_ship_employee
        FOREIGN KEY (assigned_employee) REFERENCES users(user_id),
    INDEX idx_ship_track     (tracking_number),
    INDEX idx_ship_order     (order_id),
    INDEX idx_ship_status    (status),
    INDEX idx_ship_employee  (assigned_employee)
) ENGINE=InnoDB;

CREATE TABLE supplier_orders (
    po_id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    po_number          VARCHAR(30)     NOT NULL UNIQUE,
    supplier_id        INT UNSIGNED    NOT NULL,
    warehouse_id       INT UNSIGNED    NOT NULL,
    status             ENUM('DRAFT','SENT','ACKNOWLEDGED','RECEIVED','CANCELLED') NOT NULL DEFAULT 'DRAFT',
    total_amount       DECIMAL(14,2)   NOT NULL DEFAULT 0,
    expected_delivery  DATE            NOT NULL,
    actual_delivery    DATE            NULL,
    placed_by          BIGINT UNSIGNED NOT NULL,
    placed_at          TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    received_at        DATETIME        NULL,
    notes              TEXT,
    CONSTRAINT fk_po_supplier
        FOREIGN KEY (supplier_id) REFERENCES suppliers(supplier_id),
    CONSTRAINT fk_po_warehouse
        FOREIGN KEY (warehouse_id) REFERENCES warehouses(warehouse_id),
    CONSTRAINT fk_po_user
        FOREIGN KEY (placed_by) REFERENCES users(user_id),
    INDEX idx_po_supplier  (supplier_id),
    INDEX idx_po_status    (status),
    INDEX idx_po_dates     (expected_delivery, actual_delivery)
) ENGINE=InnoDB;

CREATE TABLE supplier_order_items (
    poi_id        BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    po_id         BIGINT UNSIGNED NOT NULL,
    product_id    BIGINT UNSIGNED NOT NULL,
    quantity      INT UNSIGNED    NOT NULL,
    unit_cost     DECIMAL(12,2)   NOT NULL,
    received_qty  INT UNSIGNED    NOT NULL DEFAULT 0,
    line_total    DECIMAL(14,2)   AS (quantity * unit_cost) STORED,
    CONSTRAINT fk_poi_po
        FOREIGN KEY (po_id) REFERENCES supplier_orders(po_id) ON DELETE CASCADE,
    CONSTRAINT fk_poi_product
        FOREIGN KEY (product_id) REFERENCES products(product_id),
    CONSTRAINT chk_poi_qty CHECK (quantity > 0)
) ENGINE=InnoDB;

CREATE TABLE notifications (
    notification_id  BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id          BIGINT UNSIGNED NOT NULL,
    title            VARCHAR(150)    NOT NULL,
    message          VARCHAR(500)    NOT NULL,
    type             ENUM('LOW_STOCK','ORDER','SHIPMENT','SUPPLIER','SYSTEM','APPROVAL') NOT NULL,
    severity         ENUM('INFO','WARNING','CRITICAL') NOT NULL DEFAULT 'INFO',
    is_read          BOOLEAN         NOT NULL DEFAULT FALSE,
    link             VARCHAR(255),
    metadata         JSON,
    created_at       TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    read_at          DATETIME        NULL,
    CONSTRAINT fk_notif_user
        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    INDEX idx_notif_user_unread (user_id, is_read),
    INDEX idx_notif_created     (created_at DESC)
) ENGINE=InnoDB;

CREATE TABLE audit_logs (
    log_id        BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id       BIGINT UNSIGNED NULL,
    action        VARCHAR(80)     NOT NULL,
    entity_type   VARCHAR(50)     NOT NULL,
    entity_id     BIGINT UNSIGNED NULL,
    old_value     JSON            NULL,
    new_value     JSON            NULL,
    ip_address    VARCHAR(45),
    user_agent    VARCHAR(255),
    created_at    TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_audit_user
        FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE SET NULL,
    INDEX idx_audit_user    (user_id),
    INDEX idx_audit_entity  (entity_type, entity_id),
    INDEX idx_audit_action  (action),
    INDEX idx_audit_created (created_at DESC)
) ENGINE=InnoDB;

CREATE TABLE activity_timeline (
    activity_id   BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    entity_type   VARCHAR(50)     NOT NULL,
    entity_id     BIGINT UNSIGNED NOT NULL,
    user_id       BIGINT UNSIGNED NULL,
    icon          VARCHAR(40),
    title         VARCHAR(150)    NOT NULL,
    description   VARCHAR(500),
    created_at    TIMESTAMP       DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_timeline_entity  (entity_type, entity_id, created_at DESC)
) ENGINE=InnoDB;

CREATE TABLE demand_history (
    history_id    BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    product_id    BIGINT UNSIGNED NOT NULL,
    warehouse_id  INT UNSIGNED    NOT NULL,
    period_start  DATE            NOT NULL,
    period_end    DATE            NOT NULL,
    units_sold    INT UNSIGNED    NOT NULL DEFAULT 0,
    avg_daily     DECIMAL(10,3)   NOT NULL DEFAULT 0,
    CONSTRAINT fk_dh_product   FOREIGN KEY (product_id) REFERENCES products(product_id),
    CONSTRAINT fk_dh_warehouse FOREIGN KEY (warehouse_id) REFERENCES warehouses(warehouse_id),
    UNIQUE KEY uq_demand_period (product_id, warehouse_id, period_start, period_end)
) ENGINE=InnoDB;

CREATE TABLE token_blocklist (
    jti          VARCHAR(36)   PRIMARY KEY,
    user_id      BIGINT UNSIGNED NOT NULL,
    expires_at   DATETIME      NOT NULL,
    revoked_at   TIMESTAMP     DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_blocklist_expires (expires_at)
) ENGINE=InnoDB;

SET FOREIGN_KEY_CHECKS = 1;
