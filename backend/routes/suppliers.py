from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from extensions import db
from models import Supplier, SupplierOrder, SupplierOrderItem
from middleware.auth_middleware import require_permission
from services.supplier_service import recalculate_performance, receive_purchase_order
from utils.error_handler import success_response, error_response, paginated_response

suppliers_bp = Blueprint("suppliers", __name__)

@suppliers_bp.get("")
@jwt_required()
def list_suppliers():
    page     = max(1, request.args.get("page", 1, int))
    per_page = min(request.args.get("per_page", 25, int), 100)
    q        = Supplier.active().order_by(Supplier.name)
    total    = q.count()
    sups     = q.offset((page - 1) * per_page).limit(per_page).all()
    return paginated_response([s.to_dict() for s in sups], page, per_page, total)

@suppliers_bp.get("/<int:sid>")
@jwt_required()
def get_supplier(sid):
    s = db.session.get(Supplier, sid)
    if not s or s.deleted_at:
        return error_response("Supplier not found.", 404)
    return success_response(data=s.to_dict())

@suppliers_bp.post("")
@require_permission("suppliers:write")
def create_supplier():
    data = request.get_json(silent=True) or {}
    if not data.get("name") or not data.get("code"):
        return error_response("name and code are required.", 400)
    s = Supplier(
        code=data["code"], name=data["name"],
        contact_person=data.get("contact_person"),
        email=data.get("email", ""), phone=data.get("phone"),
        address=data.get("address"), city=data.get("city"),
    )
    db.session.add(s)
    db.session.commit()
    return success_response(data=s.to_dict(), status=201)

@suppliers_bp.put("/<int:sid>")
@require_permission("suppliers:write")
def update_supplier(sid):
    s = db.session.get(Supplier, sid)
    if not s or s.deleted_at:
        return error_response("Supplier not found.", 404)
    data = request.get_json(silent=True) or {}
    for f in ("name", "contact_person", "email", "phone", "address", "city"):
        if f in data:
            setattr(s, f, data[f])
    db.session.commit()
    return success_response(data=s.to_dict())

@suppliers_bp.delete("/<int:sid>")
@require_permission("suppliers:write")
def delete_supplier(sid):
    s = db.session.get(Supplier, sid)
    if not s or s.deleted_at:
        return error_response("Supplier not found.", 404)
    s.soft_delete()
    db.session.commit()
    return success_response(message="Supplier deleted.")

@suppliers_bp.get("/<int:sid>/performance")
@jwt_required()
def performance(sid):
    result = recalculate_performance(sid)
    return success_response(data=result) if result["success"] else error_response(result["error"])

@suppliers_bp.get("/purchase-orders")
@jwt_required()
def list_pos():
    page     = max(1, request.args.get("page", 1, int))
    per_page = min(request.args.get("per_page", 25, int), 100)
    q        = SupplierOrder.query.order_by(SupplierOrder.placed_at.desc())
    if request.args.get("supplier_id"):
        q = q.filter_by(supplier_id=request.args.get("supplier_id", type=int))
    total = q.count()
    pos   = q.offset((page - 1) * per_page).limit(per_page).all()
    return paginated_response([p.to_dict(include_items=True) for p in pos], page, per_page, total)

@suppliers_bp.post("/purchase-orders")
@require_permission("suppliers:write")
def create_po():
    data    = request.get_json(silent=True) or {}
    user_id = int(int(get_jwt_identity()))
    if not data.get("supplier_id") or not data.get("items"):
        return error_response("supplier_id and items are required.", 400)
    po = SupplierOrder(
        supplier_id=data["supplier_id"],
        warehouse_id=data.get("warehouse_id", 1),
        expected_delivery=data.get("expected_delivery"),
        notes=data.get("notes"),
        placed_by=user_id,
    )
    db.session.add(po)
    db.session.flush()
    for item in data["items"]:
        db.session.add(SupplierOrderItem(
            po_id=po.po_id, product_id=item["product_id"],
            quantity=item["ordered_qty"], unit_cost=item.get("unit_cost", 0),
        ))
    db.session.commit()
    db.session.refresh(po)
    return success_response(data=po.to_dict(include_items=True), status=201)

@suppliers_bp.post("/purchase-orders/<int:po_id>/receive")
@require_permission("suppliers:write")
def receive_po(po_id):
    data    = request.get_json(silent=True) or {}
    user_id = int(int(get_jwt_identity()))
    result  = receive_purchase_order(
        po_id=po_id, received_items=data.get("items", []),
        received_by=user_id, ip=request.remote_addr,
    )
    if not result["success"]:
        return error_response(result["error"], 400)
    return success_response(data=result["po"].to_dict(include_items=True),
                            message=f"PO status: {result['status']}")
