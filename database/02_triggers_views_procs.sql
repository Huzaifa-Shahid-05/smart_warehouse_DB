USE smart_warehouse;

DELIMITER $$

CREATE TRIGGER trg_inventory_low_stock_alert
AFTER UPDATE ON inventory
FOR EACH ROW
BEGIN
    DECLARE v_reorder_level   INT;
    DECLARE v_product_name    VARCHAR(150);
    DECLARE v_warehouse_name  VARCHAR(100);

    SELECT reorder_level, name INTO v_reorder_level, v_product_name
      FROM products WHERE product_id = NEW.product_id;

    SELECT name INTO v_warehouse_name
      FROM warehouses WHERE warehouse_id = NEW.warehouse_id;

    IF NEW.quantity <= v_reorder_level
       AND OLD.quantity > v_reorder_level THEN

        INSERT INTO notifications (user_id, title, message, type, severity, link, metadata)
        SELECT u.user_id,
               CONCAT('Low Stock: ', v_product_name),
               CONCAT('Stock for "', v_product_name, '" at ', v_warehouse_name,
                      ' has dropped to ', NEW.quantity, ' units (reorder level: ', v_reorder_level, ').'),
               'LOW_STOCK',
               CASE WHEN NEW.quantity = 0 THEN 'CRITICAL' ELSE 'WARNING' END,
               CONCAT('/inventory/', NEW.product_id),
               JSON_OBJECT(
                   'product_id',   NEW.product_id,
                   'warehouse_id', NEW.warehouse_id,
                   'quantity',     NEW.quantity,
                   'reorder_level', v_reorder_level
               )
          FROM users u
          JOIN roles r ON u.role_id = r.role_id
         WHERE r.role_name IN ('Administrator','Manager')
           AND u.deleted_at IS NULL
           AND u.is_active = TRUE;
    END IF;
END$$

CREATE TRIGGER trg_supplier_perf_after_po_update
AFTER UPDATE ON supplier_orders
FOR EACH ROW
BEGIN
    IF NEW.status = 'RECEIVED' AND OLD.status <> 'RECEIVED' THEN
        UPDATE suppliers
           SET total_orders   = total_orders + 1,
               on_time_orders = on_time_orders +
                   CASE
                       WHEN NEW.actual_delivery IS NOT NULL
                            AND NEW.actual_delivery <= NEW.expected_delivery
                       THEN 1 ELSE 0
                   END,
               rating = LEAST(5.00, GREATEST(0.00,
                   ((on_time_orders +
                     CASE
                       WHEN NEW.actual_delivery IS NOT NULL
                            AND NEW.actual_delivery <= NEW.expected_delivery
                       THEN 1 ELSE 0
                     END
                   ) / GREATEST(1, total_orders + 1)) * 5.00
               ))
         WHERE supplier_id = NEW.supplier_id;
    END IF;
END$$

CREATE TRIGGER trg_users_audit_update
AFTER UPDATE ON users
FOR EACH ROW
BEGIN
    IF OLD.role_id <> NEW.role_id
       OR OLD.is_active <> NEW.is_active
       OR (OLD.deleted_at IS NULL AND NEW.deleted_at IS NOT NULL) THEN

        INSERT INTO audit_logs (user_id, action, entity_type, entity_id, old_value, new_value)
        VALUES (
            NEW.user_id,
            'USER_UPDATED',
            'USER',
            NEW.user_id,
            JSON_OBJECT('role_id', OLD.role_id, 'is_active', OLD.is_active, 'deleted_at', OLD.deleted_at),
            JSON_OBJECT('role_id', NEW.role_id, 'is_active', NEW.is_active, 'deleted_at', NEW.deleted_at)
        );
    END IF;
END$$

CREATE TRIGGER trg_order_status_timeline
AFTER UPDATE ON orders
FOR EACH ROW
BEGIN
    IF NEW.status <> OLD.status THEN
        INSERT INTO activity_timeline (entity_type, entity_id, user_id, icon, title, description)
        VALUES (
            'ORDER',
            NEW.order_id,
            COALESCE(NEW.approved_by, NEW.placed_by),
            CASE NEW.status
                WHEN 'APPROVED'   THEN 'check-circle'
                WHEN 'PROCESSING' THEN 'package'
                WHEN 'SHIPPED'    THEN 'truck'
                WHEN 'DELIVERED'  THEN 'home'
                WHEN 'CANCELLED'  THEN 'x-circle'
                ELSE 'circle'
            END,
            CONCAT('Order ', NEW.order_number, ' → ', NEW.status),
            CONCAT('Status changed from ', OLD.status, ' to ', NEW.status)
        );

        INSERT INTO notifications (user_id, title, message, type, severity, link)
        VALUES (
            NEW.placed_by,
            CONCAT('Order ', NEW.order_number, ' updated'),
            CONCAT('Your order is now ', NEW.status, '.'),
            'ORDER',
            'INFO',
            CONCAT('/orders/', NEW.order_id)
        );
    END IF;
