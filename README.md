# MalaFlow

MalaFlow is a campus pilot for sending AI assistant food orders into real restaurant workflows.

The experiment is simple: a user asks an Agent for food near campus, the Agent calls MalaFlow through MCP, the restaurant receives a submitted order, staff assigns a pickup number, and the Agent tells the user what number to quote at the counter.

```text
User -> Agent -> MCP -> Restaurant workspace -> pickup number -> Agent -> User
```

## Why This Exists

Ordering interfaces are usually built as apps. MalaFlow explores a different question:

> What if a restaurant could expose its ordering ability directly to AI agents?

This is not trying to replace POS systems, delivery apps, or full online ordering platforms. The MVP is intentionally narrow so we can learn whether students will try agent-assisted ordering and whether small restaurants can handle it without changing their normal workflow.

## For Restaurants

MalaFlow gives each pilot restaurant a lightweight workspace:

- Keep menu and pickup instructions up to date.
- Receive submitted orders created by external Agents.
- Enter a pickup number and accept the order.
- Let the Agent report that pickup number back to the user.

Payment and final handoff stay offline at the restaurant.

## For Collaborators

Useful areas to help with:

- MCP client onboarding for non-coders.
- Restaurant workflow design.
- Campus distribution and field testing.
- Backend reliability, notifications, and observability.
- Agent prompt/tool behavior.

## For People Ordering Through An Agent

MalaFlow includes a `malaflow` ordering skill for compatible Agents. The skill tells the Agent to use only the MalaFlow MCP network for restaurant search, menu lookup, pickup ordering, and order status. If MalaFlow has no available result, the Agent should say so instead of searching the web for unrelated restaurants.

To try it, install the skill from this repository, add the MalaFlow MCP server URL, and ask the pilot administrator for a MalaFlow Access Code.

## Project Shape

- `apps/api`: FastAPI, PostgreSQL, SQLAlchemy, Alembic, MCP endpoint, internal admin console.
- `apps/web`: Next.js restaurant workspace and public MCP connection guide.
- `skills/malaflow`: Agent instructions for MalaFlow-only ordering behavior.
- `docs/MVP.md`: MVP behavior and order flow.
- `docs/USER_GUIDE.md`: Public usage guide.

Internal deployment notes, Railway details, and experiment planning docs are intentionally kept out of the public repository.

## Local Development

```bash
cp .env.example .env

cd apps/api
python -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

In another shell:

```bash
cd apps/web
npm install
npm run dev
```

Restaurant accounts are created through the internal admin console. Restaurant staff log in with phone number and password.

## Status

MalaFlow is an early MVP for a student campus pilot. It is open for collaborators and pilot restaurants who are comfortable testing an experimental agent-to-restaurant ordering loop.
