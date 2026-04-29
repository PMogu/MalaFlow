from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.sessions import SessionMiddleware

from app.config import get_settings
from app.database import Base, engine
from app.mcp_server.server import create_mcp_server
from app.routers import admin_console, auth, public, restaurant

settings = get_settings()
mcp_server = create_mcp_server()


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.app_env == "development":
        Base.metadata.create_all(bind=engine)
    async with mcp_server.session_manager.run():
        yield


app = FastAPI(title="MalaFlow API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.admin_session_secret,
    same_site="lax",
    https_only=settings.admin_cookie_secure,
)


@app.middleware("http")
async def mcp_bearer_auth(request: Request, call_next):
    if request.url.path.startswith("/mcp") and request.method != "OPTIONS":
        expected = settings.mcp_bearer_token
        received = request.headers.get("authorization", "")
        if expected and received != f"Bearer {expected}":
            return JSONResponse({"error": "MCP_UNAUTHORIZED"}, status_code=401)
    return await call_next(request)


@app.get("/health")
def health() -> dict:
    return {"ok": True, "service": "malaflow-api"}


app.include_router(auth.router)
app.include_router(admin_console.router)
app.include_router(restaurant.router)
app.include_router(public.router)
app.mount("/mcp", mcp_server.streamable_http_app())
