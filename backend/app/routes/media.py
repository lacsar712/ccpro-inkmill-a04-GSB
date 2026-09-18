from decimal import Decimal, InvalidOperation

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required

from app.database import SessionLocal
from app.models.media_issue import MediaIssue
from app.models.media_stock import MediaStock
from app.models.mill import Mill
from app.models.workshop import Workshop
from app.serializers import media_issue_json, media_stock_json
from app.utils import error, normalize_datetime

bp = Blueprint("media", __name__, url_prefix="/api/media")


def _parse_qty(body: dict):
    raw = body.get("qtyKg")
    try:
        qty = Decimal(str(raw)).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        return None, "领用数量(kg)必须为数字"
    if qty <= 0:
        return None, "领用数量(kg)必须大于 0"
    return qty, None


@bp.get("/stocks")
@jwt_required()
def list_stocks():
    db = SessionLocal()
    try:
        rows = (
            db.query(MediaStock)
            .join(Workshop, MediaStock.workshop_id == Workshop.id)
            .order_by(Workshop.id, MediaStock.media_type, MediaStock.id)
            .all()
        )
        return jsonify([media_stock_json(r) for r in rows])
    finally:
        db.close()


@bp.get("/issues")
@jwt_required()
def list_issues():
    db = SessionLocal()
    try:
        rows = (
            db.query(MediaIssue)
            .order_by(MediaIssue.issued_at.desc(), MediaIssue.id.desc())
            .all()
        )
        return jsonify([media_issue_json(r) for r in rows])
    finally:
        db.close()


@bp.post("/issues")
@jwt_required()
def create_issue():
    body = request.get_json(silent=True) or {}

    workshop_id = int(body.get("workshopId") or 0)
    if workshop_id <= 0:
        return error("请选择领用车间", 400)

    media_type = str(body.get("mediaType", "")).strip()
    if not media_type:
        return error("研磨珠类型不能为空", 400)

    qty, qty_err = _parse_qty(body)
    if qty_err:
        return error(qty_err, 400)

    issued_at = str(body.get("issuedAt", "")).strip()
    if not issued_at:
        return error("发料时间不能为空", 400)

    operator_name = str(body.get("operatorName", "")).strip()
    if not operator_name:
        return error("操作员（领用人）不能为空", 400)

    mill_id_raw = body.get("millId")
    mill_id = None
    if mill_id_raw not in (None, "", 0, "0"):
        try:
            mill_id = int(mill_id_raw)
        except (TypeError, ValueError):
            return error("研磨机无效", 400)

    db = SessionLocal()
    try:
        workshop = db.get(Workshop, workshop_id)
        if not workshop:
            return error("领用车间不存在", 400)

        if mill_id is not None:
            mill = db.get(Mill, mill_id)
            if not mill:
                return error("研磨机不存在", 400)
            if mill.workshop_id != workshop_id:
                return error("研磨机不属于所选车间，不能跨车间发料", 400)

        # 锁定该车间该介质库存行，避免并发发料扣成负库存
        stock = (
            db.query(MediaStock)
            .filter(
                MediaStock.workshop_id == workshop_id,
                MediaStock.media_type == media_type,
            )
            .with_for_update()
            .first()
        )
        if stock is None:
            return error(f"车间「{workshop.name}」暂无「{media_type}」研磨珠库存，无法发料", 409)
        if stock.on_hand_kg < qty:
            return error(
                f"研磨珠库存不足：当前结余 {stock.on_hand_kg} kg，本次领用 {qty} kg", 409
            )

        stock.on_hand_kg = stock.on_hand_kg - qty
        row = MediaIssue(
            workshop_id=workshop_id,
            mill_id=mill_id,
            media_type=media_type,
            qty_kg=qty,
            issued_at=normalize_datetime(issued_at),
            operator_name=operator_name,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return jsonify(media_issue_json(row)), 201
    finally:
        db.close()
