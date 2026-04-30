import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, JSON, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:16]}"


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("user"))
    phone: Mapped[str] = mapped_column(String(40), unique=True, index=True, nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), unique=True, index=True, nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    restaurant_id: Mapped[str | None] = mapped_column(ForeignKey("restaurants.id"), nullable=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    restaurant: Mapped["Restaurant | None"] = relationship(back_populates="users")


class Restaurant(Base, TimestampMixin):
    __tablename__ = "restaurants"

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("restaurant"))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    location_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    cuisine_tags: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    service_modes: Mapped[list[str]] = mapped_column(JSON, default=lambda: ["pickup"], nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="open", index=True, nullable=False)
    mcp_visible: Mapped[bool] = mapped_column(Boolean, default=True, index=True, nullable=False)
    pickup_instructions: Mapped[str | None] = mapped_column(Text, nullable=True)

    users: Mapped[list[User]] = relationship(back_populates="restaurant")
    menu_items: Mapped[list["MenuItem"]] = relationship(back_populates="restaurant", cascade="all, delete-orphan")
    orders: Mapped[list["Order"]] = relationship(back_populates="restaurant")


class MenuItem(Base, TimestampMixin):
    __tablename__ = "menu_items"

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("item"))
    restaurant_id: Mapped[str] = mapped_column(ForeignKey("restaurants.id"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), default="AUD", nullable=False)
    category: Mapped[str | None] = mapped_column(String(120), nullable=True)
    tags: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    available: Mapped[bool] = mapped_column(Boolean, default=True, index=True, nullable=False)
    archived: Mapped[bool] = mapped_column(Boolean, default=False, index=True, nullable=False)

    restaurant: Mapped[Restaurant] = relationship(back_populates="menu_items")
    order_items: Mapped[list["OrderItem"]] = relationship(back_populates="menu_item")


class Order(Base, TimestampMixin):
    __tablename__ = "orders"

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("order"))
    restaurant_id: Mapped[str] = mapped_column(ForeignKey("restaurants.id"), index=True, nullable=False)
    source: Mapped[str] = mapped_column(String(32), default="mcp", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="submitted", index=True, nullable=False)
    order_number: Mapped[str | None] = mapped_column(String(80), nullable=True)
    customer_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    customer_contact: Mapped[str | None] = mapped_column(String(255), nullable=True)
    fulfillment_type: Mapped[str] = mapped_column(String(32), default="pickup", nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    reject_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    cancel_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    total_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)

    restaurant: Mapped[Restaurant] = relationship(back_populates="orders")
    items: Mapped[list["OrderItem"]] = relationship(back_populates="order", cascade="all, delete-orphan")


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("order_item"))
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id"), index=True, nullable=False)
    menu_item_id: Mapped[str] = mapped_column(ForeignKey("menu_items.id"), nullable=False)
    name_snapshot: Mapped[str] = mapped_column(String(255), nullable=False)
    price_snapshot: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    quantity: Mapped[int] = mapped_column(nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    order: Mapped[Order] = relationship(back_populates="items")
    menu_item: Mapped[MenuItem] = relationship(back_populates="order_items")


class McpCallLog(Base):
    __tablename__ = "mcp_call_logs"

    id: Mapped[str] = mapped_column(String(40), primary_key=True, default=lambda: new_id("mcp_log"))
    tool_name: Mapped[str] = mapped_column(String(120), index=True, nullable=False)
    restaurant_id: Mapped[str | None] = mapped_column(ForeignKey("restaurants.id"), nullable=True, index=True)
    request_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    response_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    latency_ms: Mapped[int] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class OAuthClient(Base, TimestampMixin):
    __tablename__ = "oauth_clients"

    id: Mapped[str] = mapped_column(String(80), primary_key=True, default=lambda: new_id("oauth_client"))
    client_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    redirect_uris: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    grant_types: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    response_types: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    scope: Mapped[str | None] = mapped_column(String(255), nullable=True)


class OAuthAuthorizationCode(Base):
    __tablename__ = "oauth_authorization_codes"

    code: Mapped[str] = mapped_column(String(160), primary_key=True)
    client_id: Mapped[str] = mapped_column(ForeignKey("oauth_clients.id"), index=True, nullable=False)
    redirect_uri: Mapped[str] = mapped_column(Text, nullable=False)
    code_challenge: Mapped[str] = mapped_column(String(160), nullable=False)
    code_challenge_method: Mapped[str] = mapped_column(String(16), default="S256", nullable=False)
    scope: Mapped[str | None] = mapped_column(String(255), nullable=True)
    state: Mapped[str | None] = mapped_column(String(255), nullable=True)
    resource: Mapped[str | None] = mapped_column(Text, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class OAuthRefreshToken(Base):
    __tablename__ = "oauth_refresh_tokens"

    token: Mapped[str] = mapped_column(String(160), primary_key=True)
    client_id: Mapped[str] = mapped_column(ForeignKey("oauth_clients.id"), index=True, nullable=False)
    scope: Mapped[str | None] = mapped_column(String(255), nullable=True)
    resource: Mapped[str | None] = mapped_column(Text, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
