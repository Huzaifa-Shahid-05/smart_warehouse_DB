from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from extensions import db
from models import Notification
from utils.error_handler import success_response, error_response, paginated_response

notifications_bp = Blueprint("notifications", __name__)

@notifications_bp.get("")
@jwt_required()
def list_notifications():
    user_id  = int(get_jwt_identity())
    page     = max(1, request.args.get("page", 1, int))
    per_page = min(request.args.get("per_page", 20, int), 100)
    unread   = request.args.get("unread", "false").lower() == "true"
    q = Notification.query.filter_by(user_id=user_id)
    if unread:
        q = q.filter_by(is_read=False)
    q     = q.order_by(Notification.created_at.desc())
    total = q.count()
    items = q.offset((page - 1) * per_page).limit(per_page).all()
    return paginated_response([n.to_dict() for n in items], page, per_page, total)

@notifications_bp.post("/<int:nid>/read")
@jwt_required()
def mark_read(nid):
    user_id = int(int(get_jwt_identity()))
    n = Notification.query.filter_by(notification_id=nid, user_id=user_id).first()
    if not n:
        return error_response("Notification not found.", 404)
    n.is_read = True
    db.session.commit()
    return success_response(message="Marked as read.")

@notifications_bp.post("/read-all")
@jwt_required()
def mark_all_read():
    user_id = int(int(get_jwt_identity()))
    Notification.query.filter_by(user_id=user_id, is_read=False).update({"is_read": True})
    db.session.commit()
    return success_response(message="All notifications marked as read.")
