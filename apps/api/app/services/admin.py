import re

from fastapi import HTTPException, status
from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.models import McpCallLog, MenuItem, Order, OrderItem, Restaurant, User
from app.schemas import CreateUserInput, RestaurantInput, RestaurantOnboardingInput, UpdateUserInput
from app.security import hash_password
from app.services.formatters import order_out, restaurant_out, user_out


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "restaurant"


def unique_slug(db: Session, name: str, preferred: str | None = None) -> str:
    base = slugify(preferred or name)
    slug = base
    index = 2
    while db.scalar(select(Restaurant).where(Restaurant.slug == slug)):
        slug = f"{base}-{index}"
        index += 1
    return slug


def list_restaurants(db: Session) -> list[dict]:
    restaurants = db.scalars(select(Restaurant).order_by(Restaurant.created_at.desc())).all()
    return [restaurant_out(item) for item in restaurants]


def create_restaurant(db: Session, payload: RestaurantInput) -> dict:
    restaurant = Restaurant(
        name=payload.name,
        slug=unique_slug(db, payload.name, payload.slug),
        description=payload.description,
        location_text=payload.location_text,
        cuisine_tags=payload.cuisine_tags,
        service_modes=payload.service_modes,
        status=payload.status,
        mcp_visible=payload.mcp_visible,
        pickup_instructions=payload.pickup_instructions,
    )
    db.add(restaurant)
    db.commit()
    db.refresh(restaurant)
    return restaurant_out(restaurant)


def create_restaurant_onboarding(db: Session, payload: RestaurantOnboardingInput) -> dict:
    phone = payload.account.phone.strip()
    email = payload.account.email.strip() if payload.account.email else None
    if db.scalar(select(User).where(User.phone == phone)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="PHONE_EXISTS")
    if email and db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="EMAIL_EXISTS")

    restaurant = Restaurant(
        name=payload.restaurant.name,
        slug=unique_slug(db, payload.restaurant.name, payload.restaurant.slug),
        description=payload.restaurant.description,
        location_text=payload.restaurant.location_text,
        cuisine_tags=payload.restaurant.cuisine_tags,
        service_modes=payload.restaurant.service_modes,
        status=payload.restaurant.status,
        mcp_visible=payload.restaurant.mcp_visible,
        pickup_instructions=payload.restaurant.pickup_instructions,
    )
    db.add(restaurant)
    db.flush()

    user = User(
        phone=phone,
        email=email,
        password_hash=hash_password(payload.account.password),
        role="restaurant",
        restaurant_id=restaurant.id,
        is_active=payload.account.is_active,
    )
    db.add(user)
    db.commit()
    db.refresh(restaurant)
    db.refresh(user)
    return {"restaurant": restaurant_out(restaurant), "user": user_out(user)}


def update_restaurant(db: Session, restaurant_id: str, payload: RestaurantInput) -> dict:
    restaurant = db.get(Restaurant, restaurant_id)
    if not restaurant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="RESTAURANT_NOT_FOUND")
    restaurant.name = payload.name
    restaurant.description = payload.description
    restaurant.location_text = payload.location_text
    restaurant.cuisine_tags = payload.cuisine_tags
    restaurant.service_modes = payload.service_modes
    restaurant.status = payload.status
    restaurant.mcp_visible = payload.mcp_visible
    restaurant.pickup_instructions = payload.pickup_instructions
    db.commit()
    db.refresh(restaurant)
    return restaurant_out(restaurant)


def update_restaurant_and_account(
    db: Session,
    restaurant_id: str,
    restaurant_payload: RestaurantInput,
    account_payload: UpdateUserInput,
) -> dict:
    restaurant = get_restaurant_with_accounts(db, restaurant_id)
    account = primary_account(restaurant)
    phone = account_payload.phone.strip() if account_payload.phone else None
    email = None
    if account_payload.email is not None:
        email = account_payload.email.strip() or None

    if account:
        if phone:
            existing = db.scalar(select(User).where(User.phone == phone, User.id != account.id))
            if existing:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="PHONE_EXISTS")
        if email:
            existing = db.scalar(select(User).where(User.email == email, User.id != account.id))
            if existing:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="EMAIL_EXISTS")
    else:
        if not phone:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="PHONE_REQUIRED")
        if not account_payload.password:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ACCOUNT_PASSWORD_REQUIRED")
        if db.scalar(select(User).where(User.phone == phone)):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="PHONE_EXISTS")
        if email and db.scalar(select(User).where(User.email == email)):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="EMAIL_EXISTS")

    restaurant.name = restaurant_payload.name
    restaurant.description = restaurant_payload.description
    restaurant.location_text = restaurant_payload.location_text
    restaurant.cuisine_tags = restaurant_payload.cuisine_tags
    restaurant.service_modes = restaurant_payload.service_modes
    restaurant.status = restaurant_payload.status
    restaurant.mcp_visible = restaurant_payload.mcp_visible
    restaurant.pickup_instructions = restaurant_payload.pickup_instructions

    if account:
        if phone:
            account.phone = phone
        if account_payload.email is not None:
            account.email = email
        if account_payload.password:
            account.password_hash = hash_password(account_payload.password)
        if account_payload.is_active is not None:
            account.is_active = account_payload.is_active
        account.role = "restaurant"
        account.restaurant_id = restaurant.id
    else:
        db.add(
            User(
                phone=phone,
                email=email,
                password_hash=hash_password(account_payload.password or ""),
                role="restaurant",
                restaurant_id=restaurant.id,
                is_active=account_payload.is_active if account_payload.is_active is not None else True,
            )
        )

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="ACCOUNT_IDENTIFIER_EXISTS") from exc

    db.refresh(restaurant)
    return restaurant_out(restaurant)


