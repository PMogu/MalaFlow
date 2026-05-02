from decimal import Decimal
import logging
import time
from collections.abc import Callable
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.database import SessionLocal
from app.models import MenuItem, Order, OrderItem, Restaurant, utcnow
from app.schemas import CreateOrderInput
from app.services.formatters import order_out
from app.services.notifications import notify_new_order_sms

logger = logging.getLogger(__name__)

ORDER_WAIT_POLL_SECONDS = 10
ORDER_AUTO_REJECT_SECONDS = 5 * 60
AUTO_REJECT_REASON = "No pickup number was assigned within 5 minutes."


def _load_order(db: Session, order_id: str) -> Order:
    order = db.scalar(select(Order).options(selectinload(Order.items)).where(Order.id == order_id))
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ORDER_NOT_FOUND")
    return order


def _assert_restaurant_access(order: Order, restaurant_id: str | None, is_admin: bool = False) -> None:
    if is_admin:
        return
    if order.restaurant_id != restaurant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="FORBIDDEN")


def _aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _apply_auto_reject_if_expired(db: Session, order: Order, now: datetime | None = None) -> bool:
    if order.status != "submitted":
        return False
    current = now or utcnow()
    elapsed = (_aware_utc(current) - _aware_utc(order.created_at)).total_seconds()
    if elapsed < ORDER_AUTO_REJECT_SECONDS:
        return False
    order.status = "rejected"
    order.reject_reason = AUTO_REJECT_REASON
    db.commit()
    db.refresh(order)
    return True


def create_order(db: Session, payload: CreateOrderInput) -> dict:
    restaurant = db.get(Restaurant, payload.restaurant_id)
    if not restaurant or not restaurant.mcp_visible or restaurant.status != "open":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="RESTAURANT_NOT_AVAILABLE")
    if payload.fulfillment_type not in (restaurant.service_modes or []):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="FULFILLMENT_NOT_SUPPORTED")

    menu_ids = [item.menu_item_id for item in payload.items]
    menu_items = db.scalars(
        select(MenuItem).where(MenuItem.restaurant_id == payload.restaurant_id, MenuItem.id.in_(menu_ids))
    ).all()
    by_id = {item.id: item for item in menu_items}
    total = Decimal("0.00")
    order_items: list[OrderItem] = []
    for request_item in payload.items:
        item = by_id.get(request_item.menu_item_id)
        if not item or not item.available:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="MENU_ITEM_UNAVAILABLE")
        total += item.price * request_item.quantity
        order_items.append(
            OrderItem(
                menu_item_id=item.id,
                name_snapshot=item.name,
                price_snapshot=item.price,
                quantity=request_item.quantity,
                notes=request_item.notes,
            )
        )

    order = Order(
        restaurant_id=payload.restaurant_id,
        status="submitted",
        customer_name=payload.customer_name,
        customer_contact=payload.customer_contact,
        fulfillment_type=payload.fulfillment_type,
        notes=payload.notes,
        total_price=total,
        items=order_items,
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    loaded_order = _load_order(db, order.id)
    try:
        notify_new_order_sms(db, loaded_order)
    except Exception:
        logger.exception("Order %s was created, but notification dispatch failed", order.id)
    return order_out(loaded_order)


def list_restaurant_orders(db: Session, restaurant_id: str) -> list[dict]:
    orders = db.scalars(
        select(Order)
        .options(selectinload(Order.items))
        .where(Order.restaurant_id == restaurant_id)
        .order_by(Order.created_at.desc())
    ).all()
    for order in orders:
        _apply_auto_reject_if_expired(db, order)
    return [order_out(order) for order in orders]


def get_order_status(db: Session, order_id: str) -> dict:
    order = _load_order(db, order_id)
    _apply_auto_reject_if_expired(db, order)
    return order_out(order)


def accept_order(db: Session, order_id: str, restaurant_id: str | None, order_number: str, is_admin: bool = False) -> dict:
    order = _load_order(db, order_id)
    _assert_restaurant_access(order, restaurant_id, is_admin)
    _apply_auto_reject_if_expired(db, order)
    if order.status != "submitted":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="INVALID_ORDER_STATE")
    if not order_number.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ORDER_NUMBER_REQUIRED")
    order.status = "accepted"
    order.order_number = order_number.strip()
    db.commit()
    db.refresh(order)
    return order_out(_load_order(db, order.id))


def reject_order(db: Session, order_id: str, restaurant_id: str | None, reason: str | None, is_admin: bool = False) -> dict:
    order = _load_order(db, order_id)
    _assert_restaurant_access(order, restaurant_id, is_admin)
    _apply_auto_reject_if_expired(db, order)
    if order.status != "submitted":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="INVALID_ORDER_STATE")
    order.status = "rejected"
    order.reject_reason = reason
    db.commit()
    db.refresh(order)
    return order_out(_load_order(db, order.id))


def cancel_order(db: Session, order_id: str, reason: str | None = None) -> dict:
    order = _load_order(db, order_id)
    _apply_auto_reject_if_expired(db, order)
    if order.status != "submitted":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="INVALID_ORDER_STATE")
    order.status = "cancelled"
    order.cancel_reason = reason
    db.commit()
    db.refresh(order)
    return order_out(_load_order(db, order.id))


def wait_for_order_result(
    order_id: str,
    poll_seconds: int = ORDER_WAIT_POLL_SECONDS,
    timeout_seconds: int = ORDER_AUTO_REJECT_SECONDS,
    sleep_fn: Callable[[float], None] = time.sleep,
    session_factory: Callable[[], Session] = SessionLocal,
) -> dict:
    deadline = time.monotonic() + timeout_seconds
    while True:
        db = session_factory()
        try:
            order = _load_order(db, order_id)
            _apply_auto_reject_if_expired(db, order)
            if order.status != "submitted":
                return order_out(order)
            remaining_seconds = deadline - time.monotonic()
            if remaining_seconds <= 0:
                order.status = "rejected"
                order.reject_reason = AUTO_REJECT_REASON
                db.commit()
                db.refresh(order)
                return order_out(_load_order(db, order.id))
        finally:
            db.close()
        sleep_fn(min(poll_seconds, remaining_seconds))
