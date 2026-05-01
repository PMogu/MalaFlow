"""Smoke test the deployed MCP endpoint using the configured bearer token.

This checks the MVP loop against a live API:

1. MCP searches restaurants.
2. MCP reads the menu.
3. MCP creates a submitted order.
4. Restaurant workspace API sees and accepts it with an order number.
5. MCP status lookup returns the accepted order number.
6. MCP can cancel a separate submitted order.
"""

from __future__ import annotations

import asyncio
import json
import os
from typing import Any

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


def tool_payload(result: Any) -> dict:
    if getattr(result, "isError", False):
        raise AssertionError(f"MCP tool returned error: {result}")
    for content in result.content:
        text = getattr(content, "text", None)
        if text:
            return json.loads(text)
    raise AssertionError(f"MCP tool returned no JSON text content: {result}")


async def main() -> None:
    base_url = os.getenv("API_BASE_URL", "https://api.malaflow.com").rstrip("/")
    token = os.environ["MCP_BEARER_TOKEN"]
    restaurant_phone = os.environ["SMOKE_RESTAURANT_PHONE"]
    restaurant_password = os.environ["SMOKE_RESTAURANT_PASSWORD"]
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient(headers=headers, timeout=30) as http_client, httpx.AsyncClient(
        timeout=30
    ) as rest_client:
        async with streamable_http_client(f"{base_url}/mcp/", http_client=http_client) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = await session.list_tools()
                names = [tool.name for tool in tools.tools]
                expected = {
                    "search_restaurants",
                    "get_restaurant_detail",
                    "get_menu",
                    "create_order",
                    "get_order_status",
                    "cancel_order",
                }
                missing = expected.difference(names)
                if missing:
                    raise AssertionError(f"MCP tools missing: {sorted(missing)}")

                search = tool_payload(await session.call_tool("search_restaurants", {"query": "Mapo"}))
                restaurants = search.get("restaurants", [])
                if not restaurants:
                    raise AssertionError(f"search_restaurants returned no restaurants: {search}")
                restaurant_id = restaurants[0]["id"]

                menu_payload = tool_payload(await session.call_tool("get_menu", {"restaurant_id": restaurant_id}))
                menu_items = menu_payload.get("menu_items", [])
                mapo = next((item for item in menu_items if "麻婆" in item["name"] or "Mapo" in item["description"]), None)
                if not mapo:
                    raise AssertionError(f"Mapo item missing from menu: {menu_payload}")

                created = tool_payload(
                    await session.call_tool(
                        "create_order",
                        {
                            "restaurant_id": restaurant_id,
                            "items": [{"menu_item_id": mapo["id"], "quantity": 1, "notes": "ASAP smoke"}],
                            "customer_name": "MCP Smoke",
                            "fulfillment_type": "pickup",
                            "notes": "ASAP smoke",
                        },
                    )
                )
                order_id = created["order_id"]
                if created["status"] != "submitted" or created.get("order_number") is not None:
                    raise AssertionError(f"Unexpected created order payload: {created}")

                login = await rest_client.post(
                    f"{base_url}/api/auth/login",
                    json={"phone": restaurant_phone, "password": restaurant_password},
                )
                login.raise_for_status()
                restaurant_token = login.json()["access_token"]
                workspace_headers = {"Authorization": f"Bearer {restaurant_token}"}

                orders = await rest_client.get(f"{base_url}/api/restaurant/orders", headers=workspace_headers)
                orders.raise_for_status()
                if not any(order["id"] == order_id for order in orders.json()["orders"]):
                    raise AssertionError("Restaurant workspace cannot see the MCP-created order")

                accept = await rest_client.patch(
                    f"{base_url}/api/restaurant/orders/{order_id}/accept",
                    headers=workspace_headers,
                    json={"order_number": "MCP-1"},
                )
                accept.raise_for_status()

                status = tool_payload(await session.call_tool("get_order_status", {"order_id": order_id}))
                if status["status"] != "accepted" or status["order_number"] != "MCP-1":
                    raise AssertionError(f"MCP status did not return accepted order number: {status}")

                cancellable = tool_payload(
                    await session.call_tool(
                        "create_order",
                        {
                            "restaurant_id": restaurant_id,
                            "items": [{"menu_item_id": mapo["id"], "quantity": 1}],
                            "customer_name": "MCP Cancel Smoke",
                            "fulfillment_type": "pickup",
                            "notes": "cancel smoke",
                        },
                    )
                )
                cancelled = tool_payload(
                    await session.call_tool(
                        "cancel_order",
                        {"order_id": cancellable["order_id"], "reason": "MCP smoke cancellation"},
                    )
                )
                if cancelled["status"] != "cancelled":
                    raise AssertionError(f"MCP cancel did not cancel submitted order: {cancelled}")

                print(
                    {
                        "ok": True,
                        "tools": names,
                        "accepted_order_id": order_id,
                        "accepted_order_number": status["order_number"],
                        "cancelled_order_id": cancellable["order_id"],
                    }
                )


if __name__ == "__main__":
    asyncio.run(main())
