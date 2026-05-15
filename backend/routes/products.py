from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from extensions import db
from models import Product, Inventory
from middleware.auth_middleware import require_permission
from utils.error_handler import success_response, error_response, paginated_response

products_bp = Blueprint("products", __name__)

@products_bp.get("")
@jwt_required()
def list_products():
    page         = max(1, request.args.get("page", 1, int))
    per_page     = min(request.args.get("per_page", 25, int), 100)
    search       = request.args.get("search", "").strip()
    category_id  = request.args.get("category_id", type=int)
    show_deleted = request.args.get("show_deleted", "false").lower() == "true"
    include_stock= request.args.get("include_stock", "false").lower() == "true"

    q = Product.query
    if not show_deleted:
        q = q.filter(Product.deleted_at.is_(None))
    if search:
        q = q.filter(Product.name.ilike(f"%{search}%"))
    if category_id:
        q = q.filter_by(category_id=category_id)

    total    = q.count()
    products = q.order_by(Product.name).offset((page - 1) * per_page).limit(per_page).all()
    return paginated_response(
        [p.to_dict(include_stock=include_stock) for p in products],
        page, per_page, total
    )

@products_bp.get("/<int:product_id>")
@jwt_required()
def get_product(product_id):
    p = db.session.get(Product, product_id)
    if not p:
        return error_response("Product not found.", 404)
    return success_response(data=p.to_dict(include_stock=True))

@products_bp.get("/barcode/<barcode>")
@jwt_required()
def get_by_barcode(barcode):
    p = Product.query.filter_by(barcode=barcode).first()
    if not p:
        return error_response("No product found with that barcode.", 404)
    return success_response(data=p.to_dict(include_stock=True))

@products_bp.post("")
@require_permission("products:write")
def create_product():
    data = request.get_json(silent=True) or {}
    for f in ("sku", "name", "unit_price", "cost_price", "category_id"):
        if not data.get(f):
            return error_response(f"'{f}' is required.", 400)
    if Product.query.filter_by(sku=data["sku"]).first():
        return error_response(f"SKU '{data['sku']}' already exists.", 409)

    p = Product(
        sku=data["sku"], name=data["name"],
        barcode=data.get("barcode"),
        description=data.get("description"),
        unit_price=data["unit_price"],
        cost_price=data.get("cost_price", 0),
        reorder_level=data.get("reorder_level", 10),
        reorder_quantity=data.get("reorder_quantity", 50),
        category_id=data["category_id"],
        primary_supplier_id=data.get("supplier_id"),
    )
    db.session.add(p)
    db.session.commit()
    return success_response(data=p.to_dict(), status=201)

@products_bp.put("/<int:product_id>")
@require_permission("products:write")
def update_product(product_id):
    p = db.session.get(Product, product_id)
    if not p or p.deleted_at:
        return error_response("Product not found.", 404)
    data = request.get_json(silent=True) or {}
    for f in ("name", "description", "unit_price", "cost_price",
              "reorder_level", "reorder_quantity", "category_id", "barcode"):
        if f in data:
            setattr(p, f, data[f])
    db.session.commit()
    return success_response(data=p.to_dict())

@products_bp.delete("/<int:product_id>")
@require_permission("products:write")
def delete_product(product_id):
    p = db.session.get(Product, product_id)
    if not p or p.deleted_at:
        return error_response("Product not found.", 404)
    p.soft_delete()
    db.session.commit()
    return success_response(message=f"Product '{p.name}' deleted.")

@products_bp.get("/<int:product_id>/inventory")
@jwt_required()
def product_inventory(product_id):
    rows = Inventory.query.filter_by(product_id=product_id).all()
    return success_response(data=[r.to_dict() for r in rows])
