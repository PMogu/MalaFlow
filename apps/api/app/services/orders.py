from decimal import Decimal
import logging

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import MenuItem, Order, OrderItem, Restaurant
from app.schemas import CreateOrderInput
from app.services.formatters import order_out
from app.services.notifications import notify_new_order_sms

logger = logging.getLogger(__name__)


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
    return [order_out(order) for order in orders]


def get_order_status(db: Session, order_id: str) -> dict:
    order = _load_order(db, order_id)
    return order_out(order)


def accept_order(db: Session, order_id: str, restaurant_id: str | None, order_number: str, is_admin: bool = False) -> dict:
    order = _load_order(db, order_id)
    _assert_restaurant_access(order, restaurant_id, is_admin)
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
    if order.status != "submitted":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="INVALID_ORDER_STATE")
    order.status = "rejected"
    order.reject_reason = reason
    db.commit()
    db.refresh(order)
    return order_out(_load_order(db, order.id))


def cancel_order(db: Session, order_id: str, reason: str | None = None) -> dict:
    order = _load_order(db, order_id)
    if order.status != "submitted":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="INVALID_ORDER_STATE")
    order.status = "cancelled"
    order.cancel_reason = reason
    db.commit()
    db.refresh(order)
    return order_out(_load_order(db, order.id))
