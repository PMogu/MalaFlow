import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Order, User

logger = logging.getLogger(__name__)


def _order_item_summary(order: Order) -> str:
    items = [f"{item.quantity}x {item.name_snapshot}" for item in order.items]
    summary = ", ".join(items)
    return summary[:140] if summary else "new order"


def notify_new_order_sms(db: Session, order: Order) -> None:
    settings = get_settings()
    if settings.app_env != "production":
        logger.info("Skipping order SMS outside production")
        return
    if not (
        settings.twilio_account_sid
        and settings.twilio_auth_token
        and settings.twilio_messaging_service_sid
    ):
        logger.info("Skipping order SMS: Twilio is not configured")
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
        from twilio.rest import Client

        client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
        short_order_id = order.id.replace("order_", "")[:8]
        client.messages.create(
            messaging_service_sid=settings.twilio_messaging_service_sid,
            to=account.phone,
            body=(
                f"New MalaFlow order {short_order_id}: {_order_item_summary(order)}. "
                "Open the workspace and assign a pickup number."
            ),
        )
    except Exception:
        logger.exception("Failed to send Twilio order SMS for order %s", order.id)
