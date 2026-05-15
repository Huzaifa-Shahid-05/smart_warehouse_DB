import bcrypt as bcrypt_lib
from flask import Blueprint, request
from flask_jwt_extended import jwt_required
from extensions import db
from models import User, Role
from middleware.auth_middleware import require_permission
from utils.error_handler import success_response, error_response, paginated_response

users_bp = Blueprint("users", __name__)

@users_bp.get("")
@require_permission("users:read")
def list_users():
    page     = max(1, request.args.get("page", 1, int))
    per_page = min(request.args.get("per_page", 25, int), 100)
    q        = User.active().order_by(User.full_name)
    total    = q.count()
    users    = q.offset((page - 1) * per_page).limit(per_page).all()
    return paginated_response([u.to_dict() for u in users], page, per_page, total)

@users_bp.get("/<int:uid>")
@require_permission("users:read")
def get_user(uid):
    u = db.session.get(User, uid)
    if not u or u.deleted_at:
        return error_response("User not found.", 404)
    return success_response(data=u.to_dict())

@users_bp.post("")
@require_permission("users:write")
def create_user():
    data = request.get_json(silent=True) or {}
    for f in ("full_name", "username", "email", "password", "role_id"):
        if not data.get(f):
            return error_response(f"'{f}' is required.", 400)
    if User.query.filter_by(email=data["email"].lower()).first():
        return error_response("Email already registered.", 409)
    pw_hash = bcrypt_lib.hashpw(data["password"].encode(), bcrypt_lib.gensalt(rounds=4)).decode()
    u = User(
        full_name=data["full_name"], username=data["username"],
        email=data["email"].lower(), password_hash=pw_hash, role_id=data["role_id"],
    )
    db.session.add(u)
    db.session.commit()
    return success_response(data=u.to_dict(), status=201)

@users_bp.put("/<int:uid>")
@require_permission("users:write")
def update_user(uid):
    u = db.session.get(User, uid)
    if not u or u.deleted_at:
        return error_response("User not found.", 404)
    data = request.get_json(silent=True) or {}
    if "full_name" in data: u.full_name = data["full_name"]
    if "role_id"   in data: u.role_id   = data["role_id"]
    if "is_active" in data: u.is_active  = bool(data["is_active"])
    if "password"  in data and data["password"]:
        u.password_hash = bcrypt_lib.hashpw(
            data["password"].encode(), bcrypt_lib.gensalt(rounds=4)).decode()
    db.session.commit()
    return success_response(data=u.to_dict())

@users_bp.delete("/<int:uid>")
@require_permission("users:write")
def delete_user(uid):
    u = db.session.get(User, uid)
    if not u or u.deleted_at:
        return error_response("User not found.", 404)
    u.soft_delete()
    db.session.commit()
    return success_response(message="User deactivated.")
