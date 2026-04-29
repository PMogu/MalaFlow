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

1. Open an AI assistant that supports MCP tools.
2. Add the MalaFlow MCP server URL shared by the pilot team.
3. Add the pilot access token when the assistant asks for authorization.
4. Try a prompt like:

```text
I want beef noodles near Unimelb. Can you help me order pickup?
```

The Agent should recommend a restaurant or dish, ask for confirmation before ordering, create the order, and later check for the pickup number.

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
