from __future__ import annotations

import base64
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode, urlparse

import jwt
from fastapi import HTTPException, Request, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import OAuthAuthorizationCode, OAuthClient, OAuthRefreshToken


OAUTH_SCOPE = "mcp"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def issuer_url(request: Request) -> str:
    settings = get_settings()
    if settings.public_base_url:
        return settings.public_base_url.rstrip("/")
    return str(request.base_url).rstrip("/")


def mcp_resource_url(request: Request) -> str:
    return f"{issuer_url(request)}/mcp/"


def protected_resource_metadata_url(request: Request) -> str:
    return f"{issuer_url(request)}/.well-known/oauth-protected-resource/mcp"


def register_client(db: Session, payload: dict) -> dict:
    redirect_uris = payload.get("redirect_uris") or []
    if not isinstance(redirect_uris, list) or not redirect_uris:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="INVALID_REDIRECT_URIS")
    scope = payload.get("scope") or OAUTH_SCOPE
    if isinstance(scope, list):
        scope = " ".join(str(item) for item in scope)

    client = OAuthClient(
        client_name=payload.get("client_name"),
        redirect_uris=[str(uri) for uri in redirect_uris],
        grant_types=payload.get("grant_types") or ["authorization_code", "refresh_token"],
        response_types=payload.get("response_types") or ["code"],
        scope=str(scope),
    )
    db.add(client)
    db.commit()
    db.refresh(client)
    return {
        "client_id": client.id,
        "client_id_issued_at": int(client.created_at.timestamp()),
        "client_name": client.client_name,
        "redirect_uris": client.redirect_uris,
        "grant_types": client.grant_types,
        "response_types": client.response_types,
        "scope": client.scope,
        "token_endpoint_auth_method": "none",
    }


def register_loopback_client(db: Session) -> dict:
    return register_client(
        db,
        {
            "client_name": "MalaFlow OAuth Client",
            "redirect_uris": ["*"],
            "grant_types": ["authorization_code", "refresh_token"],
            "response_types": ["code"],
            "scope": OAUTH_SCOPE,
        },
    )


def redirect_uri_allowed(client: OAuthClient, redirect_uri: str) -> bool:
    if redirect_uri in client.redirect_uris:
        return True
    if "*" not in client.redirect_uris:
        return False
    parsed = urlparse(redirect_uri)
    return parsed.scheme == "http" and parsed.hostname in {"127.0.0.1", "localhost", "::1"}


def validate_authorize_request(
    db: Session,
    client_id: str,
    redirect_uri: str,
    response_type: str,
    code_challenge: str | None,
    code_challenge_method: str | None,
) -> OAuthClient:
    client = db.get(OAuthClient, client_id)
    if not client:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="UNKNOWN_OAUTH_CLIENT")
    if response_type != "code":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="UNSUPPORTED_RESPONSE_TYPE")
    if not redirect_uri_allowed(client, redirect_uri):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="INVALID_REDIRECT_URI")
    if not code_challenge or code_challenge_method != "S256":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="PKCE_S256_REQUIRED")
    return client


def create_authorization_code(
    db: Session,
    client_id: str,
    redirect_uri: str,
    code_challenge: str,
    code_challenge_method: str,
    scope: str | None,
    state: str | None,
    resource: str | None,
) -> str:
    code = secrets.token_urlsafe(48)
    db.add(
        OAuthAuthorizationCode(
            code=code,
            client_id=client_id,
            redirect_uri=redirect_uri,
            code_challenge=code_challenge,
            code_challenge_method=code_challenge_method,
            scope=scope or OAUTH_SCOPE,
            state=state,
            resource=resource,
            expires_at=utcnow() + timedelta(minutes=5),
        )
    )
    db.commit()
    return code


def redirect_with_code(redirect_uri: str, code: str, state: str | None) -> str:
    params = {"code": code}
    if state:
        params["state"] = state
    separator = "&" if "?" in redirect_uri else "?"
    return f"{redirect_uri}{separator}{urlencode(params)}"


def verify_access_code(access_code: str) -> bool:
    settings = get_settings()
    return secrets.compare_digest(access_code.strip(), settings.mcp_bearer_token)


def is_expired(value: datetime) -> bool:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value < utcnow()


def _pkce_challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def create_mcp_access_token(client_id: str, scope: str | None, resource: str | None) -> str:
    settings = get_settings()
    now = utcnow()
    payload = {
        "sub": client_id,
        "iss": "malaflow",
        "aud": "malaflow-mcp",
        "typ": "mcp_oauth",
        "scope": scope or OAUTH_SCOPE,
        "resource": resource,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.mcp_oauth_access_token_minutes)).timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def verify_mcp_access_token(token: str) -> dict | None:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"], audience="malaflow-mcp")
    except jwt.PyJWTError:
        return None
    if payload.get("typ") != "mcp_oauth":
        return None
    scopes = str(payload.get("scope") or "").split()
    if OAUTH_SCOPE not in scopes:
        return None
    return payload


def is_valid_mcp_bearer_token(token: str | None) -> bool:
    if not token:
        return False
    settings = get_settings()
    if settings.mcp_bearer_token and secrets.compare_digest(token, settings.mcp_bearer_token):
        return True
    return verify_mcp_access_token(token) is not None


def exchange_authorization_code(db: Session, form: dict) -> dict:
    code_value = form.get("code")
    client_id = form.get("client_id")
    redirect_uri = form.get("redirect_uri")
    code_verifier = form.get("code_verifier")
    if not all([code_value, client_id, redirect_uri, code_verifier]):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="INVALID_TOKEN_REQUEST")

    code = db.get(OAuthAuthorizationCode, code_value)
    if (
        not code
        or code.client_id != client_id
        or code.redirect_uri != redirect_uri
        or code.used_at is not None
        or is_expired(code.expires_at)
    ):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="INVALID_AUTHORIZATION_CODE")
    if _pkce_challenge(code_verifier) != code.code_challenge:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="INVALID_PKCE_VERIFIER")

    code.used_at = utcnow()
    refresh_token = OAuthRefreshToken(
        token=secrets.token_urlsafe(48),
        client_id=client_id,
        scope=code.scope,
        resource=code.resource,
        expires_at=utcnow() + timedelta(days=get_settings().mcp_oauth_refresh_token_days),
    )
    db.add(refresh_token)
    db.commit()
    return token_response(client_id, code.scope, code.resource, refresh_token.token)


def exchange_refresh_token(db: Session, form: dict) -> dict:
    token_value = form.get("refresh_token")
    client_id = form.get("client_id")
    if not token_value or not client_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="INVALID_REFRESH_REQUEST")
    refresh = db.get(OAuthRefreshToken, token_value)
    if (
        not refresh
        or refresh.client_id != client_id
        or refresh.revoked_at is not None
        or is_expired(refresh.expires_at)
    ):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="INVALID_REFRESH_TOKEN")
    return token_response(client_id, refresh.scope, refresh.resource, refresh.token)


def token_response(client_id: str, scope: str | None, resource: str | None, refresh_token: str) -> dict:
    settings = get_settings()
    return {
        "access_token": create_mcp_access_token(client_id, scope, resource),
        "token_type": "Bearer",
        "expires_in": settings.mcp_oauth_access_token_minutes * 60,
        "refresh_token": refresh_token,
        "scope": scope or OAUTH_SCOPE,
    }
