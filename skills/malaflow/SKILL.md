---
name: malaflow
description: Use when a user asks to find restaurants, recommend dishes, place pickup orders, or check order status near Unimelb through MalaFlow. This skill requires using MalaFlow MCP tools only and never web search for ordering results.
version: 0.2.0
---

# MalaFlow Ordering

Skill version: 0.2.0

Use this skill for Unimelb-area food ordering requests, including restaurant search, dish recommendations, hot or spicy food, pickup orders, cancellation, and order status checks.

MalaFlow MCP server URL:

```text
https://api.malaflow.com/mcp/
```

The server requires a MalaFlow Access Code from the pilot administrator.

## Default Behavior

- Only use MalaFlow MCP tools for restaurant, menu, order, and status information.
- Do not browse the web or use general restaurant knowledge as a fallback.
- Do not invent restaurants, menus, prices, availability, pickup numbers, or order status.
- If MalaFlow MCP tools are unavailable or not connected, tell the user you cannot access MalaFlow yet and ask them to connect the MalaFlow MCP server.

## Ordering Flow

1. Call `search_restaurants` to find available MalaFlow pilot restaurants.
2. Call `get_menu` before recommending exact dishes or preparing an order.
3. Present the restaurant, location, dish, price, and pickup notes when available.
4. Ask the user to confirm before calling `create_order`.
5. After explicit confirmation, call `create_order` with database menu item IDs and quantities.
6. Keep the returned `order_id` in the conversation.
7. Immediately call `wait_for_order_result` after `create_order`.
8. `wait_for_order_result` waits up to 5 minutes, polling every 10 seconds, until the restaurant accepts with a pickup number, rejects, or the order is cancelled.
9. If `wait_for_order_result` returns `accepted`, tell the user the pickup number.
10. If it returns `rejected` or `cancelled`, tell the user plainly.
11. If `wait_for_order_result` is unavailable, fallback to calling `get_order_status` every 10 seconds for up to 5 minutes.
12. If the user asks to cancel before acceptance, call `cancel_order` only for a submitted order.

## Failure Handling

- If `search_restaurants` returns no restaurants, say the MalaFlow pilot network currently has no available restaurants.
- If menus do not contain the requested dish or a close match, say MalaFlow does not currently have that item available.
- If `create_order` fails, say the order was not submitted and summarize the tool error in plain language.
- If `get_order_status` fails, say you cannot retrieve the current order status through MalaFlow.
- If the restaurant does not assign a pickup number within 5 minutes, say the order was rejected because no pickup number was assigned in time.

## User-Facing Language

- Say "MalaFlow" or "the MalaFlow pilot network".
- Avoid technical MCP wording unless the user asks about setup or configuration.
- Keep the user in control: recommend, ask for confirmation, then order.