END$$

CREATE TRIGGER trg_orders_before_insert
BEFORE INSERT ON orders
FOR EACH ROW
BEGIN
    IF NEW.order_number IS NULL OR NEW.order_number = '' THEN
        SET NEW.order_number = CONCAT(
            'ORD-',
            DATE_FORMAT(NOW(),'%Y'),
            '-',
            LPAD((SELECT IFNULL(MAX(order_id),0) + 1 FROM orders), 5, '0')
        );
    END IF;
END$$

CREATE TRIGGER trg_shipments_before_insert
BEFORE INSERT ON shipments
FOR EACH ROW
BEGIN
    IF NEW.tracking_number IS NULL OR NEW.tracking_number = '' THEN
        SET NEW.tracking_number = CONCAT(
            'TRK-',
            DATE_FORMAT(NOW(),'%Y'),
            '-',
            LPAD((SELECT IFNULL(MAX(shipment_id),0) + 1 FROM shipments), 5, '0')
        );
    END IF;
END$$

CREATE TRIGGER trg_inventory_movement_log
AFTER UPDATE ON inventory
FOR EACH ROW
BEGIN
    IF OLD.quantity <> NEW.quantity AND @disable_movement_trigger IS NULL THEN
        INSERT INTO stock_movements
            (product_id, warehouse_id, movement_type, quantity, reference_type, notes, performed_by)
        VALUES (
            NEW.product_id,
            NEW.warehouse_id,
            CASE WHEN NEW.quantity > OLD.quantity THEN 'IN' ELSE 'OUT' END,
            ABS(NEW.quantity - OLD.quantity),
            'MANUAL_ADJUSTMENT',
            CONCAT('Auto-logged: ', OLD.quantity, ' → ', NEW.quantity),
            COALESCE(@current_user_id, 1)
        );
    END IF;
END$$

DELIMITER ;

CREATE OR REPLACE VIEW v_low_stock AS
SELECT  p.product_id,
        p.sku,
        p.name             AS product_name,
        c.name             AS category,
        w.warehouse_id,
        w.name             AS warehouse_name,
        i.quantity,
        p.reorder_level,
        p.reorder_quantity,
        (p.reorder_level - i.quantity) AS shortage
  FROM  inventory i
  JOIN  products   p ON i.product_id = p.product_id
  JOIN  warehouses w ON i.warehouse_id = w.warehouse_id
  JOIN  categories c ON p.category_id = c.category_id
 WHERE  i.quantity <= p.reorder_level
   AND  p.deleted_at IS NULL;

CREATE OR REPLACE VIEW v_supplier_performance AS
SELECT  s.supplier_id,
        s.code,
        s.name,
        s.rating,
        s.total_orders,
        s.on_time_orders,
        ROUND(IF(s.total_orders = 0, 0, s.on_time_orders / s.total_orders) * 100, 2)
            AS on_time_percentage,
        (SELECT AVG(DATEDIFF(po.actual_delivery, po.placed_at))
           FROM supplier_orders po
          WHERE po.supplier_id = s.supplier_id AND po.status = 'RECEIVED')
            AS avg_delivery_days
  FROM  suppliers s
 WHERE  s.deleted_at IS NULL;

CREATE OR REPLACE VIEW v_dashboard_kpis AS
SELECT
    (SELECT COUNT(*) FROM orders     WHERE deleted_at IS NULL)                               AS total_orders,
    (SELECT COUNT(*) FROM orders     WHERE status = 'PENDING'   AND deleted_at IS NULL)      AS pending_orders,
    (SELECT COUNT(*) FROM shipments  WHERE status IN ('IN_TRANSIT','OUT_FOR_DELIVERY'))      AS active_shipments,
    (SELECT COUNT(*) FROM v_low_stock)                                                        AS low_stock_items,
    (SELECT COUNT(*) FROM products   WHERE deleted_at IS NULL)                               AS total_products,
    (SELECT COUNT(*) FROM suppliers  WHERE deleted_at IS NULL)                               AS total_suppliers,
    (SELECT COUNT(*) FROM warehouses WHERE deleted_at IS NULL)                               AS total_warehouses,
    (SELECT IFNULL(SUM(grand_total),0) FROM orders
       WHERE status NOT IN ('CANCELLED','RETURNED') AND deleted_at IS NULL
         AND placed_at >= DATE_SUB(NOW(), INTERVAL 30 DAY))                                   AS revenue_30d;

CREATE OR REPLACE VIEW v_monthly_order_trend AS
SELECT  DATE_FORMAT(placed_at, '%Y-%m') AS month,
        COUNT(*)                         AS order_count,
        SUM(grand_total)                 AS revenue,
        SUM(CASE WHEN status = 'CANCELLED' THEN 1 ELSE 0 END) AS cancelled_count
  FROM  orders
 WHERE  placed_at >= DATE_SUB(NOW(), INTERVAL 12 MONTH)
   AND  deleted_at IS NULL
 GROUP  BY DATE_FORMAT(placed_at, '%Y-%m')
 ORDER  BY month;

