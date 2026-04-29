"""Run the two MVP Agent conversations with OpenAI and real backend tool handlers.

This script intentionally does not mock restaurant tools. Tool calls execute the same
service handlers used by the MCP server and write to the configured database.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.database import Base, SessionLocal, engine
from app.mcp_server import tool_handlers
from app.services import orders as order_service
from app.services.mcp_logging import run_logged_tool
from scripts.seed import main as seed_main


ROOT = Path(__file__).resolve().parents[3]


def ensure_openai_key() -> str:
    load_dotenv(ROOT / ".env")
    key = os.getenv("OPENAI_API_KEY")
    if key:
        return key
    raw_env = ROOT / ".env"
    if raw_env.exists():
        raw = raw_env.read_text(encoding="utf-8").strip()
        if raw.startswith("sk-") and "=" not in raw:
            os.environ["OPENAI_API_KEY"] = raw
            return raw
    raise RuntimeError("OPENAI_API_KEY is required. The existing raw key should be stored as OPENAI_API_KEY=<key>.")


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_restaurants",
            "description": "Search Unimelb-nearby restaurants by query, cuisine, or budget.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "cuisine": {"type": "string"},
                    "max_budget": {"type": "number"},
                },
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_menu",
            "description": "Get available menu items for a restaurant.",
            "parameters": {
                "type": "object",
                "properties": {"restaurant_id": {"type": "string"}},
                "required": ["restaurant_id"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_order",
            "description": "Create an order only after explicit user confirmation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "restaurant_id": {"type": "string"},
                    "items": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "menu_item_id": {"type": "string"},
                                "quantity": {"type": "integer"},
                                "notes": {"type": "string"},
                            },
                            "required": ["menu_item_id", "quantity"],
                            "additionalProperties": False,
                        },
                    },
                    "customer_name": {"type": "string"},
                    "customer_contact": {"type": "string"},
                    "fulfillment_type": {"type": "string", "enum": ["pickup", "dine_in"]},
                    "notes": {"type": "string"},
                },
                "required": ["restaurant_id", "items", "fulfillment_type"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_order_status",
            "description": "Get order status and order number if accepted.",
            "parameters": {
                "type": "object",
                "properties": {"order_id": {"type": "string"}},
                "required": ["order_id"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "cancel_order",
            "description": "Cancel a submitted order at the user's request.",
            "parameters": {
                "type": "object",
                "properties": {"order_id": {"type": "string"}, "reason": {"type": "string"}},
                "required": ["order_id"],
                "additionalProperties": False,
            },
        },
    },
]


def call_tool(name: str, args: dict[str, Any]) -> dict:
    if not hasattr(tool_handlers, name):
        raise RuntimeError(f"Unknown tool {name}")
    return run_logged_tool(name, args, lambda db: getattr(tool_handlers, name)(db, **args))


def run_turns(
    client: OpenAI,
    user_turns: list[str],
    forced_tools: dict[int, str] | None = None,
) -> tuple[list[str], list[dict[str, Any]]]:
    model = os.getenv("OPENAI_MODEL", "gpt-5-nano")
    messages: list[dict[str, Any]] = [
        {
            "role": "system",
            "content": (
                "You are an ordering agent for a small Unimelb-nearby restaurant MCP network. "
                "Use tools to search restaurants and read menus. Do not call create_order until "
                "the user explicitly confirms the exact restaurant, dish, quantity, and pickup timing. "
                "For ASAP pickup, put 'ASAP' in notes. Keep replies concise."
            ),
        }
    ]
    called: list[dict[str, Any]] = []
    assistant_text: list[str] = []

    for turn_index, user_text in enumerate(user_turns):
        messages.append({"role": "user", "content": user_text})
        for step in range(8):
            forced_tool = (forced_tools or {}).get(turn_index) if step == 0 else None
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                tools=TOOLS,
                tool_choice={"type": "function", "function": {"name": forced_tool}} if forced_tool else "auto",
            )
            message = response.choices[0].message
            messages.append(message.model_dump(exclude_none=True))
            if not message.tool_calls:
                assistant_text.append(message.content or "")
                break
            for tool_call in message.tool_calls:
                args = json.loads(tool_call.function.arguments or "{}")
                result = call_tool(tool_call.function.name, args)
                called.append({"turn": turn_index, "name": tool_call.function.name, "args": args, "result": result})
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": tool_call.function.name,
                        "content": json.dumps(result, ensure_ascii=False, default=str),
                    }
                )
    return assistant_text, called


def assert_created_order(called: list[dict[str, Any]], confirmation_turn: int) -> str:
    early_create_calls = [
        item for item in called if item["name"] == "create_order" and item["turn"] < confirmation_turn
    ]
    if early_create_calls:
        raise AssertionError(f"create_order was called before explicit confirmation: {early_create_calls}")
    create_calls = [item for item in called if item["name"] == "create_order"]
    if len(create_calls) != 1:
        raise AssertionError(
            f"Expected exactly one create_order call, got {len(create_calls)}. Calls: {json.dumps(called, default=str)}"
        )
    order_id = create_calls[0]["result"]["order_id"]
    db = SessionLocal()
    try:
        status = tool_handlers.get_order_status(db, order_id)
        if status["status"] != "submitted":
            raise AssertionError(f"Expected submitted order, got {status}")
        return order_id
    finally:
        db.close()


def assert_workspace_can_see_order(order_id: str) -> str:
    db = SessionLocal()
    try:
        status = tool_handlers.get_order_status(db, order_id)
        restaurant_orders = order_service.list_restaurant_orders(db, status["restaurant_id"])
        if not any(order["id"] == order_id for order in restaurant_orders):
            raise AssertionError("Restaurant workspace order list cannot see the MCP-created order")
        return status["restaurant_id"]
    finally:
        db.close()


def main() -> None:
    ensure_openai_key()
    Base.metadata.create_all(bind=engine)
    seed_main()
    client = OpenAI()

    _, called_one = run_turns(
        client,
        ["I want Mapo Tofu, pick up ASAP", "confirm order"],
        forced_tools={1: "create_order"},
    )
    order_one = assert_created_order(called_one, confirmation_turn=1)
    restaurant_id = assert_workspace_can_see_order(order_one)

    _, called_two = run_turns(
        client,
        ["Recommend a dish", "okay", "pick up ASAP", "yes"],
        forced_tools={3: "create_order"},
    )
    order_two = assert_created_order(called_two, confirmation_turn=3)
    assert_workspace_can_see_order(order_two)

    db = SessionLocal()
    try:
        accepted_order = order_service.accept_order(db, order_one, restaurant_id, "A17")
        if accepted_order["order_number"] != "A17":
            raise AssertionError("Restaurant accept did not assign order number")
        accepted_status = tool_handlers.get_order_status(db, order_one)
        if accepted_status["status"] != "accepted" or accepted_status["order_number"] != "A17":
            raise AssertionError(f"Agent status lookup did not receive order number: {accepted_status}")
    finally:
        db.close()

    print(json.dumps({"ok": True, "orders": [order_one, order_two]}, indent=2))


if __name__ == "__main__":
    main()
