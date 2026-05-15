USE smart_warehouse;

SET FOREIGN_KEY_CHECKS = 0;

INSERT INTO roles (role_name, description, permissions) VALUES
('Administrator', 'Full system access',
 JSON_ARRAY('users:*','products:*','warehouses:*','suppliers:*','orders:*','shipments:*','reports:*','settings:*')),
('Manager', 'Approve large orders, manage suppliers, view analytics',
 JSON_ARRAY('products:read','products:update','suppliers:*','orders:read','orders:approve','shipments:read','reports:*')),
('Employee', 'Day-to-day inventory and order processing',
 JSON_ARRAY('products:read','inventory:*','orders:create','orders:read','orders:update','shipments:*'));

INSERT INTO users (username, email, password_hash, full_name, phone, role_id, is_active) VALUES
('admin',     'admin@smartwarehouse.pk',   '$2b$12$KIXEX0Cv6q3QpGz2CZqYYuPDgvkBcU.HpFQHVWmJwHJQL6wkFJ8zG', 'System Admin',     '+92-300-1111111', 1, TRUE),
('manager1',  'manager@smartwarehouse.pk', '$2b$12$KIXEX0Cv6q3QpGz2CZqYYuPDgvkBcU.HpFQHVWmJwHJQL6wkFJ8zG', 'Sara Khan',        '+92-300-2222222', 2, TRUE),
('huzaifa',   'huzaifa@smartwarehouse.pk', '$2b$12$KIXEX0Cv6q3QpGz2CZqYYuPDgvkBcU.HpFQHVWmJwHJQL6wkFJ8zG', 'Huzaifa Shahid',   '+92-300-3333333', 3, TRUE),
('ali',       'ali@smartwarehouse.pk',     '$2b$12$KIXEX0Cv6q3QpGz2CZqYYuPDgvkBcU.HpFQHVWmJwHJQL6wkFJ8zG', 'Ali Hussain',      '+92-300-4444444', 3, TRUE),
('ammar',     'ammar@smartwarehouse.pk',   '$2b$12$KIXEX0Cv6q3QpGz2CZqYYuPDgvkBcU.HpFQHVWmJwHJQL6wkFJ8zG', 'Muhammad Ammar',   '+92-300-5555555', 3, TRUE);

INSERT INTO warehouses (code, name, address, city, country, capacity_units, manager_id, is_active) VALUES
('WH-KHI-01', 'Karachi Central Warehouse', 'Plot 24, S.I.T.E. Industrial Area',  'Karachi',   'Pakistan', 50000, 2, TRUE),
('WH-LHE-01', 'Lahore Distribution Hub',   '12-A Multan Road, Industrial Estate', 'Lahore',   'Pakistan', 35000, 2, TRUE),
('WH-ISB-01', 'Islamabad North Depot',     'Sector I-9 Industrial Area',         'Islamabad', 'Pakistan', 25000, 2, TRUE);

INSERT INTO categories (name, description, parent_id) VALUES
('Electronics',         'Consumer electronics and gadgets', NULL),
('Mobile Phones',       'Smartphones and feature phones',  1),
('Laptops & Computers', 'Computing devices',                1),
('Accessories',         'Cables, chargers, cases',          1),
('Home & Kitchen',      'Household and kitchen items',     NULL),
('Office Supplies',     'Stationery and office equipment', NULL);

INSERT INTO suppliers (code, name, contact_person, email, phone, address, city, country, rating, total_orders, on_time_orders) VALUES
('SUP-0001', 'TechSource Pakistan',  'Imran Malik',  'sales@techsource.pk',   '+92-21-35550001', 'Plot 12, S.I.T.E.',     'Karachi',   'Pakistan', 4.50, 20, 18),
('SUP-0002', 'Global Electronics',   'Fatima Noor',  'orders@globalelec.com', '+92-42-37550002', '5-K Gulberg III',       'Lahore',    'Pakistan', 4.20, 15, 12),
('SUP-0003', 'Karachi Trading Co.',  'Ahmed Raza',   'info@karachitrading.pk','+92-21-32550003', 'Saddar Bazaar',         'Karachi',   'Pakistan', 3.80, 10, 7),
('SUP-0004', 'Premium Suppliers Ltd','Bilal Hassan', 'contact@premium.pk',    '+92-51-22550004', 'F-7 Markaz',            'Islamabad', 'Pakistan', 4.80, 25, 24);

