import html
from urllib.parse import parse_qs

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.services import oauth as oauth_service

router = APIRouter(tags=["oauth"])


def esc(value: object) -> str:
    return html.escape("" if value is None else str(value), quote=True)


async def read_form(request: Request) -> dict[str, str]:
    body = (await request.body()).decode("utf-8")
    parsed = parse_qs(body, keep_blank_values=True)
    return {key: values[-1] if values else "" for key, values in parsed.items()}


def oauth_login_page(params: dict, error: str | None = None) -> HTMLResponse:
    hidden = "\n".join(
        f'<input type="hidden" name="{esc(key)}" value="{esc(value)}" />'
        for key, value in params.items()
        if value is not None
    )
    error_html = f'<p class="notice error">{esc(error)}</p>' if error else ""
    return HTMLResponse(
        f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>MalaFlow Login</title>
  <style>
    body {{ margin: 0; background: #f6f8f5; color: #17201b; font-family: "Avenir Next", "Segoe UI", sans-serif; }}
    main {{ width: min(520px, calc(100vw - 32px)); margin: 0 auto; padding: 56px 0; }}
    .panel {{ background: white; border: 1px solid #d7ded8; border-radius: 6px; padding: 20px; }}
    h1 {{ margin: 0 0 8px; font-size: 28px; }}
    p {{ margin: 0 0 16px; color: #66736c; }}
    label {{ display: grid; gap: 6px; margin-bottom: 14px; }}
    span {{ color: #66736c; font-family: "Courier New", monospace; font-size: 12px; text-transform: uppercase; }}
    input {{ border: 1px solid #d7ded8; border-radius: 4px; padding: 10px; font: inherit; }}
    button {{ border: 1px solid #17201b; border-radius: 4px; background: #17201b; color: white; padding: 10px 12px; font: inherit; cursor: pointer; }}
    .notice {{ background: #edf6f0; border-left: 4px solid #0f6f4d; padding: 10px 12px; }}
    .error {{ background: #fff0ee; border-left-color: #a13b32; color: #a13b32; }}
  </style>
</head>
<body>
  <main>
    <form class="panel" method="post" action="/oauth/authorize">
      <h1>Connect MalaFlow</h1>
      <p>Enter the MalaFlow Access Code from the pilot administrator.</p>
      {error_html}
      {hidden}
      <label><span>Access Code</span><input name="access_code" type="password" autofocus required /></label>
      <button type="submit">Authorize</button>
    </form>
  </main>
</body>
</html>""",
        status_code=status.HTTP_401_UNAUTHORIZED if error else status.HTTP_200_OK,
    )


@router.get("/.well-known/oauth-protected-resource")
@router.get("/.well-known/oauth-protected-resource/mcp")
def protected_resource_metadata(request: Request) -> dict:
    issuer = oauth_service.issuer_url(request)
    return {
        "resource": oauth_service.mcp_resource_url(request),
        "authorization_servers": [issuer],
        "bearer_methods_supported": ["header"],
        "scopes_supported": [oauth_service.OAUTH_SCOPE],
        "resource_name": "MalaFlow MCP",
    }


@router.get("/.well-known/oauth-authorization-server")
@router.get("/.well-known/oauth-authorization-server/mcp")
@router.get("/.well-known/openid-configuration")
@router.get("/.well-known/openid-configuration/mcp")
@router.get("/mcp/.well-known/oauth-authorization-server")
@router.get("/mcp/.well-known/openid-configuration")
def authorization_server_metadata(request: Request) -> dict:
    issuer = oauth_service.issuer_url(request)
    return {
        "issuer": issuer,
        "authorization_endpoint": f"{issuer}/oauth/authorize",
        "token_endpoint": f"{issuer}/oauth/token",
        "registration_endpoint": f"{issuer}/oauth/register",
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code", "refresh_token"],
        "token_endpoint_auth_methods_supported": ["none"],
        "code_challenge_methods_supported": ["S256"],
        "scopes_supported": [oauth_service.OAUTH_SCOPE],
    }


@router.post("/oauth/register")
async def register_client(request: Request, db: Session = Depends(get_db)) -> JSONResponse:
    payload = await request.json()
    return JSONResponse(oauth_service.register_client(db, payload), status_code=status.HTTP_201_CREATED)


@router.get("/oauth/register")
def register_loopback_client(db: Session = Depends(get_db)) -> JSONResponse:
    return JSONResponse(oauth_service.register_loopback_client(db), status_code=status.HTTP_201_CREATED)


@router.get("/oauth/authorize", response_class=HTMLResponse)
def authorize_page(
    request: Request,
    client_id: str,
    redirect_uri: str,
    response_type: str,
    code_challenge: str | None = None,
    code_challenge_method: str | None = None,
    scope: str | None = None,
    state: str | None = None,
    resource: str | None = None,
    db: Session = Depends(get_db),
):
    oauth_service.validate_authorize_request(
        db,
        client_id=client_id,
        redirect_uri=redirect_uri,
        response_type=response_type,
        code_challenge=code_challenge,
        code_challenge_method=code_challenge_method,
    )
    return oauth_login_page(
        {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": response_type,
            "code_challenge": code_challenge,
            "code_challenge_method": code_challenge_method,
            "scope": scope or oauth_service.OAUTH_SCOPE,
            "state": state,
            "resource": resource or oauth_service.mcp_resource_url(request),
        }
    )


@router.post("/oauth/authorize", response_class=HTMLResponse)
async def authorize_submit(request: Request, db: Session = Depends(get_db)):
    data = await read_form(request)
    oauth_service.validate_authorize_request(
        db,
        client_id=data.get("client_id", ""),
        redirect_uri=data.get("redirect_uri", ""),
        response_type=data.get("response_type", ""),
        code_challenge=data.get("code_challenge"),
        code_challenge_method=data.get("code_challenge_method"),
    )
    if not oauth_service.verify_access_code(data.get("access_code", "")):
        return oauth_login_page(data, error="Access code did not match.")
    code = oauth_service.create_authorization_code(
        db,
        client_id=data["client_id"],
        redirect_uri=data["redirect_uri"],
        code_challenge=data["code_challenge"],
        code_challenge_method=data["code_challenge_method"],
        scope=data.get("scope"),
        state=data.get("state"),
        resource=data.get("resource") or oauth_service.mcp_resource_url(request),
    )
    return RedirectResponse(
        oauth_service.redirect_with_code(data["redirect_uri"], code, data.get("state")),
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.post("/oauth/token")
async def token(request: Request, db: Session = Depends(get_db)) -> JSONResponse:
    data = await read_form(request)
    grant_type = data.get("grant_type")
    if grant_type == "authorization_code":
        return JSONResponse(oauth_service.exchange_authorization_code(db, data))
    if grant_type == "refresh_token":
        return JSONResponse(oauth_service.exchange_refresh_token(db, data))
    return JSONResponse({"error": "unsupported_grant_type"}, status_code=status.HTTP_400_BAD_REQUEST)
