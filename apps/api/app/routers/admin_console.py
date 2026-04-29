import hmac
import html
from urllib.parse import parse_qs

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.config import get_settings
from app.database import get_db
from app.models import Restaurant
from app.schemas import CreateUserInput, RestaurantAccountInput, RestaurantInput, RestaurantOnboardingInput, UpdateUserInput
from app.services import admin as admin_service

router = APIRouter(prefix="/admin", tags=["admin-console"])
SESSION_KEY = "restaurant_skill_loop_admin"


def esc(value: object) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def split_csv(value: str | None) -> list[str]:
    return [item.strip() for item in (value or "").split(",") if item.strip()]


def checked(value: bool) -> str:
    return "checked" if value else ""


def is_admin_authenticated(request: Request) -> bool:
    return bool(request.session.get(SESSION_KEY))


def admin_redirect() -> RedirectResponse:
    return RedirectResponse("/admin/login", status_code=status.HTTP_303_SEE_OTHER)


async def read_form(request: Request) -> dict[str, str]:
    body = (await request.body()).decode("utf-8")
    parsed = parse_qs(body, keep_blank_values=True)
    return {key: values[-1] if values else "" for key, values in parsed.items()}


def page(title: str, body: str, status_code: int = 200) -> HTMLResponse:
    return HTMLResponse(
        f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{esc(title)} · MalaFlow Admin</title>
  <style>
    :root {{
      --ink: #17201b;
      --muted: #66736c;
      --line: #d7ded8;
      --paper: #f6f8f5;
      --panel: #ffffff;
      --green: #0f6f4d;
      --red: #a13b32;
      --blue: #245f86;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--paper);
      color: var(--ink);
      font-family: "Avenir Next", "Segoe UI", sans-serif;
      font-size: 14px;
    }}
    a {{ color: inherit; }}
    .shell {{ width: min(1040px, calc(100vw - 32px)); margin: 0 auto; padding: 28px 0 56px; }}
    .topbar {{ display: flex; align-items: center; justify-content: space-between; gap: 16px; border-bottom: 1px solid var(--line); padding-bottom: 14px; margin-bottom: 20px; }}
    .eyebrow {{ color: var(--muted); font-family: "Courier New", monospace; font-size: 12px; text-transform: uppercase; }}
    h1 {{ margin: 4px 0 0; font-size: 28px; line-height: 1.1; }}
    h2 {{ margin: 0 0 12px; font-size: 18px; }}
    p {{ margin: 0; }}
    .panel {{ background: var(--panel); border: 1px solid var(--line); border-radius: 6px; padding: 18px; margin-bottom: 16px; }}
    .grid {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; }}
    .field {{ display: grid; gap: 5px; margin-bottom: 12px; }}
    label span {{ color: var(--muted); font-family: "Courier New", monospace; font-size: 12px; text-transform: uppercase; }}
    input, textarea, select {{ width: 100%; border: 1px solid var(--line); border-radius: 4px; padding: 9px 10px; font: inherit; background: #fbfcfb; }}
    textarea {{ min-height: 90px; resize: vertical; }}
    button, .button {{ border: 1px solid var(--ink); border-radius: 4px; background: var(--ink); color: white; padding: 9px 12px; font: inherit; cursor: pointer; text-decoration: none; display: inline-flex; align-items: center; gap: 8px; }}
    .button.secondary, button.secondary {{ background: white; color: var(--ink); }}
    .button.danger {{ border-color: var(--red); color: var(--red); background: white; }}
    .row {{ display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }}
    .table {{ width: 100%; border-collapse: collapse; }}
    .table th, .table td {{ text-align: left; padding: 10px 8px; border-bottom: 1px solid var(--line); vertical-align: top; }}
    .table th {{ color: var(--muted); font-family: "Courier New", monospace; font-size: 12px; text-transform: uppercase; }}
    .status {{ display: inline-flex; border: 1px solid var(--line); border-radius: 999px; padding: 3px 8px; font-family: "Courier New", monospace; font-size: 12px; }}
    .status.open, .status.visible, .status.active {{ color: var(--green); }}
    .status.closed, .status.hidden, .status.inactive {{ color: var(--red); }}
    .notice {{ background: #edf6f0; border-left: 4px solid var(--green); padding: 10px 12px; margin-bottom: 16px; }}
    .error {{ background: #fff0ee; border-left-color: var(--red); color: var(--red); }}
    @media (max-width: 760px) {{ .topbar, .grid {{ display: grid; grid-template-columns: 1fr; }} }}
  </style>
</head>
<body>
  <main class="shell">{body}</main>
</body>
</html>""",
        status_code=status_code,
    )


def topbar(title: str) -> str:
    return f"""
<section class="topbar">
  <div>
    <p class="eyebrow">Internal admin</p>
    <h1>{esc(title)}</h1>
  </div>
  <form method="post" action="/admin/logout">
    <button class="secondary" type="submit">Logout</button>
  </form>
</section>
"""


def restaurant_form(
    restaurant: Restaurant | None = None,
    account_phone: str = "",
    account_email: str = "",
    account_active: bool = True,
) -> str:
    is_edit = restaurant is not None
    cuisine = ", ".join(restaurant.cuisine_tags or []) if restaurant else ""
    modes = ", ".join(restaurant.service_modes or ["pickup"]) if restaurant else "pickup"
    return f"""
<div class="grid">
  <label class="field"><span>Restaurant name</span><input name="name" required value="{esc(restaurant.name if restaurant else "")}" /></label>
  <label class="field"><span>Account phone</span><input name="account_phone" required value="{esc(account_phone)}" placeholder="+614..." /></label>
</div>
<div class="grid">
  <label class="field"><span>Description</span><textarea name="description">{esc(restaurant.description if restaurant else "")}</textarea></label>
  <label class="field"><span>{'New password (optional)' if is_edit else 'Initial password'}</span><input name="account_password" {'required' if not is_edit else ''} type="password" /></label>
</div>
<div class="grid">
  <label class="field"><span>Restaurant location</span><input name="location_text" value="{esc(restaurant.location_text if restaurant else "")}" placeholder="Near Unimelb, e.g. Swanston St" /></label>
  <label class="field"><span>Account email (optional)</span><input name="account_email" type="email" value="{esc(account_email)}" /></label>
</div>
<div class="grid">
  <label class="field"><span>Cuisine tags</span><input name="cuisine_tags" value="{esc(cuisine)}" /></label>
  <label class="field"><span>Service modes</span><input name="service_modes" value="{esc(modes)}" /></label>
</div>
<div class="grid">
  <label class="field"><span>Pickup instructions</span><input name="pickup_instructions" value="{esc(restaurant.pickup_instructions if restaurant else "")}" /></label>
  <label class="field"><span>Status</span>
    <select name="status">
      <option value="open" {'selected' if not restaurant or restaurant.status == 'open' else ''}>open</option>
      <option value="closed" {'selected' if restaurant and restaurant.status == 'closed' else ''}>closed</option>
    </select>
  </label>
</div>
<div class="row">
  <label class="row"><input name="mcp_visible" type="checkbox" {checked(True if not restaurant else restaurant.mcp_visible)} /> MCP visible</label>
  <label class="row"><input name="account_active" type="checkbox" {checked(account_active)} /> Account active</label>
  <button type="submit">{'Save changes' if is_edit else 'Create restaurant'}</button>
</div>
"""


def restaurant_input_from_form(data: dict[str, str]) -> RestaurantInput:
    return RestaurantInput(
        name=data.get("name", "").strip(),
        description=data.get("description", "").strip() or None,
        location_text=data.get("location_text", "").strip() or None,
        cuisine_tags=split_csv(data.get("cuisine_tags")),
        service_modes=split_csv(data.get("service_modes")) or ["pickup"],
        status=data.get("status", "open"),
        mcp_visible=data.get("mcp_visible") == "on",
        pickup_instructions=data.get("pickup_instructions", "").strip() or None,
    )


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    if is_admin_authenticated(request):
        return RedirectResponse("/admin", status_code=status.HTTP_303_SEE_OTHER)
    return page(
        "Admin login",
        """
<section class="topbar">
  <div>
    <p class="eyebrow">Internal admin</p>
    <h1>MalaFlow restaurant onboarding</h1>
  </div>
</section>
<form class="panel" method="post" action="/admin/login">
  <h2>Single password login</h2>
  <label class="field"><span>Password</span><input name="password" type="password" autofocus required /></label>
  <button type="submit">Login</button>
</form>
""",
    )


@router.post("/login", response_class=HTMLResponse)
async def login(request: Request):
    data = await read_form(request)
    settings = get_settings()
    if hmac.compare_digest(data.get("password", ""), settings.admin_password):
        request.session[SESSION_KEY] = True
        return RedirectResponse("/admin", status_code=status.HTTP_303_SEE_OTHER)
    return page(
        "Admin login",
        """
<section class="topbar"><div><p class="eyebrow">Internal admin</p><h1>MalaFlow restaurant onboarding</h1></div></section>
<p class="notice error">Password did not match.</p>
<form class="panel" method="post" action="/admin/login">
  <h2>Single password login</h2>
  <label class="field"><span>Password</span><input name="password" type="password" autofocus required /></label>
  <button type="submit">Login</button>
</form>
""",
        status_code=401,
    )


@router.post("/logout")
def logout(request: Request) -> RedirectResponse:
    request.session.clear()
    return RedirectResponse("/admin/login", status_code=status.HTTP_303_SEE_OTHER)


@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    if not is_admin_authenticated(request):
        return admin_redirect()
    restaurants = db.scalars(
        select(Restaurant).options(selectinload(Restaurant.users)).order_by(Restaurant.created_at.desc())
    ).all()
    rows = []
    for restaurant in restaurants:
        account = admin_service.primary_account(restaurant)
        rows.append(
            f"""
<tr>
  <td><a href="/admin/restaurants/{esc(restaurant.id)}">{esc(restaurant.name)}</a></td>
  <td>{esc(account.phone if account else "No account")}</td>
  <td><span class="status {esc(restaurant.status)}">{esc(restaurant.status)}</span></td>
  <td><span class="status {'visible' if restaurant.mcp_visible else 'hidden'}">{'visible' if restaurant.mcp_visible else 'hidden'}</span></td>
</tr>"""
        )
    return page(
        "Restaurants",
        topbar("Restaurants")
        + """
<div class="row" style="margin-bottom: 16px;">
  <a class="button" href="/admin/restaurants/new">Add restaurant</a>
</div>
<section class="panel">
  <h2>Campus pilot restaurants</h2>
  <table class="table">
    <thead><tr><th>Restaurant</th><th>Phone</th><th>Status</th><th>MCP</th></tr></thead>
    <tbody>
"""
        + "\n".join(rows)
        + """
    </tbody>
  </table>
</section>
""",
    )


@router.get("/restaurants/new", response_class=HTMLResponse)
def new_restaurant(request: Request):
    if not is_admin_authenticated(request):
        return admin_redirect()
    return page(
        "Add restaurant",
        topbar("Add restaurant")
        + f"""
<form class="panel" method="post" action="/admin/restaurants/new">
  <h2>Restaurant + login account</h2>
  {restaurant_form()}
</form>
""",
    )


@router.post("/restaurants/new", response_class=HTMLResponse)
async def create_restaurant(request: Request, db: Session = Depends(get_db)):
    if not is_admin_authenticated(request):
        return admin_redirect()
    data = await read_form(request)
    try:
        created = admin_service.create_restaurant_onboarding(
            db,
            RestaurantOnboardingInput(
                restaurant=restaurant_input_from_form(data),
                account=RestaurantAccountInput(
                    phone=data.get("account_phone", "").strip(),
                    email=data.get("account_email", "").strip(),
                    password=data.get("account_password", ""),
                    is_active=data.get("account_active") == "on",
                ),
            ),
        )
    except (ValidationError, Exception) as exc:
        detail = getattr(exc, "detail", str(exc))
        return page("Add restaurant", topbar("Add restaurant") + f'<p class="notice error">{esc(detail)}</p><form class="panel" method="post" action="/admin/restaurants/new">{restaurant_form()}</form>', status_code=400)
    return RedirectResponse(f"/admin/restaurants/{created['restaurant']['id']}", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/restaurants/{restaurant_id}", response_class=HTMLResponse)
def restaurant_detail(
    restaurant_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    if not is_admin_authenticated(request):
        return admin_redirect()
    restaurant = admin_service.get_restaurant_with_accounts(db, restaurant_id)
    account = admin_service.primary_account(restaurant)
    account_html = (
        f"<p>{esc(account.phone)}"
        f"{' · ' + esc(account.email) if account.email else ''}"
        f" - <span class=\"status {'active' if account.is_active else 'inactive'}\">{'active' if account.is_active else 'inactive'}</span></p>"
        if account
        else "<p>No restaurant account is bound yet.</p>"
    )
    return page(
        restaurant.name,
        topbar(restaurant.name)
        + f"""
<section class="panel">
  <h2>Bound account</h2>
  {account_html}
</section>
<form class="panel" method="post" action="/admin/restaurants/{esc(restaurant.id)}">
  <h2>Edit restaurant</h2>
  {restaurant_form(restaurant, account.phone if account else "", account.email if account else "", account.is_active if account else True)}
</form>
<p><a class="button secondary" href="/admin">Back to restaurants</a></p>
""",
    )


@router.post("/restaurants/{restaurant_id}", response_class=HTMLResponse)
async def update_restaurant(
    restaurant_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    if not is_admin_authenticated(request):
        return admin_redirect()
    data = await read_form(request)
    try:
        admin_service.update_restaurant(db, restaurant_id, restaurant_input_from_form(data))
        restaurant = admin_service.get_restaurant_with_accounts(db, restaurant_id)
        account = admin_service.primary_account(restaurant)
        if account:
            admin_service.update_user(
                db,
                account.id,
                UpdateUserInput(
                    phone=data.get("account_phone", "").strip(),
                    email=data.get("account_email", "").strip(),
                    password=data.get("account_password", "") or None,
                    restaurant_id=restaurant.id,
                    is_active=data.get("account_active") == "on",
                ),
            )
        elif data.get("account_phone") and data.get("account_password"):
            admin_service.create_user(
                db,
                CreateUserInput(
                    phone=data.get("account_phone", "").strip(),
                    email=data.get("account_email", "").strip(),
                    password=data.get("account_password", ""),
                    restaurant_id=restaurant.id,
                    is_active=data.get("account_active") == "on",
                ),
            )
    except (ValidationError, Exception) as exc:
        detail = getattr(exc, "detail", str(exc))
        restaurant = admin_service.get_restaurant_with_accounts(db, restaurant_id)
        account = admin_service.primary_account(restaurant)
        return page(
            restaurant.name,
            topbar(restaurant.name)
            + f'<p class="notice error">{esc(detail)}</p><form class="panel" method="post" action="/admin/restaurants/{esc(restaurant.id)}">{restaurant_form(restaurant, account.phone if account else "", account.email if account else "", account.is_active if account else True)}</form>',
            status_code=400,
        )
    return RedirectResponse(f"/admin/restaurants/{restaurant_id}", status_code=status.HTTP_303_SEE_OTHER)
