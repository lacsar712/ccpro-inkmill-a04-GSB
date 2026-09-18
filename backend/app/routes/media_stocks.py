from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required

from app.database import SessionLocal
from app.models.media_stock import MediaStock
from app.serializers import media_stock_json

bp = Blueprint("media_stocks", __name__, url_prefix="/api/media-stocks")


@bp.get("")
@jwt_required()
def list_stocks():
    db = SessionLocal()
    try:
        rows = (
            db.query(MediaStock)
            .order_by(MediaStock.workshop_id.asc(), MediaStock.media_type.asc())
            .all()
        )
        return jsonify([media_stock_json(r) for r in rows])
    finally:
        db.close()