INSERT INTO products (sku, barcode, name, description, category_id, primary_supplier_id, unit_price, cost_price, unit_of_measure, weight_kg, reorder_level, reorder_quantity) VALUES
('SKU-MOB-001', '8901234500011', 'Samsung Galaxy A55',     'Mid-range Android smartphone, 256 GB',           2, 1, 89999.00, 72000.00, 'pcs', 0.250, 15,  50),
('SKU-MOB-002', '8901234500028', 'iPhone 15 Pro',          'Apple flagship smartphone, 256 GB',              2, 4, 389999.00, 320000.00, 'pcs', 0.220, 10,  25),
('SKU-LAP-001', '8901234500035', 'Dell Inspiron 15',       'i5 laptop, 16 GB RAM, 512 GB SSD',               3, 1, 184999.00, 155000.00, 'pcs', 1.800, 8,   20),
('SKU-LAP-002', '8901234500042', 'HP Pavilion 14',         'Ryzen 5 laptop, 8 GB RAM, 512 GB SSD',           3, 2, 159999.00, 132000.00, 'pcs', 1.600, 8,   20),
('SKU-ACC-001', '8901234500059', 'USB-C Charging Cable',   '1.5 m braided cable, 60 W',                      4, 3, 1499.00,   850.00,   'pcs', 0.080, 50,  200),
('SKU-ACC-002', '8901234500066', 'Wireless Mouse',         'Bluetooth mouse, ergonomic',                     4, 3, 2499.00,   1400.00,  'pcs', 0.120, 30,  100),
('SKU-ACC-003', '8901234500073', 'Laptop Backpack',        'Water-resistant 15.6" backpack',                 4, 2, 3999.00,   2400.00,  'pcs', 0.700, 20,  60),
('SKU-HKT-001', '8901234500080', 'Electric Kettle 1.5L',   'Stainless steel, auto cut-off',                  5, 4, 4999.00,   3200.00,  'pcs', 1.100, 10,  40),
('SKU-OFF-001', '8901234500097', 'Premium Notebook Set',   'Pack of 3 hardcover notebooks',                  6, 3, 1299.00,   650.00,   'pcs', 0.500, 25,  100);

INSERT INTO inventory (product_id, warehouse_id, quantity, reserved_qty, last_restocked) VALUES

(1, 1, 35, 0, NOW()),
(1, 2, 22, 0, NOW()),
(1, 3, 12, 0, NOW()),

(2, 1, 8,  0, NOW()),
(2, 2, 5,  0, NOW()),

(3, 1, 18, 0, NOW()),
(3, 2, 10, 0, NOW()),

(4, 1, 6,  0, NOW()),
(4, 3, 14, 0, NOW()),

(5, 1, 250, 0, NOW()),
(5, 2, 180, 0, NOW()),
(5, 3, 90,  0, NOW()),

(6, 1, 75, 0, NOW()),
(6, 2, 40, 0, NOW()),

(7, 1, 45, 0, NOW()),
(7, 3, 18, 0, NOW()),

(8, 2, 28, 0, NOW()),
(8, 3, 5,  0, NOW()),

(9, 1, 80, 0, NOW()),
(9, 2, 45, 0, NOW()),
(9, 3, 22, 0, NOW());

