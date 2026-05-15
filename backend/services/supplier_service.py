from datetime import date
from flask import current_app
from extensions import db
from models import Supplier, SupplierOrder, SupplierOrderItem, ActivityTimeline
from services.inventory_service import adjust_stock

def recalculate_performance(supplier_id):
    try:
        supplier = db.session.get(Supplier, supplier_id)
        if not supplier or supplier.deleted_at:
            return {"success": False, "error": "Supplier not found."}

        received = (SupplierOrder.query
                    .filter_by(supplier_id=supplier_id, status="RECEIVED").all())
        if not received:
            return {"success": True, "rating": 0.0}

        on_time = 0
        total_ordered = 0
        total_received = 0

        for po in received:
            if po.actual_delivery and po.expected_delivery:
                if po.actual_delivery <= po.expected_delivery:
                    on_time += 1
            for item in po.items:
                total_ordered  += item.quantity
                total_received += item.received_qty

        total = len(received)
        ot_rate   = on_time / total if total else 0
        ful_rate  = total_received / total_ordered if total_ordered else 0
        score     = round((ot_rate * 0.5 + ful_rate * 0.5) * 5, 2)

        supplier.rating         = score
        supplier.total_orders   = total
        supplier.on_time_orders = on_time
        db.session.commit()
        return {"success": True, "rating": score, "total_orders": total}

    except Exception as exc:
        db.session.rollback()
        current_app.logger.error(f"recalculate_performance error: {exc}", exc_info=True)
        return {"success": False, "error": str(exc)}

def receive_purchase_order(po_id, received_items, received_by, received_date=None, ip=None):
    try:
        po = db.session.get(SupplierOrder, po_id)
        if not po:
            return {"success": False, "error": "Purchase order not found."}
        if po.status == "RECEIVED":
            return {"success": False, "error": "PO already fully received."}

        if received_date is None:
            received_date = date.today()

        for recv in received_items:
            item = db.session.get(SupplierOrderItem, recv["po_item_id"])
            if not item or item.po_id != po_id:
                return {"success": False, "error": f"PO item {recv['po_item_id']} not found."}

            qty   = recv["received_qty"]
            wh_id = recv.get("warehouse_id") or po.warehouse_id
            if not qty or qty <= 0:
                continue

            item.received_qty = min(item.received_qty + qty, item.quantity)
            result = adjust_stock(
                product_id=item.product_id, warehouse_id=wh_id,
                qty_delta=qty, movement_type="IN",
                performed_by=received_by,
                notes=f"PO#{po.po_number}", ip=ip,
            )
            if not result["success"]:
                return {"success": False, "error": result["error"]}

        fully = all(i.received_qty >= i.quantity for i in po.items)
        po.status = "RECEIVED" if fully else "ACKNOWLEDGED"
        if fully:
            po.actual_delivery = received_date

        db.session.add(ActivityTimeline(
            user_id=received_by, entity_type="supplier_order",
            entity_id=po.po_id,
            title="PO Received" if fully else "PO Partially Received",
            description=f"{po.po_number} → {po.status}",
        ))
        db.session.commit()

        if fully:
            recalculate_performance(po.supplier_id)

        return {"success": True, "po": po, "status": po.status}

    except Exception as exc:
        db.session.rollback()
        current_app.logger.error(f"receive_po error: {exc}", exc_info=True)
        return {"success": False, "error": str(exc)}
