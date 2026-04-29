from app.models import MenuItem, Order, Restaurant, User


def iso(value) -> str | None:
    return value.isoformat() if value else None


def user_out(user: User) -> dict:
    return {
        "id": user.id,
        "phone": user.phone,
        "email": user.email,
        "role": user.role,
        "restaurant_id": user.restaurant_id,
        "is_active": user.is_active,
    }


def restaurant_out(restaurant: Restaurant) -> dict:
    return {
        "id": restaurant.id,
        "name": restaurant.name,
        "slug": restaurant.slug,
        "description": restaurant.description,
        "location_text": restaurant.location_text,
        "location_phrase": f"地点在 {restaurant.location_text}" if restaurant.location_text else None,
        "cuisine_tags": restaurant.cuisine_tags or [],
        "service_modes": restaurant.service_modes or [],
        "status": restaurant.status,
        "mcp_visible": restaurant.mcp_visible,
        "pickup_instructions": restaurant.pickup_instructions,
    }


def menu_item_out(item: MenuItem) -> dict:
    return {
        "id": item.id,
        "restaurant_id": item.restaurant_id,
        "name": item.name,
        "description": item.description,
        "price": str(item.price),
        "currency": item.currency,
        "category": item.category,
        "tags": item.tags or [],
        "available": item.available,
        "archived": item.archived,
    }


def order_status_message(order: Order) -> str:
    if order.status == "submitted":
        return "Order submitted. Waiting for restaurant staff to assign a pickup number."
    if order.status == "accepted":
        return f"Order accepted. Use pickup number {order.order_number} at the restaurant."
    if order.status == "cancelled":
        return "Order cancelled before the restaurant accepted it."
    if order.status == "rejected":
        return "Order rejected by the restaurant before acceptance."
    return f"Order status is {order.status}."


def order_out(order: Order) -> dict:
    return {
        "id": order.id,
        "restaurant_id": order.restaurant_id,
        "source": order.source,
        "status": order.status,
        "order_number": order.order_number,
        "customer_name": order.customer_name,
        "customer_contact": order.customer_contact,
        "fulfillment_type": order.fulfillment_type,
        "notes": order.notes,
        "reject_reason": order.reject_reason,
        "cancel_reason": order.cancel_reason,
        "total_price": str(order.total_price),
        "items": [
            {
                "id": item.id,
                "menu_item_id": item.menu_item_id,
                "name_snapshot": item.name_snapshot,
                "price_snapshot": str(item.price_snapshot),
                "quantity": item.quantity,
                "notes": item.notes,
            }
            for item in order.items
        ],
        "status_message": order_status_message(order),
        "created_at": iso(order.created_at),
        "updated_at": iso(order.updated_at),
    }
