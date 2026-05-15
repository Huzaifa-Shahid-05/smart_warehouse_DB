from datetime import datetime
from sqlalchemy import text
from flask import current_app

from extensions import db
from models import Inventory, StockMovement, Product, Warehouse, AuditLog, ActivityTimeline, Notification, User

def _set_session_user(user_id):
    try:
        db.session.execute(text("SET @current_user_id = :uid"), {"uid": user_id})
    except Exception:
        pass

def _log_audit(user_id, action, entity_type, entity_id, old_val, new_val, ip=None):
    try:
        entry = AuditLog(
            user_id=user_id, action=action,
            entity_type=entity_type, entity_id=entity_id,
            old_value=old_val, new_value=new_val,
            ip_address=ip,
        )
        db.session.add(entry)
    except Exception:
        pass

def _log_timeline(user_id, entity_type, entity_id, action, description, metadata=None):
    try:
        entry = ActivityTimeline(
            user_id=user_id, entity_type=entity_type,
            entity_id=entity_id, title=action,
            description=description,
        )
        db.session.add(entry)
    except Exception:
        pass

def adjust_stock(product_id, warehouse_id, qty_delta, movement_type,
                 performed_by, reference=None, notes=None, ip=None):
    try:
        _set_session_user(performed_by)

        inv = (Inventory.query
               .filter_by(product_id=product_id, warehouse_id=warehouse_id)
               .with_for_update().first())

        if inv is None:
            if qty_delta < 0:
                return {"success": False, "error": "No inventory record found."}
            inv = Inventory(product_id=product_id, warehouse_id=warehouse_id, quantity=0, reserved_qty=0)
            db.session.add(inv)
            db.session.flush()

        if movement_type == "OUT" and inv.available < abs(qty_delta):
            return {"success": False,
                    "error": f"Insufficient stock. Available: {inv.available}, Requested: {abs(qty_delta)}"}

        qty_before   = inv.quantity
        inv.quantity += qty_delta
        if inv.quantity < 0:
            return {"success": False, "error": "Stock cannot go below zero."}

        movement = StockMovement(
            product_id=product_id, warehouse_id=warehouse_id,
            movement_type=movement_type,
            quantity=abs(qty_delta),
            reference_type="MANUAL",
            notes=notes or reference,
            performed_by=performed_by,
        )
        db.session.add(movement)
        _log_timeline(performed_by, "inventory", inv.inventory_id,
                      f"Stock {movement_type}",
                      f"{movement_type} {abs(qty_delta)} units")
        db.session.commit()
        return {"success": True, "inventory": inv}

    except Exception as exc:
        db.session.rollback()
        current_app.logger.error(f"adjust_stock error: {exc}", exc_info=True)
        return {"success": False, "error": str(exc)}

def transfer_between_warehouses(product_id, from_warehouse_id, to_warehouse_id,
                                 quantity, performed_by, notes=None, ip=None):
    try:
        _set_session_user(performed_by)

        src = (Inventory.query
               .filter_by(product_id=product_id, warehouse_id=from_warehouse_id)
               .with_for_update().first())

        if not src or src.available < quantity:
            avail = src.available if src else 0
            return {"success": False,
                    "error": f"Insufficient stock in source warehouse. Available: {avail}"}

        dst = (Inventory.query
               .filter_by(product_id=product_id, warehouse_id=to_warehouse_id)
               .with_for_update().first())
        if dst is None:
            dst = Inventory(product_id=product_id, warehouse_id=to_warehouse_id,
                            quantity=0, reserved_qty=0)
            db.session.add(dst)
            db.session.flush()

        src.quantity -= quantity
        dst.quantity += quantity

        db.session.add(StockMovement(
            product_id=product_id, warehouse_id=from_warehouse_id,
            movement_type="TRANSFER", quantity=quantity,
            reference_type="TRANSFER", notes=notes, performed_by=performed_by,
        ))
        db.session.add(StockMovement(
            product_id=product_id, warehouse_id=to_warehouse_id,
            movement_type="TRANSFER", quantity=quantity,
            reference_type="TRANSFER", notes=notes, performed_by=performed_by,
        ))

        db.session.commit()
        return {"success": True, "source": src, "destination": dst}

    except Exception as exc:
        db.session.rollback()
        current_app.logger.error(f"transfer error: {exc}", exc_info=True)
        return {"success": False, "error": str(exc)}

def reserve_stock(product_id, warehouse_id, quantity, performed_by):
    try:
        inv = (Inventory.query
               .filter_by(product_id=product_id, warehouse_id=warehouse_id)
               .with_for_update().first())
        if not inv or inv.available < quantity:
            avail = inv.available if inv else 0
            return {"success": False,
                    "message": f"Insufficient stock. Available: {avail}"}
        inv.reserved_qty += quantity
        db.session.commit()
        return {"success": True, "message": "Stock reserved."}
    except Exception as exc:
        db.session.rollback()
        return {"success": False, "error": str(exc)}

def release_stock(product_id, warehouse_id, quantity, performed_by):
    try:
        inv = (Inventory.query
               .filter_by(product_id=product_id, warehouse_id=warehouse_id)
               .with_for_update().first())
        if not inv:
            return {"success": False, "error": "Inventory record not found."}
        inv.reserved_qty = max(0, inv.reserved_qty - quantity)
        db.session.commit()
        return {"success": True, "released": quantity}
    except Exception as exc:
        db.session.rollback()
        return {"success": False, "error": str(exc)}

def get_low_stock_items(warehouse_id=None):
    q = (db.session.query(Inventory)
         .join(Product, Inventory.product_id == Product.product_id)
         .filter(Product.deleted_at.is_(None),
                 Inventory.quantity <= Product.reorder_level))
    if warehouse_id:
        q = q.filter(Inventory.warehouse_id == warehouse_id)
    return q.all()

def predict_stockout(product_id=None, warehouse_id=None):
    try:
        from models import DemandHistory
        q = (db.session.query(
                Inventory.product_id,
                Inventory.warehouse_id,
                Inventory.quantity,
                Product.name.label("product_name"),
                Product.reorder_level,
                db.func.avg(DemandHistory.avg_daily).label("avg_daily")
             )
             .join(Product, Inventory.product_id == Product.product_id)
             .outerjoin(DemandHistory, db.and_(
                 DemandHistory.product_id == Inventory.product_id,
                 DemandHistory.warehouse_id == Inventory.warehouse_id
             ))
             .filter(Product.deleted_at.is_(None)))

        if product_id:
            q = q.filter(Inventory.product_id == product_id)
        if warehouse_id:
            q = q.filter(Inventory.warehouse_id == warehouse_id)

        q = q.group_by(Inventory.product_id, Inventory.warehouse_id,
                       Inventory.quantity, Product.name, Product.reorder_level)

        results = []
        for row in q.all():
            avg = float(row.avg_daily or 1)
            days = round(row.quantity / avg, 1) if avg > 0 else 999
            status = "CRITICAL" if days <= 3 else "WARNING" if days <= 7 else "OK"
            results.append({
                "product_id": row.product_id,
                "warehouse_id": row.warehouse_id,
                "product_name": row.product_name,
                "quantity": row.quantity,
                "avg_daily": avg,
                "days_until_stockout": days,
                "status": status,
            })
        return [r for r in results if r["status"] != "OK"]
    except Exception as exc:
        current_app.logger.error(f"predict_stockout error: {exc}", exc_info=True)
        return []
