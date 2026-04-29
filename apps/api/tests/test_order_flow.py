from decimal import Decimal

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import MenuItem, Restaurant, User
from app.schemas import CreateOrderInput, OrderItemInput, RestaurantAccountInput, RestaurantInput, RestaurantOnboardingInput
from app.security import hash_password
from app.services import admin, auth, orders, restaurants


@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    session = Session()
    restaurant = Restaurant(
        name="锦川汇",
        slug="jinchuan-hui",
        description="Sichuan near Unimelb",
        location_text="Swanston St, near Unimelb",
        cuisine_tags=["Sichuan"],
        service_modes=["pickup", "dine_in"],
        status="open",
        mcp_visible=True,
    )
    session.add(restaurant)
    session.flush()
    session.add(
        MenuItem(
            restaurant_id=restaurant.id,
            name="麻婆豆腐饭",
            description="Mapo tofu rice",
            price=Decimal("15.80"),
            category="Rice",
            tags=["tofu", "spicy"],
            available=True,
        )
    )
    session.commit()
    try:
        yield session
    finally:
        session.close()


def create_submitted_order(db):
    restaurant = db.query(Restaurant).first()
    item = db.query(MenuItem).first()
    return orders.create_order(
        db,
        CreateOrderInput(
            restaurant_id=restaurant.id,
            items=[OrderItemInput(menu_item_id=item.id, quantity=1)],
            fulfillment_type="pickup",
            notes="ASAP",
        ),
    )


def test_create_order_snapshots_database_price(db):
    order = create_submitted_order(db)
    assert order["status"] == "submitted"
    assert order["total_price"] == "15.80"
    assert order["items"][0]["name_snapshot"] == "麻婆豆腐饭"
    assert order["order_number"] is None


def test_accept_requires_order_number(db):
    order = create_submitted_order(db)
    with pytest.raises(HTTPException) as exc:
        orders.accept_order(db, order["id"], order["restaurant_id"], "")
    assert exc.value.detail == "ORDER_NUMBER_REQUIRED"

    accepted = orders.accept_order(db, order["id"], order["restaurant_id"], "A17")
    assert accepted["status"] == "accepted"
    assert accepted["order_number"] == "A17"


def test_cancel_and_reject_only_from_submitted(db):
    first = create_submitted_order(db)
    cancelled = orders.cancel_order(db, first["id"], "User changed mind")
    assert cancelled["status"] == "cancelled"

    second = create_submitted_order(db)
    rejected = orders.reject_order(db, second["id"], second["restaurant_id"], "Sold out")
    assert rejected["status"] == "rejected"

    third = create_submitted_order(db)
    accepted = orders.accept_order(db, third["id"], third["restaurant_id"], "B03")
    with pytest.raises(HTTPException) as cancel_exc:
        orders.cancel_order(db, accepted["id"])
    assert cancel_exc.value.detail == "INVALID_ORDER_STATE"
    with pytest.raises(HTTPException) as reject_exc:
        orders.reject_order(db, accepted["id"], accepted["restaurant_id"], "Too late")
    assert reject_exc.value.detail == "INVALID_ORDER_STATE"


def test_admin_onboarding_creates_restaurant_account_binding(db):
    created = admin.create_restaurant_onboarding(
        db,
        RestaurantOnboardingInput(
            restaurant=RestaurantInput(
                name="Uni Noodles",
                description="Quick pickup near campus",
                location_text="University Square",
                cuisine_tags=["Chinese"],
                service_modes=["pickup"],
                pickup_instructions="Quote the pickup number at the counter",
            ),
            account=RestaurantAccountInput(
                phone="+61400000001",
                email="uni-noodles@example.test",
                password="demo-pass",
            ),
        ),
    )

    assert created["restaurant"]["name"] == "Uni Noodles"
    assert created["restaurant"]["location_phrase"] == "地点在 University Square"
    assert created["user"]["role"] == "restaurant"
    assert created["user"]["phone"] == "+61400000001"
    assert created["user"]["restaurant_id"] == created["restaurant"]["id"]

    restaurant_count = db.query(Restaurant).count()
    with pytest.raises(HTTPException) as duplicate_exc:
        admin.create_restaurant_onboarding(
            db,
            RestaurantOnboardingInput(
                restaurant=RestaurantInput(name="Duplicate Noodles"),
                account=RestaurantAccountInput(phone="+61400000001", password="demo-pass"),
            ),
        )
    assert duplicate_exc.value.detail == "PHONE_EXISTS"
    assert db.query(Restaurant).count() == restaurant_count
    assert db.query(User).filter(User.phone == "+61400000001").count() == 1


def test_restaurant_login_rejects_legacy_admin_user(db):
    db.add(
        User(
            phone="+61400000999",
            email="legacy-admin@example.test",
            password_hash=hash_password("admin-pass"),
            role="admin",
            is_active=True,
        )
    )
    db.commit()

    with pytest.raises(HTTPException) as exc:
        auth.login(db, "+61400000999", "admin-pass")
    assert exc.value.detail == "RESTAURANT_LOGIN_ONLY"


def test_search_returns_experiment_recommendation_metadata(db):
    results = restaurants.search_restaurants(db, query="Mapo tofu pickup")
    assert results
    assert results[0]["match_reasons"]
    assert results[0]["location_phrase"] == "地点在 Swanston St, near Unimelb"
    assert results[0]["recommended_items"][0]["name"] == "麻婆豆腐饭"


def test_delete_menu_item_archives_when_order_snapshot_references_it(db):
    order = create_submitted_order(db)
    item_id = order["items"][0]["menu_item_id"]

    result = restaurants.delete_menu_item(db, order["restaurant_id"], item_id)

    assert result == {"ok": True, "mode": "archived"}
    item = db.get(MenuItem, item_id)
    assert item is not None
    assert item.archived is True
    assert item.available is False
    assert restaurants.list_menu(db, order["restaurant_id"]) == []


def test_phone_login_allows_optional_email(db):
    restaurant = db.query(Restaurant).first()
    db.add(
        User(
            phone="+61400000002",
            email=None,
            password_hash=hash_password("phone-pass"),
            role="restaurant",
            restaurant_id=restaurant.id,
            is_active=True,
        )
    )
    db.commit()

    logged_in = auth.login(db, "+61400000002", "phone-pass")

    assert logged_in["user"]["phone"] == "+61400000002"
    assert logged_in["user"]["email"] is None


def test_order_creation_survives_notification_failure(db, monkeypatch):
    def fail_notification(*_args, **_kwargs):
        raise RuntimeError("sms provider unavailable")

    monkeypatch.setattr(orders, "notify_new_order_sms", fail_notification)

    order = create_submitted_order(db)

    assert order["status"] == "submitted"
    assert db.query(MenuItem).count() == 1
