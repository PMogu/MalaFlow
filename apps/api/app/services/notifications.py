import logging

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.config import get_settings
from app.models import Order, User

logger = logging.getLogger(__name__)


def _order_item_summary(order: Order) -> str:
    items = [f"{item.quantity}x {item.name_snapshot}" for item in order.items]
    summary = ", ".join(items)
    return summary[:140] if summary else "new order"


def _ensure_sms_ready(settings: Settings) -> None:
    if settings.app_env != "production":
        raise RuntimeError("SMS_REQUIRES_PRODUCTION")
    if not (
        settings.twilio_account_sid
        and settings.twilio_auth_token
        and settings.twilio_messaging_service_sid
    ):
        raise RuntimeError("TWILIO_NOT_CONFIGURED")


def _send_sms(to_phone: str, body: str) -> str | None:
    settings = get_settings()
    _ensure_sms_ready(settings)
    from twilio.rest import Client

    client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
    message = client.messages.create(
        messaging_service_sid=settings.twilio_messaging_service_sid,
        to=to_phone,
        body=body,
    )
    return getattr(message, "sid", None)


def notify_new_order_sms(db: Session, order: Order) -> None:
    settings = get_settings()
    try:
        _ensure_sms_ready(settings)
    except RuntimeError as exc:
        logger.info("Skipping order SMS: %s", exc)
        return

    account = db.scalar(
        select(User)
        .where(
            User.restaurant_id == order.restaurant_id,
            User.role == "restaurant",
            User.is_active.is_(True),
        )
        .order_by(User.created_at.asc())
    )
    if not account or not account.phone:
        logger.warning("Skipping order SMS: no active restaurant phone for order %s", order.id)
        return

    try:
        short_order_id = order.id.replace("order_", "")[:8]
        _send_sms(
            account.phone,
            (
                f"New MalaFlow order {short_order_id}: {_order_item_summary(order)}. "
                "Open the workspace and assign a pickup number."
            ),
        )
    except Exception:
        logger.exception("Failed to send Twilio order SMS for order %s", order.id)


def send_test_order_sms(db: Session, restaurant_id: str) -> dict:
    account = db.scalar(
        select(User)
        .where(
            User.restaurant_id == restaurant_id,
            User.role == "restaurant",
            User.is_active.is_(True),
        )
        .order_by(User.created_at.asc())
    )
    if not account or not account.phone:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="NO_ACTIVE_RESTAURANT_PHONE",
        )

    body = "Test MalaFlow order: 1x Sample dish. Open the workspace and assign a pickup number."
    try:
        message_sid = _send_sms(account.phone, body)
    except Exception as exc:
        logger.exception("Failed to send Twilio test SMS for restaurant %s", restaurant_id)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"SMS_SEND_FAILED: {exc}",
        ) from exc
    return {"ok": True, "phone": account.phone, "message_sid": message_sid}
