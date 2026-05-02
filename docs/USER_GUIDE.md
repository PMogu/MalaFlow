# MalaFlow User Guide

MalaFlow lets an AI assistant send a confirmed food order into a restaurant workspace.

```text
User -> Agent -> MCP -> Restaurant workspace -> pickup number -> Agent -> User
```

## For Restaurant Staff

1. Open the MalaFlow restaurant workspace.
2. Log in with the phone number and password provided during onboarding.
3. Keep the page open and enable order alerts.
4. When a submitted order appears, review the items and notes.
5. Enter a pickup number, for example `A17`.
6. Click **Accept**.

The user's Agent can then check the order status and tell the user the pickup number.

## For People Ordering Through An AI Assistant

1. Open ChatGPT with custom MCP connector support enabled.
2. Add the MalaFlow MCP server URL: `https://api.malaflow.com/mcp/`.
3. When the MalaFlow login page opens, enter the Access Code provided by the pilot administrator.
4. Start with this prompt:

```text
Use the malaflow skill. I want something hot near Unimelb for pickup. Please search MalaFlow, help me confirm an order, then wait for the pickup number or rejection result.
```

The Agent should use MalaFlow tools only, recommend a restaurant or dish, ask for confirmation before ordering, create the order, then wait for a pickup number or rejection result. If MalaFlow has no available restaurant or matching menu item, the Agent should tell you instead of searching the web.

For Codex, Cursor, Claude, Continue, or other MCP clients, install the `malaflow` ordering skill from the GitHub repository, add the same MCP URL manually, and use the Access Code as a Bearer token if the client asks for one.

## Order States

```text
submitted -> accepted
submitted -> cancelled
submitted -> rejected
```

- `submitted`: the Agent placed the order and restaurant staff have not processed it yet.
- `accepted`: restaurant staff accepted the order and assigned a pickup number.
- `cancelled`: the user cancelled before the restaurant accepted.
- `rejected`: the restaurant rejected before accepting, or no pickup number was assigned within 5 minutes.

`accepted` always includes an `order_number`.
