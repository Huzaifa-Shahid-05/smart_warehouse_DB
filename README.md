# Smart Warehouse Management System

A full-stack warehouse management system for tracking inventory, orders, shipments, and suppliers in real time, with role-based access and automated stock alerts.

## Features

- **Authentication & Authorization** — JWT-based login with role-based access control and account lockout after repeated failed attempts.
- **Inventory Management** — Real-time stock tracking across multiple warehouses, with automatic low-stock alerts via database triggers.
- **Order Management** — Full order lifecycle from creation to fulfillment, with automatic status timeline logging.
- **Shipment Tracking** — Manage outbound shipments linked to orders and warehouses.
- **Supplier Management** — Track suppliers, purchase orders, and supplier performance metrics.
- **Demand Prediction & Stock Reservation** — Stored procedures for stockout prediction and automated stock reservation/fulfillment matching.
- **Real-Time Notifications** — WebSocket-based live notifications (unread counts, alerts) via Socket.IO.
- **Reports & Exports** — Downloadable CSV and PDF reports for inventory, orders, suppliers, and audit logs, plus a KPI dashboard.
- **Audit Logging** — Full audit trail of user actions and record changes.

## Technology Stack

**Backend**
- Python, Flask
- Flask-SQLAlchemy (ORM)
- Flask-JWT-Extended (authentication)
- Flask-SocketIO (real-time WebSocket communication)
- Flask-CORS
- Marshmallow (serialization/validation)
- PyMySQL + MySQL (database)
- ReportLab (PDF generation)
- Bcrypt (password hashing)

**Frontend**
- HTML, CSS, JavaScript (vanilla)

**Database**
- MySQL — with triggers, stored procedures, and views for automated business logic (low-stock alerts, order timelines, stock reservation, stockout prediction)

## Process

1. **Database Design** — Designed a normalized MySQL schema (users, products, inventory, orders, shipments, suppliers, notifications, audit logs, etc.) along with triggers and stored procedures to automate stock alerts, order tracking, and fulfillment logic.
2. **Backend Development** — Built a Flask REST API organized into blueprints (auth, users, products, inventory, orders, shipments, suppliers, warehouses, reports, notifications), secured with JWT authentication and role-based middleware.
3. **Real-Time Layer** — Integrated Flask-SocketIO to push live notifications and stock alerts to connected clients.
4. **Frontend Development** — Built a multi-page frontend (dashboard, inventory, orders, shipments, suppliers, reports) that consumes the REST API.
5. **Reporting** — Implemented CSV/PDF export endpoints for inventory, orders, suppliers, and audit data using ReportLab.
6. **Testing & Iteration** — Verified core workflows (stock updates, order placement, notifications) end-to-end before finalizing.

## How to Run

### Prerequisites
- Python 3.12+
- MySQL Server

### 1. Set up the database
```bash
mysql -u root -p < database/01_schema.sql
mysql -u root -p < database/02_triggers_views_procs.sql
mysql -u root -p < database/03_seed_data.sql
```

### 2. Set up the backend
```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

pip install -r requirements.txt
```

Create a `.env` file in `backend/` with your database credentials:
```
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=smart_warehouse
```

### 3. Run the application
```bash
python app.py
```

The app will be available at:
```
http://localhost:5000
```

The Flask server serves both the API (`/api/*`) and the frontend pages directly, so no separate frontend server is needed.
