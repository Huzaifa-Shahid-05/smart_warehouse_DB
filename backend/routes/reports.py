"""Reports routes — fixed for actual schema column names."""
import csv
import io
from datetime import datetime
from flask import Blueprint, request, send_file, jsonify
from flask_jwt_extended import jwt_required
from extensions import db
from models import Inventory, Product, Order, Supplier, AuditLog, Warehouse

reports_bp = Blueprint("reports", __name__)

@reports_bp.get("/kpis")
@jwt_required()
def kpis_json():
    from sqlalchemy import func, text as sa_text

    total_orders   = Order.active().count()
    pending_orders = Order.active().filter_by(status="PENDING").count()
    low_stock_count= (db.session.query(func.count(Inventory.inventory_id))
                      .join(Product, Inventory.product_id == Product.product_id)
                      .filter(Inventory.quantity <= Product.reorder_level,
                              Product.deleted_at.is_(None)).scalar() or 0)
    inv_value = float(
        db.session.query(func.sum(Inventory.quantity * Product.cost_price))
        .join(Product, Inventory.product_id == Product.product_id)
        .filter(Product.deleted_at.is_(None)).scalar() or 0
    )

    try:
        monthly = db.session.execute(sa_text("""
            SELECT DATE_FORMAT(placed_at, '%b %Y') AS label,
                   YEAR(placed_at) AS yr, MONTH(placed_at) AS mo,
                   COUNT(*) AS orders
            FROM orders
            WHERE deleted_at IS NULL
              AND placed_at >= DATE_SUB(NOW(), INTERVAL 12 MONTH)
            GROUP BY label, yr, mo
            ORDER BY yr, mo
        """)).fetchall()
        monthly_data = [{"label": r.label, "orders": r.orders} for r in monthly]
    except Exception:
        monthly_data = []

    return jsonify({
        "success": True,
        "data": {
            "total_orders":    total_orders,
            "pending_orders":  pending_orders,
            "low_stock_items": low_stock_count,
            "inventory_value": inv_value,
            "monthly_trend":   monthly_data,
        }
    })

@reports_bp.get("/inventory/csv")
@jwt_required()
def inventory_csv():
    rows = Inventory.query.all()
    out  = io.StringIO()
    w    = csv.writer(out)
    w.writerow(["product_id","product","sku","warehouse","quantity","reserved","available","reorder_level"])
    for r in rows:
        w.writerow([
            r.product_id,
            r.product.name if r.product else "",
            r.product.sku  if r.product else "",
            r.warehouse.name if r.warehouse else "",
            r.quantity, r.reserved_qty, r.available,
            r.product.reorder_level if r.product else 0,
        ])
    buf = io.BytesIO(out.getvalue().encode())
    return send_file(buf, mimetype="text/csv",
                     download_name="inventory.csv", as_attachment=True)

@reports_bp.get("/inventory/pdf")
@jwt_required()
def inventory_pdf():
    try:
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet

        rows_data = Inventory.query.all()
        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=landscape(A4))
        styles = getSampleStyleSheet()
        elements = [Paragraph("Smart Warehouse — Inventory Report", styles["Title"]),
                    Paragraph(f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}", styles["Normal"]),
                    Spacer(1, 12)]

        table_data = [["Product", "SKU", "Warehouse", "On Hand", "Reserved", "Available", "Reorder At"]]
        for r in rows_data:
            table_data.append([
                r.product.name if r.product else "—",
                r.product.sku  if r.product else "—",
                r.warehouse.name if r.warehouse else "—",
                str(r.quantity), str(r.reserved_qty), str(r.available),
                str(r.product.reorder_level if r.product else 0),
            ])

        t = Table(table_data)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#4f46e5")),
            ("TEXTCOLOR",  (0,0), (-1,0), colors.white),
            ("FONTNAME",   (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE",   (0,0), (-1,-1), 8),
            ("GRID",       (0,0), (-1,-1), 0.4, colors.lightgrey),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#f4f4f4")]),
        ]))
        elements.append(t)
        doc.build(elements)
        buf.seek(0)
        return send_file(buf, mimetype="application/pdf",
                         download_name="inventory_report.pdf", as_attachment=True)
    except ImportError:
        return jsonify({"success": False, "error": "reportlab not installed"}), 500

@reports_bp.get("/orders/csv")
@jwt_required()
def orders_csv():
    orders = Order.active().order_by(Order.placed_at.desc()).limit(1000).all()
    out    = io.StringIO()
    w      = csv.writer(out)
    w.writerow(["order_number","customer","status","total_amount","placed_at"])
    for o in orders:
        w.writerow([
            o.order_number, o.customer.name if o.customer else "",
            o.status, o.total(),
            o.placed_at.isoformat() if o.placed_at else "",
        ])
    buf = io.BytesIO(out.getvalue().encode())
    return send_file(buf, mimetype="text/csv",
                     download_name="orders.csv", as_attachment=True)

@reports_bp.get("/orders/pdf")
@jwt_required()
def orders_pdf():
    return inventory_csv()

@reports_bp.get("/suppliers/pdf")
@jwt_required()
def suppliers_pdf():
    sups = Supplier.active().all()
    out  = io.StringIO()
    w    = csv.writer(out)
    w.writerow(["name","rating","total_orders","on_time_orders","on_time_rate"])
    for s in sups:
        w.writerow([s.name, s.rating, s.total_orders, s.on_time_orders, s.on_time_rate()])
    buf = io.BytesIO(out.getvalue().encode())
    return send_file(buf, mimetype="text/csv",
                     download_name="suppliers.csv", as_attachment=True)

@reports_bp.get("/suppliers/csv")
@jwt_required()
def suppliers_csv():
    return suppliers_pdf()

@reports_bp.get("/audit/csv")
@jwt_required()
def audit_csv():
    logs = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(1000).all()
    out  = io.StringIO()
    w    = csv.writer(out)
    w.writerow(["id","user_id","action","entity_type","entity_id","ip","created_at"])
    for log in logs:
        w.writerow([log.log_id, log.user_id, log.action, log.entity_type,
                    log.entity_id, log.ip_address,
                    log.created_at.isoformat() if log.created_at else ""])
    buf = io.BytesIO(out.getvalue().encode())
    return send_file(buf, mimetype="text/csv",
                     download_name="audit_trail.csv", as_attachment=True)
