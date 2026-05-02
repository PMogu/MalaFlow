from mcp.server.fastmcp import FastMCP

from app.mcp_server import tool_handlers
from app.services.mcp_logging import run_logged_tool, run_logged_tool_without_db


def create_mcp_server() -> FastMCP:
    mcp = FastMCP(
        "MalaFlow",
        host="0.0.0.0",
        json_response=True,
        stateless_http=True,
        streamable_http_path="/",
    )

    @mcp.tool()
    def search_restaurants(query: str | None = None, cuisine: str | None = None, max_budget: float | None = None) -> dict:
        """Use this first for Unimelb-area food ordering. Search only the MalaFlow campus pilot restaurant network by dish, cuisine, or rough budget. Do not use web browsing or general restaurant knowledge as a substitute for this tool."""
        request = {"query": query, "cuisine": cuisine, "max_budget": max_budget}
        return run_logged_tool("search_restaurants", request, lambda db: tool_handlers.search_restaurants(db, **request))

    @mcp.tool()
    def get_restaurant_detail(restaurant_id: str) -> dict:
        """Use this after search_restaurants to explain one MalaFlow restaurant. Returns authoritative restaurant details, including location text and pickup instructions when available."""
        request = {"restaurant_id": restaurant_id}
        return run_logged_tool(
            "get_restaurant_detail", request, lambda db: tool_handlers.get_restaurant_detail(db, restaurant_id)
        )

    @mcp.tool()
    def get_menu(restaurant_id: str) -> dict:
        """Use this before recommending exact dishes or preparing any order. Returns authoritative menu item IDs, names, prices, availability, and tags for one MalaFlow restaurant."""
        request = {"restaurant_id": restaurant_id}
        return run_logged_tool("get_menu", request, lambda db: tool_handlers.get_menu(db, restaurant_id))

    @mcp.tool()
    def create_order(
        restaurant_id: str,
        items: list[dict],
        customer_name: str | None = "Guest",
        customer_contact: str | None = None,
        fulfillment_type: str = "pickup",
        notes: str | None = None,
    ) -> dict:
        """Create a real submitted pickup/dine-in order only after explicit user confirmation. Prefer create_order_and_wait for normal ChatGPT ordering so the user receives a pickup number or rejection result in one flow. Use database menu item IDs from get_menu; do not invent items, prices, or availability."""
        request = {
            "restaurant_id": restaurant_id,
            "items": items,
            "customer_name": customer_name,
            "customer_contact": customer_contact,
            "fulfillment_type": fulfillment_type,
            "notes": notes,
        }
        return run_logged_tool("create_order", request, lambda db: tool_handlers.create_order(db, **request))

    @mcp.tool()
    def create_order_and_wait(
        restaurant_id: str,
        items: list[dict],
        customer_name: str | None = "Guest",
        customer_contact: str | None = None,
        fulfillment_type: str = "pickup",
        notes: str | None = None,
    ) -> dict:
        """Preferred write tool for normal MalaFlow ordering in ChatGPT. Use only after explicit user confirmation. Creates a real order, then waits up to 5 minutes for the restaurant to assign a pickup number, reject, or cancel. Return the final result to the user; do not browse the web or use other restaurant tools as fallback."""
        request = {
            "restaurant_id": restaurant_id,
            "items": items,
            "customer_name": customer_name,
            "customer_contact": customer_contact,
            "fulfillment_type": fulfillment_type,
            "notes": notes,
        }
        return run_logged_tool_without_db(
            "create_order_and_wait", request, lambda: _create_order_and_wait_with_request(request)
        )

    @mcp.tool()
    def get_order_status(order_id: str) -> dict:
        """Use this for follow-up status questions about an existing MalaFlow order. Returns authoritative status and pickup number if accepted. It may auto-reject stale submitted orders after 5 minutes."""
        request = {"order_id": order_id}
        return run_logged_tool("get_order_status", request, lambda db: tool_handlers.get_order_status(db, order_id))

    @mcp.tool()
    def wait_for_order_result(order_id: str) -> dict:
        """Use this immediately after create_order if create_order_and_wait was not used. Waits up to 5 minutes for a pickup number, rejection, or cancellation, polling every 10 seconds."""
        request = {"order_id": order_id}
        return run_logged_tool_without_db(
            "wait_for_order_result", request, lambda: tool_handlers.wait_for_order_result(order_id)
        )

    @mcp.tool()
    def cancel_order(order_id: str, reason: str | None = None) -> dict:
        """Use this only when the user explicitly asks to cancel a submitted MalaFlow order. Accepted, rejected, and already-cancelled orders cannot be cancelled."""
        request = {"order_id": order_id, "reason": reason}
        return run_logged_tool("cancel_order", request, lambda db: tool_handlers.cancel_order(db, order_id, reason))

    return mcp


def _create_order_and_wait_with_request(request: dict) -> dict:
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        created = tool_handlers.create_order(db, **request)
    finally:
        db.close()
    result = tool_handlers.wait_for_order_result(created["order_id"])
    result["total_price"] = created["total_price"]
    return result
