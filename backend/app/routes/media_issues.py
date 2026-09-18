from decimal import Decimal, InvalidOperation

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required

from app.database import SessionLocal
from app.models.media_issue import MediaIssue
from app.models.media_stock import MediaStock
from app.models.mill import Mill
from app.models.workshop import Workshop
from app.serializers import media_issue_json
from app.utils import error, normalize_datetime

bp = Blueprint("media_issues", __name__, url_prefix="/api/media-issues")


def _validate(body: dict) -> tuple[dict | None, str | None]:
    workshop_id = int(body.get("workshopId") or 0)
    if workshop_id <= 0:
        return None, "请选择车间"

    mill_id_raw = body.get("millId")
    mill_id = None
    if mill_id_raw not in (None, "", 0, "0"):
        mill_id = int(mill_id_raw)

    media_type = str(body.get("mediaType", "")).strip()
    if not media_type:
        return None, "研磨介质不能为空"

    try:
        qty_kg = Decimal(str(body.get("qtyKg", ""))).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        return None, "发料重量(kg)必须大于 0"
    if qty_kg <= 0:
        return None, "发料重量(kg)必须大于 0"

    operator_name = str(body.get("operatorName", "")).strip()
    if not operator_name:
        return None, "操作员不能为空"

    db = SessionLocal()
    try:
        if not db.get(Workshop, workshop_id):
            return None, "车间不存在"
        if mill_id is not None:
            mill = db.get(Mill, mill_id)
            if not mill:
                return None, "研磨机不存在"
            if mill.workshop_id != workshop_id:
                return None, "研磨机不属于所选车间，不能发料"
    finally:
        db.close()

    issued_at = normalize_datetime(str(body.get("issuedAt", "")).strip())

    return (
        {
            "workshop_id": workshop_id,
            "mill_id": mill_id,
            "media_type": media_type,
            "qty_kg": qty_kg,
            "issued_at": issued_at,
            "operator_name": operator_name,
        },
        None,
    )


@bp.get("")
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


@bp.post("")
@jwt_required()
def create_issue():
    body = request.get_json(silent=True) or {}
    data, err = _validate(body)
    if err:
        return error(err, 400)

    db = SessionLocal()
    try:
        # 锁定本车间该介质的库存行，避免并发发料扣成负数
        stock = (
            db.query(MediaStock)
            .filter(
                MediaStock.workshop_id == data["workshop_id"],
                MediaStock.media_type == data["media_type"],
            )
            .with_for_update()
            .first()
        )

        if stock is None:
            # 无库存行视同结存 0，不允许凭空发料
            return error(
                f"库存不足：{data['media_type']} 在该车间无库存，无法发料", 409
            )
        if stock.on_hand_kg < data["qty_kg"]:
            return error(
                f"库存不足：{data['media_type']} 当前结存 {stock.on_hand_kg} kg，"
                f"无法发放 {data['qty_kg']} kg",
                409,
            )

        stock.on_hand_kg = stock.on_hand_kg - data["qty_kg"]
        row = MediaIssue(**data)
        db.add(row)
        db.commit()
        db.refresh(row)
        return jsonify(media_issue_json(row)), 201
    finally:
        db.close()
