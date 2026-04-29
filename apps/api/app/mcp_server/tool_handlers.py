from decimal import Decimal

from sqlalchemy.orm import Session

from app.schemas import CancelOrderInput, CreateOrderInput, OrderItemInput
from app.services import orders as order_service
from app.services import restaurants as restaurant_service


def search_restaurants(
    db: Session,
    query: str | None = None,
    cuisine: str | None = None,
    max_budget: float | None = None,
) -> dict:
    budget = Decimal(str(max_budget)) if max_budget is not None else None
    return {"restaurants": restaurant_service.search_restaurants(db, query, cuisine, budget)}


def get_restaurant_detail(db: Session, restaurant_id: str) -> dict:
    return {"restaurant": restaurant_service.get_public_restaurant(db, restaurant_id)}


def get_menu(db: Session, restaurant_id: str) -> dict:
    return restaurant_service.get_menu(db, restaurant_id, public_only=True)


def create_order(
    db: Session,
    restaurant_id: str,
    items: list[dict],
    customer_name: str | None = "Guest",
    customer_contact: str | None = None,
    fulfillment_type: str = "pickup",
    notes: str | None = None,
) -> dict:
    payload = CreateOrderInput(
        restaurant_id=restaurant_id,
        items=[OrderItemInput(**item) for item in items],
        customer_name=customer_name,
        customer_contact=customer_contact,
        fulfillment_type=fulfillment_type,
        notes=notes,
    )
    order = order_service.create_order(db, payload)
    return {
        "order_id": order["id"],
        "status": order["status"],
        "restaurant_id": order["restaurant_id"],
        "order_number": order["order_number"],
        "total_price": order["total_price"],
        "message": order["status_message"],
    }


def get_order_status(db: Session, order_id: str) -> dict:
    order = order_service.get_order_status(db, order_id)
    return {
        "order_id": order["id"],
        "status": order["status"],
        "restaurant_id": order["restaurant_id"],
        "order_number": order["order_number"],
        "updated_at": order["updated_at"],
        "message": order["status_message"],
    }


def cancel_order(db: Session, order_id: str, reason: str | None = None) -> dict:
    payload = CancelOrderInput(reason=reason)
    order = order_service.cancel_order(db, order_id, payload.reason)
    return {"order_id": order["id"], "status": order["status"]}
