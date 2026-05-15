from flask import current_app
from extensions import db, socketio
from models import Order, OrderItem, Customer, Product, Inventory, Shipment, Notification, User, ActivityTimeline

def _notify_user(user_id, type_, severity, title, message, link=None):
    try:
        n = Notification(user_id=user_id, type=type_, severity=severity,
                         title=title, message=message, link=link)
        db.session.add(n)
        db.session.flush()
        socketio.emit("notification", n.to_dict(), room=f"user_{user_id}")
    except Exception:
        pass

def _log_timeline(user_id, entity_type, entity_id, action, description):
    try:
        db.session.add(ActivityTimeline(
            user_id=user_id, entity_type=entity_type,
            entity_id=entity_id, title=action, description=description,
        ))
    except Exception:
        pass

def _find_best_warehouse(product_id, quantity):
    rows = (db.session.query(Inventory)
            .filter_by(product_id=product_id)
            .filter(Inventory.quantity - Inventory.reserved_qty >= 1)
            .order_by((Inventory.quantity - Inventory.reserved_qty).desc())
            .all())
    return rows

def place_order(customer_id, items, notes, created_by, ip=None):
    try:
        customer = db.session.get(Customer, customer_id)
        if not customer or customer.deleted_at:
            return {"success": False, "error": "Customer not found."}

        fulfillment_lines = []
        for item in items:
            pid     = item["product_id"]
            needed  = item["quantity"]
            product = db.session.get(Product, pid)
            if not product or product.deleted_at:
                return {"success": False, "error": f"Product {pid} not found."}

            wh_options = _find_best_warehouse(pid, needed)
            if not wh_options:
                return {"success": False,
                        "error": f"No stock available for '{product.name}'."}

            remaining = needed
            for inv in wh_options:
                if remaining <= 0:
                    break
                take = min(remaining, inv.available)
                fulfillment_lines.append({
                    "product_id":   pid,
                    "warehouse_id": inv.warehouse_id,
                    "quantity":     take,
                    "unit_price":   float(product.unit_price),
                })
                remaining -= take

            if remaining > 0:
                return {"success": False,
                        "error": f"Insufficient total stock for '{product.name}'. Short by {remaining}."}

        for line in fulfillment_lines:
            inv = (Inventory.query
                   .filter_by(product_id=line["product_id"], warehouse_id=line["warehouse_id"])
                   .with_for_update().first())
            inv.reserved_qty += line["quantity"]

        order = Order(
            customer_id=customer_id,
            status="PENDING",
            notes=notes,
            placed_by=created_by,
        )
        db.session.add(order)
        db.session.flush()

        total = 0
        for line in fulfillment_lines:
            lt = line["quantity"] * line["unit_price"]
            total += lt
            db.session.add(OrderItem(
                order_id=order.order_id,
                product_id=line["product_id"],
                warehouse_id=line["warehouse_id"],
                quantity=line["quantity"],
                unit_price=line["unit_price"],
            ))

        order.total_amount = total
        order.grand_total  = total

        _log_timeline(created_by, "order", order.order_id,
                      "Order Created", f"Order placed for {customer.name}")

        db.session.commit()
        db.session.refresh(order)
        return {"success": True, "order": order}

    except Exception as exc:
        db.session.rollback()
        current_app.logger.error(f"place_order error: {exc}", exc_info=True)
        return {"success": False, "error": str(exc)}

def approve_order(order_id, approver_id, ip=None):
    try:
        order = db.session.get(Order, order_id)
        if not order or order.deleted_at:
            return {"success": False, "error": "Order not found."}
        if order.status != "PENDING":
            return {"success": False, "error": f"Cannot approve order with status '{order.status}'."}

        order.status      = "APPROVED"
        order.approved_by = approver_id

        _log_timeline(approver_id, "order", order.order_id,
                      "Order Approved", f"Approved by user #{approver_id}")
        _notify_user(order.placed_by, "ORDER", "INFO",
                     f"Order {order.order_number} Approved",
                     "Your order has been approved.",
                     link=f"/orders/{order.order_id}")

        db.session.commit()
        return {"success": True, "order": order}

    except Exception as exc:
        db.session.rollback()
        current_app.logger.error(f"approve_order error: {exc}", exc_info=True)
        return {"success": False, "error": str(exc)}

def cancel_order(order_id, cancelled_by, reason=None, ip=None):
    try:
        order = db.session.get(Order, order_id)
        if not order or order.deleted_at:
            return {"success": False, "error": "Order not found."}
        if order.status not in {"PENDING", "APPROVED", "PROCESSING"}:
            return {"success": False,
                    "error": f"Cannot cancel order with status '{order.status}'."}

        order.status        = "CANCELLED"
        order.cancel_reason = reason

        for item in order.items:
            inv = Inventory.query.filter_by(
                product_id=item.product_id,
                warehouse_id=item.warehouse_id
            ).first()
            if inv:
                inv.reserved_qty = max(0, inv.reserved_qty - item.quantity)

        _log_timeline(cancelled_by, "order", order.order_id,
                      "Order Cancelled", reason or "Cancelled by user")

        db.session.commit()
        return {"success": True, "order": order}

    except Exception as exc:
        db.session.rollback()
        current_app.logger.error(f"cancel_order error: {exc}", exc_info=True)
        return {"success": False, "error": str(exc)}
