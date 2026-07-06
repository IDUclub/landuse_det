"""Auth configuration — Keycloak realm + verification toggles.

Mirrors the convention used across IDUclub services (PzzCompareAPI /
ChatStorage) so it is familiar. ``server_url`` points at the realm base, e.g.
``https://keycloak.../realms/<realm>``; JWKS and token endpoints are derived
from it.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in ("true", "1", "yes")


def _as_int(value: str | None, default: int) -> int:
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


@dataclass
class AuthConfig:
    """Authentication and token-validation settings."""

    verify: bool  # проверять ли подпись токена локально
    server_url: str  # https://.../realms/<realm>
    client_id: str = ""
    client_secret: str = ""
    verify_aud: bool = True
    valid_audiences: list[str] = field(default_factory=list)
    user_cache_ttl: int = 300  # TTL кеша пользователей (сек)
    user_cache_size: int = 10_000  # размер кеша пользователей
    jwks_cache_ttl: int = 600  # TTL кеша JWKS (сек)
    timeout: int = 5

    def __post_init__(self) -> None:
        if self.server_url and not self.server_url.startswith("http"):
            self.server_url = "http://" + self.server_url
        self.server_url = self.server_url.rstrip("/")

    @property
    def jwks_url(self) -> str:
        return f"{self.server_url}/protocol/openid-connect/certs"

    @property
    def token_url(self) -> str:
        return f"{self.server_url}/protocol/openid-connect/token"


def build_auth_config() -> AuthConfig:
    """Build an ``AuthConfig`` from environment variables.

    Reads ``os.environ`` directly (rather than idu-config's ``Config.get``,
    which raises on empty/optional values) so that unset AUTH_* vars fall back
    to sane defaults. The ``.env`` file must already be loaded by this point.
    """
    raw_aud = (os.getenv("AUTH_VALID_AUDIENCES") or "").strip()
    audiences = [a.strip() for a in raw_aud.split(",") if a.strip()]
    return AuthConfig(
        verify=_as_bool(os.getenv("AUTH_VERIFY"), default=False),
        server_url=os.getenv("AUTH_SERVER_URL") or "",
        client_id=os.getenv("AUTH_CLIENT_ID") or "",
        client_secret=os.getenv("AUTH_CLIENT_SECRET") or "",
        verify_aud=_as_bool(os.getenv("AUTH_VERIFY_AUD"), default=True),
        valid_audiences=audiences,
        user_cache_ttl=_as_int(os.getenv("AUTH_USER_CACHE_TTL"), 300),
        user_cache_size=_as_int(os.getenv("AUTH_USER_CACHE_SIZE"), 10_000),
        jwks_cache_ttl=_as_int(os.getenv("AUTH_JWKS_CACHE_TTL"), 600),
        timeout=_as_int(os.getenv("AUTH_TIMEOUT_SECONDS"), 5),
    )
