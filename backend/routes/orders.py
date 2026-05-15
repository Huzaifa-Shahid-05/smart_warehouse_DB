from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from extensions import db
from models import Order, ActivityTimeline
from middleware.auth_middleware import require_permission
from services.order_service import place_order, approve_order, cancel_order
from utils.error_handler import success_response, error_response, paginated_response

orders_bp = Blueprint("orders", __name__)

@orders_bp.get("")
@jwt_required()
def list_orders():
    page     = max(1, request.args.get("page", 1, int))
    per_page = min(request.args.get("per_page", 25, int), 100)
    status   = request.args.get("status", "").upper()
    q = Order.active().order_by(Order.placed_at.desc())
    if status and status in Order.STATUSES:
        q = q.filter_by(status=status)
    total  = q.count()
    orders = q.offset((page - 1) * per_page).limit(per_page).all()
    return paginated_response([o.to_dict() for o in orders], page, per_page, total)

@orders_bp.get("/<int:order_id>")
@jwt_required()
def get_order(order_id):
    order = db.session.get(Order, order_id)
    if not order or order.deleted_at:
        return error_response("Order not found.", 404)
    timeline = (ActivityTimeline.query
                .filter_by(entity_type="order", entity_id=order_id)
                .order_by(ActivityTimeline.created_at.asc()).all())
    data = order.to_dict(include_items=True)
    data["timeline"] = [t.to_dict() for t in timeline]
    return success_response(data=data)

@orders_bp.post("")
@require_permission("orders:write")
def create_order():
    data    = request.get_json(silent=True) or {}
    user_id = int(int(get_jwt_identity()))
    if not data.get("customer_id") or not data.get("items"):
        return error_response("customer_id and items are required.", 400)
    result = place_order(
        customer_id=data["customer_id"], items=data["items"],
        notes=data.get("notes", ""), created_by=user_id,
        ip=request.remote_addr,
    )
    if not result["success"]:
        return error_response(result["error"], 400)
    return success_response(data=result["order"].to_dict(include_items=True), status=201)

@orders_bp.post("/<int:order_id>/approve")
@require_permission("orders:approve")
def approve(order_id):
    user_id = int(int(get_jwt_identity()))
    result  = approve_order(order_id, user_id, ip=request.remote_addr)
    if not result["success"]:
        return error_response(result["error"], 400)
    return success_response(data=result["order"].to_dict(), message="Order approved.")

@orders_bp.post("/<int:order_id>/cancel")
@require_permission("orders:write")
def cancel(order_id):
    user_id = int(int(get_jwt_identity()))
    data    = request.get_json(silent=True) or {}
    result  = cancel_order(order_id, user_id, reason=data.get("reason"),
                           ip=request.remote_addr)
    if not result["success"]:
        return error_response(result["error"], 400)
    return success_response(data=result["order"].to_dict(), message="Order cancelled.")
