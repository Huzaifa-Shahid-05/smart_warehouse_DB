"""
WebSocket events for real-time notifications.
Import this module in app.py AFTER socketio is initialized.
"""
from flask import request
from flask_jwt_extended import decode_token
from flask_socketio import join_room, leave_room, emit

from extensions import socketio, db
from models import User, Notification


@socketio.on("connect")
def on_connect(auth):
    """Client connects — authenticate via JWT in auth dict."""
    token = (auth or {}).get("token", "")
    if not token:
        return False  # reject

    try:
        decoded = decode_token(token)
        user_id = decoded["sub"]
        user    = db.session.get(User, user_id)
        if not user or not user.is_active or user.deleted_at:
            return False
        join_room(f"user_{user_id}")
        # Send unread count on connect
        unread = Notification.query.filter_by(user_id=user_id, is_read=False).count()
        emit("unread_count", {"count": unread})
    except Exception:
        return False


@socketio.on("disconnect")
def on_disconnect():
    pass


@socketio.on("join_room")
def on_join(data):
    room = data.get("room")
    if room:
        join_room(room)


@socketio.on("leave_room")
def on_leave(data):
    room = data.get("room")
    if room:
        leave_room(room)


@socketio.on("mark_read")
def on_mark_read(data):
    """Client emits mark_read with notification_id."""
    nid     = data.get("notification_id")
    token   = data.get("token", "")
    try:
        user_id = decode_token(token)["sub"]
        n = Notification.query.filter_by(id=nid, user_id=user_id).first()
        if n:
            n.is_read = True
            db.session.commit()
            unread = Notification.query.filter_by(user_id=user_id, is_read=False).count()
            emit("unread_count", {"count": unread}, room=f"user_{user_id}")
    except Exception:
        pass
