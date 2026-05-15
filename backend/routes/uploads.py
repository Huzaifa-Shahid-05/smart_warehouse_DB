import os
import uuid
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required

uploads_bp = Blueprint("uploads", __name__)

IMAGES_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "..", "frontend", "images"
)
ALLOWED  = {"jpg", "jpeg", "png", "webp", "gif"}
MAX_SIZE = 5 * 1024 * 1024

@uploads_bp.post("/product-image")
@jwt_required()
def upload_product_image():
    if "image" not in request.files:
        return jsonify({"success": False, "error": "No image file provided."}), 400

    file = request.files["image"]
    if not file.filename:
        return jsonify({"success": False, "error": "Empty filename."}), 400

    ext = file.filename.rsplit(".", 1)[-1].lower()
    if ext not in ALLOWED:
        return jsonify({"success": False,
                        "error": f"Not allowed. Use: {', '.join(ALLOWED)}"}), 400

    data = file.read()
    if len(data) > MAX_SIZE:
        return jsonify({"success": False, "error": "File too large. Max 5MB."}), 400

    filename  = f"{uuid.uuid4().hex}.{ext}"
    os.makedirs(IMAGES_DIR, exist_ok=True)
    with open(os.path.join(IMAGES_DIR, filename), "wb") as f:
        f.write(data)

    return jsonify({"success": True, "url": f"/images/{filename}"})
