from datetime import datetime
from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from extensions import db
from models import Shipment, Order, ActivityTimeline
from middleware.auth_middleware import require_permission
from utils.error_handler import success_response, error_response, paginated_response

shipments_bp = Blueprint("shipments", __name__)

@shipments_bp.get("")
@jwt_required()
def list_shipments():
    page     = max(1, request.args.get("page", 1, int))
    per_page = min(request.args.get("per_page", 25, int), 100)
    status   = request.args.get("status", "").upper()
    q = Shipment.query.order_by(Shipment.created_at.desc())
    if status:
        q = q.filter_by(status=status)
    total     = q.count()
    shipments = q.offset((page - 1) * per_page).limit(per_page).all()
    return paginated_response([s.to_dict() for s in shipments], page, per_page, total)

@shipments_bp.get("/<int:shipment_id>")
@jwt_required()
def get_shipment(shipment_id):
    s = db.session.get(Shipment, shipment_id)
    if not s:
        return error_response("Shipment not found.", 404)
    timeline = (ActivityTimeline.query
                .filter_by(entity_type="shipment", entity_id=shipment_id)
                .order_by(ActivityTimeline.created_at.asc()).all())
    data = s.to_dict()
    data["timeline"] = [t.to_dict() for t in timeline]
    return success_response(data=data)

@shipments_bp.post("")
@require_permission("shipments:write")
def create_shipment():
    data    = request.get_json(silent=True) or {}
    user_id = int(int(get_jwt_identity()))
    if not data.get("order_id"):
        return error_response("order_id is required.", 400)
    order = db.session.get(Order, data["order_id"])
    if not order:
        return error_response("Order not found.", 404)
    s = Shipment(
        order_id=data["order_id"],
        warehouse_id=data.get("warehouse_id", 1),
        assigned_employee=data.get("assigned_to", user_id),
        carrier=data.get("carrier"),
        notes=data.get("notes"),
    )
    db.session.add(s)
    db.session.commit()
    db.session.refresh(s)
    return success_response(data=s.to_dict(), status=201)

@shipments_bp.patch("/<int:shipment_id>/status")
@require_permission("shipments:write")
def update_status(shipment_id):
    s = db.session.get(Shipment, shipment_id)
    if not s:
        return error_response("Shipment not found.", 404)
    data   = request.get_json(silent=True) or {}
    status = data.get("status", "").upper()
    if status not in Shipment.STATUSES:
        return error_response(f"Invalid status. Valid: {Shipment.STATUSES}", 400)

    s.status = status
    if status == "DELIVERED":
        s.delivered_at = datetime.utcnow()
        if s.order:
            s.order.status = "DELIVERED"
    elif status == "IN_TRANSIT":
        s.shipped_at = datetime.utcnow()

    user_id = int(int(get_jwt_identity()))
    db.session.add(ActivityTimeline(
        user_id=user_id, entity_type="shipment", entity_id=shipment_id,
        title=f"Status → {status}", description=data.get("notes", ""),
    ))
    db.session.commit()
    return success_response(data=s.to_dict())
