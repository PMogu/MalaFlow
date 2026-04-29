from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import CancelOrderInput, CreateOrderInput
from app.services import orders as order_service
from app.services import restaurants as restaurant_service

router = APIRouter(prefix="/api/public", tags=["public"])


@router.get("/restaurants/search")
def search_restaurants(
    query: str | None = None,
    cuisine: str | None = None,
    max_budget: Decimal | None = None,
    db: Session = Depends(get_db),
) -> dict:
    return {"restaurants": restaurant_service.search_restaurants(db, query, cuisine, max_budget)}


@router.get("/restaurants/{restaurant_id}")
def get_restaurant(restaurant_id: str, db: Session = Depends(get_db)) -> dict:
    return {"restaurant": restaurant_service.get_public_restaurant(db, restaurant_id)}


@router.get("/restaurants/{restaurant_id}/menu")
def get_menu(restaurant_id: str, db: Session = Depends(get_db)) -> dict:
    return restaurant_service.get_menu(db, restaurant_id, public_only=True)


@router.post("/orders")
def create_order(payload: CreateOrderInput, db: Session = Depends(get_db)) -> dict:
    return {"order": order_service.create_order(db, payload)}


@router.get("/orders/{order_id}")
def get_order_status(order_id: str, db: Session = Depends(get_db)) -> dict:
    return {"order": order_service.get_order_status(db, order_id)}


@router.post("/orders/{order_id}/cancel")
def cancel_order(order_id: str, payload: CancelOrderInput, db: Session = Depends(get_db)) -> dict:
    return {"order": order_service.cancel_order(db, order_id, payload.reason)}

