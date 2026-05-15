from functools import wraps
from flask import g
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from extensions import db
from models import User

def _load_current_user():
    if hasattr(g, "_current_user"):
        return g._current_user
    user_id = int(get_jwt_identity())
    user = db.session.get(User, user_id)
    g._current_user = user
    return user

def _has_permission(role_perms, permission: str) -> bool:
    if not role_perms or not isinstance(role_perms, list):
        return False

    namespace = permission.split(":")[0]
    for perm in role_perms:
        if perm == permission:
            return True
        if perm == f"{namespace}:*":
            return True
        if perm == "*" or perm.endswith(":*") and perm.split(":")[0] == namespace:
            return True
    return False

def require_permission(*permissions):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            user = _load_current_user()

            if not user or user.deleted_at is not None:
                return {"success": False, "error": "User not found or inactive."}, 401
            if user.is_locked():
                return {"success": False, "error": "Account is locked."}, 403

            role_name = user.role.role_name if user.role else ""
            if role_name == "Administrator":
                return fn(*args, **kwargs)

            role_perms = user.role.permissions if user.role else []
            granted = any(_has_permission(role_perms, p) for p in permissions)

            if not granted:
                return {
                    "success": False,
                    "error": f"Permission denied. Required one of: {list(permissions)}"
                }, 403

            return fn(*args, **kwargs)
        return wrapper
    return decorator

def require_roles(*roles):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            user = _load_current_user()
            if not user or user.deleted_at is not None:
                return {"success": False, "error": "User not found."}, 401
            role_name = user.role.role_name if user.role else ""
            if role_name not in roles:
                return {"success": False,
                        "error": f"Role '{role_name}' not permitted."}, 403
            return fn(*args, **kwargs)
        return wrapper
    return decorator

def jwt_required_flexible(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        user = _load_current_user()
        if not user:
            return {"success": False, "error": "User not found."}, 401
        return fn(*args, **kwargs)
    return wrapper

def get_current_user():
    return getattr(g, "_current_user", None)
