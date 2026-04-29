from decimal import Decimal
import re

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import MenuItem, OrderItem, Restaurant
from app.schemas import MenuItemInput, RestaurantInput
from app.services.admin import unique_slug
from app.services.formatters import menu_item_out, restaurant_out


def _tokens(value: str | None) -> list[str]:
    if not value:
        return []
    return [token for token in re.split(r"[^a-z0-9\u4e00-\u9fff]+", value.lower()) if token]


def _item_score(item: MenuItem, query_tokens: list[str], budget: Decimal | None) -> tuple[int, list[str]]:
    fields = [item.name, item.description or "", item.category or "", *(item.tags or [])]
    text = " ".join(fields).lower()
    score = 0
    reasons: list[str] = []
    if budget is not None and item.price <= budget:
        score += 2
        reasons.append(f"under AUD {budget}")
    for token in query_tokens:
        if token and token in text:
            score += 3 if token in item.name.lower() else 1
            if len(reasons) < 3:
                reasons.append(f"matches {token}")
    return score, reasons


def search_restaurants(
    db: Session,
    query: str | None = None,
    cuisine: str | None = None,
    max_budget: Decimal | None = None,
) -> list[dict]:
    query_tokens = _tokens(query)
    cuisine_tokens = _tokens(cuisine)
    vague_queries = {"recommend", "dish", "food", "hungry", "lunch", "dinner", "pickup", "asap"}
    restaurants = db.scalars(
        select(Restaurant)
        .where(Restaurant.mcp_visible.is_(True), Restaurant.status == "open")
        .order_by(Restaurant.created_at.asc())
    ).all()
    results: list[dict] = []
    for restaurant in restaurants:
        available_items = [item for item in restaurant.menu_items if item.available and not item.archived]
        if not available_items:
            continue
        restaurant_text = " ".join(
            [restaurant.name, restaurant.description or "", restaurant.location_text or "", *(restaurant.cuisine_tags or [])]
        ).lower()
        if cuisine_tokens and not any(token in restaurant_text for token in cuisine_tokens):
            continue
        if max_budget is not None and not any(item.price <= max_budget for item in available_items):
            continue

        score = 1
        match_reasons: list[str] = ["campus pilot restaurant accepting MCP orders"]
        for token in query_tokens:
            if token and token in restaurant_text:
                score += 2
                if len(match_reasons) < 5:
                    match_reasons.append(f"restaurant matches {token}")
        for token in cuisine_tokens:
            if token in restaurant_text:
                score += 2
                match_reasons.append(f"cuisine matches {token}")

        ranked_items: list[tuple[int, MenuItem, list[str]]] = []
        for item in available_items:
            item_score, reasons = _item_score(item, query_tokens, max_budget)
            ranked_items.append((item_score, item, reasons))
            score += item_score

        meaningful_tokens = [token for token in query_tokens if token not in vague_queries]
        if meaningful_tokens and score <= 1:
            continue

        ranked_items.sort(key=lambda row: (row[0], -available_items.index(row[1])), reverse=True)
        recommended_items = [item for item_score, item, _ in ranked_items if item_score > 0][:3]
        if not recommended_items:
            recommended_items = available_items[:3]
        for _, _, reasons in ranked_items[:2]:
            for reason in reasons:
                if reason not in match_reasons and len(match_reasons) < 5:
                    match_reasons.append(reason)

        payload = restaurant_out(restaurant)
        payload["match_score"] = score
        payload["match_reasons"] = match_reasons
        payload["recommended_items"] = [menu_item_out(item) for item in recommended_items]
        payload["menu_preview"] = [menu_item_out(item) for item in recommended_items[:4]]
        results.append(payload)
    results.sort(key=lambda item: item["match_score"], reverse=True)
    return results


def get_public_restaurant(db: Session, restaurant_id: str) -> dict:
    restaurant = db.get(Restaurant, restaurant_id)
    if not restaurant or not restaurant.mcp_visible:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="RESTAURANT_NOT_FOUND")
    return restaurant_out(restaurant)


def get_menu(db: Session, restaurant_id: str, public_only: bool = True) -> dict:
    restaurant = db.get(Restaurant, restaurant_id)
    if not restaurant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="RESTAURANT_NOT_FOUND")
    if public_only and not restaurant.mcp_visible:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="RESTAURANT_NOT_FOUND")
    items = [
        item
        for item in restaurant.menu_items
        if not item.archived and ((item.available and public_only) or not public_only)
    ]
    items.sort(key=lambda item: ((item.category or ""), item.name))
    return {"restaurant": restaurant_out(restaurant), "menu_items": [menu_item_out(item) for item in items]}


def get_restaurant_owned(db: Session, restaurant_id: str) -> Restaurant:
    restaurant = db.get(Restaurant, restaurant_id)
    if not restaurant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="RESTAURANT_NOT_FOUND")
    return restaurant


def update_owned_restaurant(db: Session, restaurant_id: str, payload: RestaurantInput) -> dict:
    restaurant = get_restaurant_owned(db, restaurant_id)
    restaurant.name = payload.name
    restaurant.description = payload.description
    restaurant.location_text = payload.location_text
    restaurant.cuisine_tags = payload.cuisine_tags
    restaurant.service_modes = payload.service_modes
    restaurant.status = payload.status
    restaurant.mcp_visible = payload.mcp_visible
    restaurant.pickup_instructions = payload.pickup_instructions
    if not restaurant.slug:
        restaurant.slug = unique_slug(db, payload.name, payload.slug)
    db.commit()
    db.refresh(restaurant)
    return restaurant_out(restaurant)


def list_menu(db: Session, restaurant_id: str) -> list[dict]:
    items = db.scalars(
        select(MenuItem)
        .where(MenuItem.restaurant_id == restaurant_id, MenuItem.archived.is_(False))
        .order_by(MenuItem.category, MenuItem.name)
    ).all()
    return [menu_item_out(item) for item in items]


def create_menu_item(db: Session, restaurant_id: str, payload: MenuItemInput) -> dict:
    if not db.get(Restaurant, restaurant_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="RESTAURANT_NOT_FOUND")
    item = MenuItem(
        restaurant_id=restaurant_id,
        name=payload.name,
        description=payload.description,
        price=payload.price,
        currency=payload.currency,
        category=payload.category,
        tags=payload.tags,
        available=payload.available,
        archived=False,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return menu_item_out(item)


def update_menu_item(db: Session, restaurant_id: str, item_id: str, payload: MenuItemInput) -> dict:
    item = db.scalar(select(MenuItem).where(MenuItem.id == item_id, MenuItem.restaurant_id == restaurant_id))
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="MENU_ITEM_NOT_FOUND")
    item.name = payload.name
    item.description = payload.description
    item.price = payload.price
    item.currency = payload.currency
    item.category = payload.category
    item.tags = payload.tags
    item.available = payload.available
    db.commit()
    db.refresh(item)
    return menu_item_out(item)


def delete_menu_item(db: Session, restaurant_id: str, item_id: str) -> dict:
    item = db.scalar(select(MenuItem).where(MenuItem.id == item_id, MenuItem.restaurant_id == restaurant_id))
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="MENU_ITEM_NOT_FOUND")
    reference_count = db.scalar(select(func.count(OrderItem.id)).where(OrderItem.menu_item_id == item.id)) or 0
    if reference_count:
        item.available = False
        item.archived = True
        mode = "archived"
    else:
        db.delete(item)
        mode = "deleted"
    db.commit()
    return {"ok": True, "mode": mode}
