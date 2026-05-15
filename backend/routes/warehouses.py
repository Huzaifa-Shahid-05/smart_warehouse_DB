from flask import Blueprint, request
from flask_jwt_extended import jwt_required
from extensions import db
from models import Warehouse
from middleware.auth_middleware import require_permission
from utils.error_handler import success_response, error_response

warehouses_bp = Blueprint("warehouses", __name__)

@warehouses_bp.get("")
@jwt_required()
def list_warehouses():
    whs = Warehouse.active().order_by(Warehouse.name).all()
    return success_response(data=[w.to_dict() for w in whs])

@warehouses_bp.get("/<int:wid>")
@jwt_required()
def get_warehouse(wid):
    w = db.session.get(Warehouse, wid)
    if not w or w.deleted_at:
        return error_response("Warehouse not found.", 404)
    return success_response(data=w.to_dict())

@warehouses_bp.post("")
@require_permission("warehouses:write")
def create_warehouse():
    data = request.get_json(silent=True) or {}
    for f in ("code", "name"):
        if not data.get(f):
            return error_response(f"'{f}' is required.", 400)
    if Warehouse.query.filter_by(code=data["code"]).first():
        return error_response(f"Code '{data['code']}' already exists.", 409)
    w = Warehouse(
        code=data["code"], name=data["name"],
        address=data.get("address", ""),
        city=data.get("city", ""), country=data.get("country", "Pakistan"),
        capacity_units=data.get("capacity", 10000),
        manager_id=data.get("manager_id"),
    )
    db.session.add(w)
    db.session.commit()
    return success_response(data=w.to_dict(), status=201)

@warehouses_bp.put("/<int:wid>")
@require_permission("warehouses:write")
def update_warehouse(wid):
    w = db.session.get(Warehouse, wid)
    if not w or w.deleted_at:
        return error_response("Warehouse not found.", 404)
    data = request.get_json(silent=True) or {}
    for f in ("name", "address", "city", "capacity_units", "manager_id"):
        if f in data:
            setattr(w, f, data[f])
    db.session.commit()
    return success_response(data=w.to_dict())

@warehouses_bp.delete("/<int:wid>")
@require_permission("warehouses:write")
def delete_warehouse(wid):
    w = db.session.get(Warehouse, wid)
    if not w or w.deleted_at:
        return error_response("Warehouse not found.", 404)
    w.soft_delete()
    db.session.commit()
    return success_response(message="Warehouse deleted.")
