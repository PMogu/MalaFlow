from mcp.server.fastmcp import FastMCP

from app.mcp_server import tool_handlers
from app.services.mcp_logging import run_logged_tool


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
        """Search the MalaFlow campus pilot restaurant network by dish, cuisine, or rough budget."""
        request = {"query": query, "cuisine": cuisine, "max_budget": max_budget}
        return run_logged_tool("search_restaurants", request, lambda db: tool_handlers.search_restaurants(db, **request))

    @mcp.tool()
    def get_restaurant_detail(restaurant_id: str) -> dict:
        """Get one restaurant's public detail."""
        request = {"restaurant_id": restaurant_id}
        return run_logged_tool(
            "get_restaurant_detail", request, lambda db: tool_handlers.get_restaurant_detail(db, restaurant_id)
        )

    @mcp.tool()
    def get_menu(restaurant_id: str) -> dict:
        """Get available menu items for a restaurant."""
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
        """Create a real submitted pickup/dine-in order after the Agent has confirmed with the user."""
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
    def get_order_status(order_id: str) -> dict:
        """Get current order status, user-facing message, and pickup number if accepted."""
        request = {"order_id": order_id}
        return run_logged_tool("get_order_status", request, lambda db: tool_handlers.get_order_status(db, order_id))

    @mcp.tool()
    def cancel_order(order_id: str, reason: str | None = None) -> dict:
        """Cancel a submitted order at the user's request."""
        request = {"order_id": order_id, "reason": reason}
        return run_logged_tool("cancel_order", request, lambda db: tool_handlers.cancel_order(db, order_id, reason))

    return mcp
