import base64
import hashlib

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import main
from app.config import get_settings
from app.database import Base, get_db
from app.models import MenuItem, Restaurant
from decimal import Decimal


def pkce_pair() -> tuple[str, str]:
    verifier = "verifier-1234567890"
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii")).digest()).rstrip(b"=").decode(
        "ascii"
    )
    return verifier, challenge


@pytest.fixture()
def client(monkeypatch):
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    session = Session()
    restaurant = Restaurant(
        name="Mala Test",
        slug="mala-test",
        description="Hot food near Unimelb",
        location_text="University Square",
        cuisine_tags=["hot"],
        service_modes=["pickup"],
        status="open",
        mcp_visible=True,
    )
    session.add(restaurant)
    session.flush()
    session.add(
        MenuItem(
            restaurant_id=restaurant.id,
            name="Hot Noodles",
            description="Spicy noodles",
            price=Decimal("16.80"),
            category="Noodles",
            tags=["hot"],
            available=True,
        )
    )
    session.commit()

    def override_db():
        try:
            yield session
        finally:
            pass

    settings = get_settings()
    monkeypatch.setattr(settings, "mcp_bearer_token", "MALA_TEST_CODE")
    monkeypatch.setattr(settings, "app_env", "test")
    monkeypatch.setattr(settings, "public_base_url", None)
    main.app.dependency_overrides[get_db] = override_db
    yield TestClient(main.app)
    main.app.dependency_overrides.clear()
    session.close()


def test_mcp_without_token_returns_oauth_challenge(client):
    response = client.post("/mcp/", json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"})

    assert response.status_code == 401
    assert response.json()["error"] == "invalid_token"
    assert "WWW-Authenticate" in response.headers
    assert "oauth-protected-resource/mcp" in response.headers["WWW-Authenticate"]
    assert 'scope="mcp"' in response.headers["WWW-Authenticate"]


def test_oauth_metadata_endpoints(client):
    resource = client.get("/.well-known/oauth-protected-resource/mcp")
    root_resource = client.get("/.well-known/oauth-protected-resource")
    auth_server = client.get("/.well-known/oauth-authorization-server")
    scoped_auth_server = client.get("/.well-known/oauth-authorization-server/mcp")
    mounted_auth_server = client.get("/mcp/.well-known/oauth-authorization-server")

    assert resource.status_code == 200
    assert root_resource.status_code == 200
    assert resource.json()["bearer_methods_supported"] == ["header"]
    assert resource.json()["authorization_servers"]
    assert auth_server.status_code == 200
    assert scoped_auth_server.status_code == 200
    assert mounted_auth_server.status_code == 200
    assert auth_server.json()["authorization_endpoint"].endswith("/oauth/authorize")
    assert auth_server.json()["token_endpoint"].endswith("/oauth/token")
    assert auth_server.json()["registration_endpoint"].endswith("/oauth/register")


def test_oauth_metadata_uses_public_base_url(client):
    settings = get_settings()
    settings.public_base_url = "https://malaflow.example"

    response = client.get("/.well-known/oauth-authorization-server")

    assert response.status_code == 200
    assert response.json()["issuer"] == "https://malaflow.example"
    assert response.json()["registration_endpoint"] == "https://malaflow.example/oauth/register"


def test_oauth_register_get_creates_loopback_client(client):
    registration = client.get("/oauth/register")

    assert registration.status_code == 201
    assert registration.json()["client_id"].startswith("oauth_client_")
    assert registration.json()["redirect_uris"] == ["*"]


def test_oauth_pkce_flow_issues_valid_mcp_token(client):
    verifier, challenge = pkce_pair()
    registration = client.post(
        "/oauth/register",
        json={
            "client_name": "Test Client",
            "redirect_uris": ["http://127.0.0.1:4321/callback"],
        },
    )
    assert registration.status_code == 201
    client_id = registration.json()["client_id"]

    authorize = client.post(
        "/oauth/authorize",
        data={
            "client_id": client_id,
            "redirect_uri": "http://127.0.0.1:4321/callback",
            "response_type": "code",
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "scope": "mcp",
            "state": "abc",
            "access_code": "MALA_TEST_CODE",
        },
        follow_redirects=False,
    )
    assert authorize.status_code == 303
    location = authorize.headers["location"]
    code = location.split("code=", 1)[1].split("&", 1)[0]

    token = client.post(
        "/oauth/token",
        data={
            "grant_type": "authorization_code",
            "client_id": client_id,
            "redirect_uri": "http://127.0.0.1:4321/callback",
            "code": code,
            "code_verifier": verifier,
        },
    )
    assert token.status_code == 200
    access_token = token.json()["access_token"]
    assert main.oauth_service.is_valid_mcp_bearer_token(access_token)


def test_oauth_get_registered_loopback_client_accepts_local_redirect(client):
    verifier, challenge = pkce_pair()
    registration = client.get("/oauth/register")
    client_id = registration.json()["client_id"]

    authorize = client.post(
        "/oauth/authorize",
        data={
            "client_id": client_id,
            "redirect_uri": "http://127.0.0.1:4321/callback",
            "response_type": "code",
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "scope": "mcp",
            "access_code": "MALA_TEST_CODE",
        },
        follow_redirects=False,
    )

    assert authorize.status_code == 303


def test_legacy_bearer_token_still_valid_for_mcp(client):
    assert main.oauth_service.is_valid_mcp_bearer_token("MALA_TEST_CODE")
