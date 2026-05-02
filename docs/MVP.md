# MalaFlow MVP Notes

## Scope

The restaurant network is pre-filtered to Unimelb nearby restaurants. The MVP does not store or compute user location.
Restaurants may enter a free-text location so Agents can tell users where the restaurant is.

## Order States

- `submitted`: Agent has placed the order and the restaurant has not processed it yet.
- `accepted`: Restaurant staff accepted the order and assigned an `order_number`.
- `cancelled`: User cancelled a submitted order through the Agent.
- `rejected`: Restaurant staff rejected a submitted order, or no pickup number was assigned within 5 minutes.

Allowed transitions:

```text
submitted -> accepted
submitted -> cancelled
submitted -> rejected
```

`accepted` requires `order_number`.
If an order remains `submitted` for 5 minutes after creation, MalaFlow automatically changes it to `rejected` with the reason `No pickup number was assigned within 5 minutes.`

## MCP Tools

- `search_restaurants`
- `get_restaurant_detail`
- `get_menu`
- `create_order`
- `create_order_and_wait`
- `get_order_status`
- `wait_for_order_result`
- `cancel_order`

All tools call backend service functions and write to `mcp_call_logs`.
For normal ChatGPT ordering, `create_order_and_wait` is the preferred write tool because it creates the order and returns the pickup number, rejection, or cancellation result in one flow.

The deployed Streamable HTTP URL is `https://api.malaflow.com/mcp/`.
