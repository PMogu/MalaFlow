# MalaFlow MVP Notes

## Scope

The restaurant network is pre-filtered to Unimelb nearby restaurants. The MVP does not store or compute user location.
Restaurants may enter a free-text location so Agents can tell users where the restaurant is.

## Order States

- `submitted`: Agent has placed the order and the restaurant has not processed it yet.
- `accepted`: Restaurant staff accepted the order and assigned an `order_number`.
- `cancelled`: User cancelled a submitted order through the Agent.
- `rejected`: Restaurant staff rejected a submitted order.

Allowed transitions:

```text
submitted -> accepted
submitted -> cancelled
submitted -> rejected
```

`accepted` requires `order_number`.

## MCP Tools

- `search_restaurants`
- `get_restaurant_detail`
- `get_menu`
- `create_order`
- `get_order_status`
- `cancel_order`

All tools call backend service functions and write to `mcp_call_logs`.

The deployed Streamable HTTP URL uses the mounted ASGI path `/mcp/`.
