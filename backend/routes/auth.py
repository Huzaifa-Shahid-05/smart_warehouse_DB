from datetime import timedelta, datetime

import bcrypt
from flask import Blueprint, request, current_app
from flask_jwt_extended import (
    create_access_token, create_refresh_token,
    jwt_required, get_jwt_identity, get_jwt,
)

from extensions import db
from models import User, TokenBlocklist
from utils.error_handler import success_response, error_response

auth_bp = Blueprint("auth", __name__)

@auth_bp.post("/login")
def login():
    data     = request.get_json(silent=True) or {}
    email    = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not email or not password:
        return error_response("Email and password are required.", 400)

    user = User.query.filter_by(email=email).first()

    if not user or user.deleted_at:
        return error_response("Invalid credentials.", 401)

    if not user.is_active:
        return error_response("Account is disabled. Contact an administrator.", 403)

    if user.is_locked():
        unlock_in = int((user.locked_until - datetime.utcnow()).total_seconds() // 60) + 1
        return error_response(
            f"Account locked due to too many failed attempts. "
            f"Try again in {unlock_in} minute(s).", 403
        )

    cfg = current_app.config

    if not bcrypt.checkpw(password.encode(), user.password_hash.encode()):
        user.register_failed_login(
            cfg.get("MAX_FAILED_LOGINS", 5),
            cfg.get("LOCKOUT_MINUTES", 15),
        )
        db.session.commit()
        return error_response("Invalid credentials.", 401)

    user.clear_login_failures()
    db.session.commit()

    access_token = create_access_token(
        identity=str(user.user_id),
        expires_delta=timedelta(seconds=cfg.get("JWT_ACCESS_TOKEN_EXPIRES", 900)),
        additional_claims={"role": user.role.role_name if user.role else ""},
    )
    refresh_token = create_refresh_token(
        identity=str(user.user_id),
        expires_delta=timedelta(seconds=cfg.get("JWT_REFRESH_TOKEN_EXPIRES", 604800)),
    )

    return success_response(
        data={
            "access_token":  access_token,
            "refresh_token": refresh_token,
            "user": user.to_dict(),
        },
        message="Login successful.",
    )

@auth_bp.post("/logout")
@jwt_required()
def logout():
    from datetime import datetime, timedelta
    jwt_data = get_jwt()
    jti      = jwt_data["jti"]
    user_id  = int(get_jwt_identity())
    exp      = datetime.utcfromtimestamp(jwt_data["exp"])
    db.session.add(TokenBlocklist(jti=jti, user_id=user_id, expires_at=exp))
    db.session.commit()
    return success_response(message="Logged out successfully.")

@auth_bp.post("/refresh")
@jwt_required(refresh=True)
def refresh():
    user_id      = int(get_jwt_identity())
    cfg          = current_app.config
    access_token = create_access_token(
        identity=user_id,
        expires_delta=timedelta(seconds=cfg.get("JWT_ACCESS_TOKEN_EXPIRES", 900)),
    )
    return success_response(data={"access_token": access_token})

@auth_bp.get("/me")
@jwt_required()
def me():
    user = db.session.get(User, int(get_jwt_identity()))
    if not user:
        return error_response("User not found.", 404)
    return success_response(data=user.to_dict())