CREATE OR REPLACE VIEW v_warehouse_stock_value AS
SELECT  w.warehouse_id,
        w.code,
        w.name,
        COUNT(DISTINCT i.product_id)        AS unique_products,
        SUM(i.quantity)                     AS total_units,
        SUM(i.quantity * p.cost_price)      AS total_cost_value,
        SUM(i.quantity * p.unit_price)      AS total_retail_value
  FROM  warehouses w
  LEFT  JOIN inventory i ON w.warehouse_id = i.warehouse_id
  LEFT  JOIN products  p ON i.product_id = p.product_id AND p.deleted_at IS NULL
 WHERE  w.deleted_at IS NULL
 GROUP  BY w.warehouse_id, w.code, w.name;

DELIMITER $$

CREATE PROCEDURE sp_reserve_stock(
    IN  p_product_id    BIGINT UNSIGNED,
    IN  p_warehouse_id  INT UNSIGNED,
    IN  p_quantity      INT,
    IN  p_user_id       BIGINT UNSIGNED,
    IN  p_order_id      BIGINT UNSIGNED,
    OUT p_success       BOOLEAN,
    OUT p_message       VARCHAR(255)
)
BEGIN
    DECLARE v_available INT DEFAULT 0;

    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        SET p_success = FALSE;
        SET p_message = 'Database error during stock reservation';
    END;

    START TRANSACTION;

    SELECT (quantity - reserved_qty) INTO v_available
      FROM inventory
     WHERE product_id = p_product_id AND warehouse_id = p_warehouse_id
     FOR UPDATE;

    IF v_available IS NULL THEN
        SET p_success = FALSE;
        SET p_message = 'No inventory record exists for this product/warehouse';
        ROLLBACK;
    ELSEIF v_available < p_quantity THEN
        SET p_success = FALSE;
        SET p_message = CONCAT('Insufficient stock. Available: ', v_available);
        ROLLBACK;
    ELSE
        UPDATE inventory
           SET reserved_qty = reserved_qty + p_quantity
         WHERE product_id = p_product_id AND warehouse_id = p_warehouse_id;

        INSERT INTO stock_movements
            (product_id, warehouse_id, movement_type, quantity, reference_type, reference_id, performed_by, notes)
        VALUES
            (p_product_id, p_warehouse_id, 'RESERVE', p_quantity, 'ORDER', p_order_id, p_user_id, 'Reserved for order');

        SET p_success = TRUE;
        SET p_message = 'Stock reserved successfully';
        COMMIT;
    END IF;
END$$

CREATE PROCEDURE sp_find_fulfillment(
    IN  p_product_id  BIGINT UNSIGNED,
    IN  p_quantity    INT
)
BEGIN

    SELECT  i.warehouse_id,
            w.name AS warehouse_name,
            (i.quantity - i.reserved_qty) AS available,
            LEAST(i.quantity - i.reserved_qty, p_quantity) AS take_qty
      FROM  inventory i
      JOIN  warehouses w ON i.warehouse_id = w.warehouse_id
     WHERE  i.product_id = p_product_id
       AND  (i.quantity - i.reserved_qty) > 0
       AND  w.is_active = TRUE
       AND  w.deleted_at IS NULL
     ORDER  BY (i.quantity - i.reserved_qty) DESC;
END$$

CREATE PROCEDURE sp_predict_stockout(
    IN  p_product_id BIGINT UNSIGNED
)
BEGIN
    SELECT  p.product_id,
            p.name,
            w.warehouse_id,
            w.name AS warehouse_name,
            i.quantity AS current_stock,
            COALESCE(AVG(dh.avg_daily), 0) AS avg_daily_demand,
            CASE
              WHEN COALESCE(AVG(dh.avg_daily), 0) = 0 THEN NULL
              ELSE FLOOR(i.quantity / AVG(dh.avg_daily))
            END AS days_until_stockout,
            CASE
              WHEN COALESCE(AVG(dh.avg_daily), 0) = 0 THEN 'NO_DATA'
              WHEN FLOOR(i.quantity / AVG(dh.avg_daily)) <= 7  THEN 'CRITICAL'
              WHEN FLOOR(i.quantity / AVG(dh.avg_daily)) <= 14 THEN 'WARNING'
              ELSE 'OK'
            END AS status
      FROM  products p
      JOIN  inventory i  ON p.product_id = i.product_id
      JOIN  warehouses w ON i.warehouse_id = w.warehouse_id
      LEFT  JOIN demand_history dh
                  ON  dh.product_id   = p.product_id
                 AND  dh.warehouse_id = w.warehouse_id
                 AND  dh.period_end >= DATE_SUB(CURDATE(), INTERVAL 90 DAY)
     WHERE  p.product_id = p_product_id
       AND  p.deleted_at IS NULL
     GROUP  BY p.product_id, p.name, w.warehouse_id, w.name, i.quantity;
END$$

DELIMITER ;
