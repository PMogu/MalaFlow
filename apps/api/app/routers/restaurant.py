from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_restaurant_user
from app.models import User
from app.schemas import AcceptOrderInput, MenuItemInput, RejectOrderInput, RestaurantInput
from app.services import orders as order_service
from app.services import restaurants as restaurant_service
from app.services.formatters import restaurant_out

router = APIRouter(prefix="/api/restaurant", tags=["restaurant"])


def owned_restaurant_id(user: User) -> str:
    if not user.restaurant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="RESTAURANT_NOT_BOUND")
    return user.restaurant_id


@router.get("/me")
def get_restaurant(user: User = Depends(require_restaurant_user), db: Session = Depends(get_db)) -> dict:
    restaurant_id = owned_restaurant_id(user)
    restaurant = restaurant_service.get_restaurant_owned(db, restaurant_id)
    return {"restaurant": restaurant_out(restaurant)}


@router.patch("/me")
def update_restaurant(
    payload: RestaurantInput,
    user: User = Depends(require_restaurant_user),
    db: Session = Depends(get_db),
) -> dict:
    return {"restaurant": restaurant_service.update_owned_restaurant(db, owned_restaurant_id(user), payload)}


@router.get("/menu")
def list_menu(user: User = Depends(require_restaurant_user), db: Session = Depends(get_db)) -> dict:
    return {"menu_items": restaurant_service.list_menu(db, owned_restaurant_id(user))}


@router.post("/menu")
def create_menu_item(
    payload: MenuItemInput,
    user: User = Depends(require_restaurant_user),
    db: Session = Depends(get_db),
) -> dict:
    return {"menu_item": restaurant_service.create_menu_item(db, owned_restaurant_id(user), payload)}


@router.patch("/menu/{item_id}")
def update_menu_item(
    item_id: str,
    payload: MenuItemInput,
    user: User = Depends(require_restaurant_user),
    db: Session = Depends(get_db),
) -> dict:
    return {"menu_item": restaurant_service.update_menu_item(db, owned_restaurant_id(user), item_id, payload)}


@router.delete("/menu/{item_id}")
def delete_menu_item(
    item_id: str,
    user: User = Depends(require_restaurant_user),
    db: Session = Depends(get_db),
) -> dict:
    return restaurant_service.delete_menu_item(db, owned_restaurant_id(user), item_id)


@router.get("/orders")
def list_orders(user: User = Depends(require_restaurant_user), db: Session = Depends(get_db)) -> dict:
    return {"orders": order_service.list_restaurant_orders(db, owned_restaurant_id(user))}


@router.patch("/orders/{order_id}/accept")
def accept_order(
    order_id: str,
    payload: AcceptOrderInput,
    user: User = Depends(require_restaurant_user),
    db: Session = Depends(get_db),
) -> dict:
    return {
        "order": order_service.accept_order(
            db, order_id, owned_restaurant_id(user), payload.order_number
        )
    }


@router.patch("/orders/{order_id}/reject")
def reject_order(
    order_id: str,
    payload: RejectOrderInput,
    user: User = Depends(require_restaurant_user),
    db: Session = Depends(get_db),
) -> dict:
    return {"order": order_service.reject_order(db, order_id, owned_restaurant_id(user), payload.reason)}


@router.get("/mcp-status")
def mcp_status(user: User = Depends(require_restaurant_user), db: Session = Depends(get_db)) -> dict:
    restaurant = restaurant_service.get_restaurant_owned(db, owned_restaurant_id(user))
    return {
        "restaurant_id": restaurant.id,
        "mcp_visible": restaurant.mcp_visible,
        "status": restaurant.status,
        "tools": [
            "search_restaurants",
            "get_restaurant_detail",
            "get_menu",
            "create_order",
            "create_order_and_wait",
            "get_order_status",
            "wait_for_order_result",
            "cancel_order",
        ],
    }
