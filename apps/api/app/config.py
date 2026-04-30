from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _repo_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "AGENTS.md").exists() or (parent / ".env").exists():
            return parent
    return current.parents[1]


load_dotenv(_repo_root() / ".env")
load_dotenv(Path(__file__).resolve().parents[1] / ".env")


class Settings(BaseSettings):
    app_env: str = Field(default="development", alias="APP_ENV")
    database_url: str = Field(default="sqlite:///./restaurant_skill_loop.sqlite", alias="DATABASE_URL")
    jwt_secret: str = Field(default="dev-secret-change-me", alias="JWT_SECRET")
    jwt_expires_minutes: int = Field(default=60 * 24 * 7, alias="JWT_EXPIRES_MINUTES")
    mcp_bearer_token: str = Field(default="dev-mcp-token", alias="MCP_BEARER_TOKEN")
    mcp_oauth_access_token_minutes: int = Field(default=60, alias="MCP_OAUTH_ACCESS_TOKEN_MINUTES")
    mcp_oauth_refresh_token_days: int = Field(default=30, alias="MCP_OAUTH_REFRESH_TOKEN_DAYS")
    admin_password: str = Field(default="dev-admin-pass", alias="ADMIN_PASSWORD")
    admin_session_secret: str = Field(default="dev-admin-session-secret", alias="ADMIN_SESSION_SECRET")
    cors_origins: str = Field(default="http://localhost:3000", alias="CORS_ORIGINS")
    twilio_account_sid: str | None = Field(default=None, alias="TWILIO_ACCOUNT_SID")
    twilio_auth_token: str | None = Field(default=None, alias="TWILIO_AUTH_TOKEN")
    twilio_messaging_service_sid: str | None = Field(default=None, alias="TWILIO_MESSAGING_SERVICE_SID")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_database_url(cls, value: str) -> str:
        if value.startswith("postgresql://"):
            return value.replace("postgresql://", "postgresql+psycopg://", 1)
        return value

    @property
    def admin_cookie_secure(self) -> bool:
        return self.app_env == "production"

    @model_validator(mode="after")
    def validate_production_secrets(self) -> "Settings":
        if self.app_env == "production":
            insecure_values = {
                "dev-secret-change-me",
                "dev-mcp-token",
                "dev-admin-pass",
                "dev-admin-session-secret",
            }
            for name in ("jwt_secret", "mcp_bearer_token", "admin_password", "admin_session_secret"):
                if getattr(self, name) in insecure_values:
                    raise ValueError(f"{name.upper()} must be configured in production")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
