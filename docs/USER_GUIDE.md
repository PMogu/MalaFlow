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

1. Install the `malaflow` ordering skill from the MalaFlow GitHub repository.
2. Open an AI assistant that supports MCP tools.
3. Add the MalaFlow MCP server URL shared by the pilot team.
4. Add the MalaFlow Access Code, also called a Bearer token, when the assistant asks for authorization.
5. Start with a prompt like:

```text
Use the MalaFlow skill. I want something hot near Unimelb for pickup. Can you help me order?
```

The Agent should use MalaFlow tools only, recommend a restaurant or dish, ask for confirmation before ordering, create the order, and later check for the pickup number. If MalaFlow has no available restaurant or matching menu item, the Agent should tell you instead of searching the web.

## Order States

```text
submitted -> accepted
submitted -> cancelled
submitted -> rejected
```

- `submitted`: the Agent placed the order and restaurant staff have not processed it yet.
- `accepted`: restaurant staff accepted the order and assigned a pickup number.
- `cancelled`: the user cancelled before the restaurant accepted.
- `rejected`: the restaurant rejected before accepting.

`accepted` always includes an `order_number`.