INSERT INTO customers (code, name, email, phone, address, city, country) VALUES
('CUST-0001', 'Hassan Mehmood',     'hassan@example.com', '+92-300-9990001', 'House 12, DHA Phase 5',     'Karachi',   'Pakistan'),
('CUST-0002', 'Aisha Tariq',        'aisha@example.com',  '+92-300-9990002', 'Flat 3-B, Bahria Town',     'Lahore',    'Pakistan'),
('CUST-0003', 'TechCorp Solutions', 'po@techcorp.pk',     '+92-51-9990003',  'Office 401, Centaurus Mall','Islamabad', 'Pakistan'),
('CUST-0004', 'Zara Ahmed',         'zara@example.com',   '+92-300-9990004', '24/A Defence Road',         'Karachi',   'Pakistan');

INSERT INTO orders (order_number, customer_id, status, total_amount, discount, tax_amount, grand_total, placed_by, approved_by, placed_at, approved_at)
VALUES
('ORD-2026-00001', 1, 'DELIVERED',  91498.00, 0,    16469.64, 107967.64, 3, 2, '2026-04-10 10:00:00', '2026-04-10 11:00:00'),
('ORD-2026-00002', 2, 'SHIPPED',   162498.00, 5000, 28349.64, 185847.64, 3, 2, '2026-04-15 14:00:00', '2026-04-15 15:00:00'),
('ORD-2026-00003', 3, 'PROCESSING',389999.00, 10000,68398.20, 448397.20, 4, NULL, '2026-04-20 09:00:00', NULL),
('ORD-2026-00004', 4, 'PENDING',     8997.00, 0,    1619.46,  10616.46,  5, NULL, '2026-04-22 16:30:00', NULL);

INSERT INTO order_items (order_id, product_id, warehouse_id, quantity, unit_price) VALUES
(1, 1, 1, 1, 89999.00),
(1, 5, 1, 1, 1499.00),
(2, 3, 1, 1, 184999.00),
(3, 2, 1, 1, 389999.00),
(4, 5, 1, 2, 1499.00),
(4, 6, 1, 1, 2499.00),
(4, 9, 1, 2, 1299.00);

INSERT INTO shipments (tracking_number, order_id, warehouse_id, assigned_employee, carrier, status, expected_delivery, actual_delivery, shipped_at, delivered_at)
VALUES
('TRK-2026-00001', 1, 1, 4, 'TCS Pakistan',     'DELIVERED',   '2026-04-12', '2026-04-12 14:30:00', '2026-04-11 09:00:00', '2026-04-12 14:30:00'),
('TRK-2026-00002', 2, 1, 4, 'Leopards Courier', 'IN_TRANSIT',  '2026-04-23', NULL,                  '2026-04-21 10:00:00', NULL);

INSERT INTO supplier_orders (po_number, supplier_id, warehouse_id, status, total_amount, expected_delivery, actual_delivery, placed_by, placed_at, received_at)
VALUES
('PO-2026-00001', 1, 1, 'RECEIVED', 720000.00, '2026-03-15', '2026-03-14', 1, '2026-03-01 10:00:00', '2026-03-14 16:00:00'),
('PO-2026-00002', 4, 1, 'SENT',     800000.00, '2026-04-30', NULL,         1, '2026-04-15 09:00:00', NULL);

INSERT INTO supplier_order_items (po_id, product_id, quantity, unit_cost, received_qty) VALUES
(1, 1, 10, 72000.00, 10),
(2, 2, 5,  320000.00, 0);

INSERT INTO demand_history (product_id, warehouse_id, period_start, period_end, units_sold, avg_daily) VALUES
(1, 1, '2026-03-01', '2026-03-31', 45,  1.45),
(2, 1, '2026-03-01', '2026-03-31', 12,  0.39),
(3, 1, '2026-03-01', '2026-03-31', 8,   0.26),
(5, 1, '2026-03-01', '2026-03-31', 120, 3.87),
(6, 1, '2026-03-01', '2026-03-31', 35,  1.13);

SET FOREIGN_KEY_CHECKS = 1;
