from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from extensions import db
from models import Inventory, StockMovement, Product
from middleware.auth_middleware import require_permission
from services.inventory_service import (
    adjust_stock, transfer_between_warehouses,
    get_low_stock_items, predict_stockout
)
from utils.error_handler import success_response, error_response, paginated_response

inventory_bp = Blueprint("inventory", __name__)

@inventory_bp.get("")
@jwt_required()
def list_inventory():
    page     = max(1, request.args.get("page", 1, int))
    per_page = min(request.args.get("per_page", 25, int), 100)
    warehouse_id = request.args.get("warehouse_id", type=int)
    product_id   = request.args.get("product_id", type=int)
    status       = request.args.get("status", "").lower()

    q = Inventory.query
    if warehouse_id:
        q = q.filter_by(warehouse_id=warehouse_id)
    if product_id:
        q = q.filter_by(product_id=product_id)
    if status == "low":
        q = (q.join(Product, Inventory.product_id == Product.product_id)
               .filter(Inventory.quantity <= Product.reorder_level,
                       Product.deleted_at.is_(None)))
    elif status == "out":
        q = q.filter(Inventory.quantity == 0)

    total = q.count()
    rows  = q.offset((page - 1) * per_page).limit(per_page).all()
    return paginated_response([r.to_dict() for r in rows], page, per_page, total)

@inventory_bp.post("/adjust")
@require_permission("inventory:write")
def adjust():
    data    = request.get_json(silent=True) or {}
    user_id = int(int(get_jwt_identity()))
    for f in ("product_id", "warehouse_id", "quantity", "movement_type"):
        if not data.get(f):
            return error_response(f"Missing field: {f}", 400)

    mt = data["movement_type"].upper()
    if mt not in ("IN", "OUT", "ADJUSTMENT"):
        return error_response("movement_type must be IN, OUT, or ADJUSTMENT.", 400)

    qty_delta = data["quantity"] if mt == "IN" else -abs(data["quantity"])
    result = adjust_stock(
        product_id=data["product_id"], warehouse_id=data["warehouse_id"],
        qty_delta=qty_delta, movement_type=mt,
        performed_by=user_id,
        reference=data.get("reference"), notes=data.get("notes"),
        ip=request.remote_addr,
    )
    if not result["success"]:
        return error_response(result["error"], 400)
    return success_response(data=result["inventory"].to_dict(),
                            message="Stock adjusted successfully.")

@inventory_bp.post("/transfer")
@require_permission("inventory:write")
def transfer():
    data    = request.get_json(silent=True) or {}
    user_id = int(int(get_jwt_identity()))
    for f in ("product_id", "from_warehouse_id", "to_warehouse_id", "quantity"):
        if not data.get(f):
            return error_response(f"Missing field: {f}", 400)
    if data["from_warehouse_id"] == data["to_warehouse_id"]:
        return error_response("Source and destination must differ.", 400)

    result = transfer_between_warehouses(
        product_id=data["product_id"],
        from_warehouse_id=data["from_warehouse_id"],
        to_warehouse_id=data["to_warehouse_id"],
        quantity=data["quantity"], performed_by=user_id,
        notes=data.get("notes"), ip=request.remote_addr,
    )
    if not result["success"]:
        return error_response(result["error"], 400)
    return success_response(
        data={"source": result["source"].to_dict(),
              "destination": result["destination"].to_dict()},
        message="Transfer completed.")

@inventory_bp.get("/movements")
@jwt_required()
def movements():
    page     = max(1, request.args.get("page", 1, int))
    per_page = min(request.args.get("per_page", 25, int), 100)
    q = StockMovement.query.order_by(StockMovement.created_at.desc())
    if request.args.get("product_id"):
        q = q.filter_by(product_id=request.args.get("product_id", type=int))
    if request.args.get("warehouse_id"):
        q = q.filter_by(warehouse_id=request.args.get("warehouse_id", type=int))
    total = q.count()
    rows  = q.offset((page - 1) * per_page).limit(per_page).all()
    return paginated_response([r.to_dict() for r in rows], page, per_page, total)

@inventory_bp.get("/low-stock")
@jwt_required()
def low_stock():
    warehouse_id = request.args.get("warehouse_id", type=int)
    items = get_low_stock_items(warehouse_id=warehouse_id)
    return success_response(data=[i.to_dict() for i in items])

@inventory_bp.get("/predict-stockout")
@jwt_required()
def stockout_prediction():
    results = predict_stockout(
        product_id=request.args.get("product_id", type=int),
        warehouse_id=request.args.get("warehouse_id", type=int),
    )
    return success_response(data=results)
