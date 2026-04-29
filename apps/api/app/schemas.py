from decimal import Decimal
import re

from pydantic import BaseModel, ConfigDict, Field, field_validator


PHONE_PATTERN = re.compile(r"^\+?[0-9][0-9\s().-]{5,24}$")


def clean_phone(value: str) -> str:
    cleaned = value.strip()
    if not PHONE_PATTERN.match(cleaned):
        raise ValueError("PHONE_INVALID")
    return cleaned


class LoginInput(BaseModel):
    phone: str = Field(min_length=6)
    password: str

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        return clean_phone(value)


class UserOut(BaseModel):
    id: str
    phone: str
    email: str | None = None
    role: str = "restaurant"
    restaurant_id: str | None = None
    is_active: bool


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class RestaurantInput(BaseModel):
    name: str = Field(min_length=1)
    slug: str | None = None
    description: str | None = None
    location_text: str | None = None
    cuisine_tags: list[str] = Field(default_factory=list)
    service_modes: list[str] = Field(default_factory=lambda: ["pickup"])
    status: str = "open"
    mcp_visible: bool = True
    pickup_instructions: str | None = None


class RestaurantOut(RestaurantInput):
    id: str
    model_config = ConfigDict(from_attributes=True)


class MenuItemInput(BaseModel):
    name: str = Field(min_length=1)
    description: str | None = None
    price: Decimal = Field(gt=0)
    currency: str = "AUD"
    category: str | None = None
    tags: list[str] = Field(default_factory=list)
    available: bool = True


class MenuItemOut(MenuItemInput):
    id: str
    restaurant_id: str
    archived: bool = False
    model_config = ConfigDict(from_attributes=True)


class CreateUserInput(BaseModel):
    phone: str = Field(min_length=6)
    email: str | None = None
    password: str = Field(min_length=6)
    restaurant_id: str | None = None
    is_active: bool = True

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        return clean_phone(value)


class UpdateUserInput(BaseModel):
    phone: str | None = Field(default=None, min_length=6)
    email: str | None = None
    password: str | None = Field(default=None, min_length=6)
    restaurant_id: str | None = None
    is_active: bool | None = None

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str | None) -> str | None:
        return clean_phone(value) if value is not None else None


class RestaurantAccountInput(BaseModel):
    phone: str = Field(min_length=6)
    email: str | None = None
    password: str = Field(min_length=6)
    is_active: bool = True

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        return clean_phone(value)


class RestaurantOnboardingInput(BaseModel):
    restaurant: RestaurantInput
    account: RestaurantAccountInput


class OrderItemInput(BaseModel):
    menu_item_id: str
    quantity: int = Field(gt=0)
    notes: str | None = None


class CreateOrderInput(BaseModel):
    restaurant_id: str
    items: list[OrderItemInput] = Field(min_length=1)
    customer_name: str | None = "Guest"
    customer_contact: str | None = None
    fulfillment_type: str = "pickup"
    notes: str | None = None


class OrderItemOut(BaseModel):
    id: str
    menu_item_id: str
    name_snapshot: str
    price_snapshot: Decimal
    quantity: int
    notes: str | None = None
    model_config = ConfigDict(from_attributes=True)


class OrderOut(BaseModel):
    id: str
    restaurant_id: str
    source: str
    status: str
    order_number: str | None = None
    customer_name: str | None = None
    customer_contact: str | None = None
    fulfillment_type: str
    notes: str | None = None
    reject_reason: str | None = None
    cancel_reason: str | None = None
    total_price: Decimal
    items: list[OrderItemOut] = Field(default_factory=list)
    status_message: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class AcceptOrderInput(BaseModel):
    order_number: str = Field(min_length=1)


class RejectOrderInput(BaseModel):
    reason: str | None = None


class CancelOrderInput(BaseModel):
    reason: str | None = None
