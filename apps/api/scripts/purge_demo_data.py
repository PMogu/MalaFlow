from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))

from sqlalchemy import delete, select

from app.database import SessionLocal
from app.models import McpCallLog, MenuItem, Order, OrderItem, Restaurant, User


DEMO_EMAILS = {"admin@pilot.test", "restaurant@pilot.test"}
DEMO_SLUGS = {"jinchuan-hui"}
DEMO_NAMES = {"锦川汇"}


def main() -> None:
    db = SessionLocal()
    try:
        restaurants = db.scalars(
            select(Restaurant).where(Restaurant.slug.in_(DEMO_SLUGS) | Restaurant.name.in_(DEMO_NAMES))
        ).all()
        restaurant_ids = [restaurant.id for restaurant in restaurants]
        order_ids = []
        if restaurant_ids:
            order_ids = db.scalars(select(Order.id).where(Order.restaurant_id.in_(restaurant_ids))).all()
            if order_ids:
                db.execute(delete(OrderItem).where(OrderItem.order_id.in_(order_ids)))
                db.execute(delete(Order).where(Order.id.in_(order_ids)))
            db.execute(delete(McpCallLog).where(McpCallLog.restaurant_id.in_(restaurant_ids)))
            db.execute(delete(MenuItem).where(MenuItem.restaurant_id.in_(restaurant_ids)))
            db.execute(delete(User).where(User.restaurant_id.in_(restaurant_ids)))
            db.execute(delete(Restaurant).where(Restaurant.id.in_(restaurant_ids)))
        db.execute(delete(User).where(User.email.in_(DEMO_EMAILS)))
        db.commit()
        print({"purged_restaurants": len(restaurant_ids), "purged_orders": len(order_ids)})
    finally:
        db.close()


if __name__ == "__main__":
    main()