def list_users(db: Session) -> list[dict]:
    users = db.scalars(select(User).where(User.role == "restaurant").order_by(User.created_at.desc())).all()
    return [user_out(user) for user in users]


def create_user(db: Session, payload: CreateUserInput) -> dict:
    if not payload.restaurant_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="RESTAURANT_REQUIRED")
    if payload.restaurant_id and not db.get(Restaurant, payload.restaurant_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="RESTAURANT_NOT_FOUND")
    phone = payload.phone.strip()
    email = payload.email.strip() if payload.email else None
    if db.scalar(select(User).where(User.phone == phone)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="PHONE_EXISTS")
    if email and db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="EMAIL_EXISTS")
    user = User(
        phone=phone,
        email=email,
        password_hash=hash_password(payload.password),
        role="restaurant",
        restaurant_id=payload.restaurant_id,
        is_active=payload.is_active,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user_out(user)


def update_user(db: Session, user_id: str, payload: UpdateUserInput) -> dict:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="USER_NOT_FOUND")
    restaurant_id = payload.restaurant_id if payload.restaurant_id is not None else user.restaurant_id
    if not restaurant_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="RESTAURANT_REQUIRED")
    if restaurant_id and not db.get(Restaurant, restaurant_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="RESTAURANT_NOT_FOUND")
    if payload.phone:
        phone = payload.phone.strip()
        existing = db.scalar(select(User).where(User.phone == phone, User.id != user_id))
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="PHONE_EXISTS")
        user.phone = phone
    if payload.email is not None:
        email = payload.email.strip() or None
        existing = db.scalar(select(User).where(User.email == email, User.id != user_id)) if email else None
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="EMAIL_EXISTS")
        user.email = email
    if payload.password:
        user.password_hash = hash_password(payload.password)
    if payload.is_active is not None:
        user.is_active = payload.is_active
    user.role = "restaurant"
    user.restaurant_id = restaurant_id
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="ACCOUNT_IDENTIFIER_EXISTS") from exc
    db.refresh(user)
    return user_out(user)


def get_restaurant_with_accounts(db: Session, restaurant_id: str) -> Restaurant:
    restaurant = db.scalar(
        select(Restaurant).options(selectinload(Restaurant.users)).where(Restaurant.id == restaurant_id)
    )
    if not restaurant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="RESTAURANT_NOT_FOUND")
    return restaurant


def primary_account(restaurant: Restaurant) -> User | None:
    restaurant_users = [user for user in restaurant.users if user.role == "restaurant"]
    restaurant_users.sort(key=lambda user: user.created_at)
    return restaurant_users[0] if restaurant_users else None


def list_all_orders(db: Session) -> list[dict]:
    orders = db.scalars(select(Order).options(selectinload(Order.items)).order_by(Order.created_at.desc())).all()
    return [order_out(order) for order in orders]


def list_mcp_logs(db: Session, limit: int = 100) -> list[dict]:
    logs = db.scalars(select(McpCallLog).order_by(McpCallLog.created_at.desc()).limit(limit)).all()
    return [
        {
            "id": log.id,
            "tool_name": log.tool_name,
            "restaurant_id": log.restaurant_id,
            "request_json": log.request_json,
            "response_summary": log.response_summary,
            "status": log.status,
            "error_message": log.error_message,
            "latency_ms": log.latency_ms,
            "created_at": log.created_at.isoformat(),
        }
        for log in logs
    ]


def hard_delete_restaurant(db: Session, restaurant_id: str, confirmation_name: str) -> dict:
    restaurant = db.get(Restaurant, restaurant_id)
    if not restaurant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="RESTAURANT_NOT_FOUND")
    if confirmation_name.strip() != restaurant.name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="RESTAURANT_NAME_CONFIRMATION_MISMATCH",
        )

    order_ids = db.scalars(select(Order.id).where(Order.restaurant_id == restaurant_id)).all()
    try:
        db.execute(update(McpCallLog).where(McpCallLog.restaurant_id == restaurant_id).values(restaurant_id=None))
        if order_ids:
            db.execute(delete(OrderItem).where(OrderItem.order_id.in_(order_ids)))
        db.execute(delete(Order).where(Order.restaurant_id == restaurant_id))
        db.execute(delete(MenuItem).where(MenuItem.restaurant_id == restaurant_id))
        db.execute(delete(User).where(User.restaurant_id == restaurant_id))
        db.delete(restaurant)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="RESTAURANT_DELETE_BLOCKED") from exc
    return {"ok": True}
