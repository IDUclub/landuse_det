"""Keycloak service-account token provider (client_credentials grant).

Used by the non-request (Kafka) path, where there is no frontend token to
forward. Obtains an access token from Keycloak using ``client_id`` +
``client_secret`` and caches it until shortly before expiry.
"""
from __future__ import annotations

import asyncio
import logging
import time

import aiohttp

from .auth_config import AuthConfig
from .exceptions import ServiceTokenError

logger = logging.getLogger("landuse_app.auth")

# refresh the token this many seconds before it actually expires
_EXPIRY_SKEW = 30


class ServiceTokenProvider:
    """Fetch and cache a Keycloak service-account access token."""

    def __init__(self, config: AuthConfig) -> None:
        self.config = config
        self._token: str | None = None
        self._expires_at: float = 0.0
        self._lock = asyncio.Lock()

    def _is_valid(self) -> bool:
        return self._token is not None and time.time() < self._expires_at - _EXPIRY_SKEW

    async def get_token(self) -> str:
        """Return a valid service token, fetching a new one when needed."""
        if self._is_valid():
            return self._token  # type: ignore[return-value]
        async with self._lock:
            if self._is_valid():
                return self._token  # type: ignore[return-value]
            return await self._request_token()

    async def _request_token(self) -> str:
        if not self.config.client_id or not self.config.client_secret:
            raise ServiceTokenError(
                "AUTH_CLIENT_ID / AUTH_CLIENT_SECRET are not configured; "
                "cannot obtain a service token for the Kafka path"
            )

        payload = {
            "grant_type": "client_credentials",
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
        }
        headers = {
            "accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        timeout = aiohttp.ClientTimeout(total=self.config.timeout)
        async with aiohttp.ClientSession(timeout=timeout) as sess:
            async with sess.post(
                self.config.token_url, data=payload, headers=headers
            ) as resp:
                text = await resp.text()
                if resp.status != 200:
                    logger.error(
                        "Service token request failed %s: %s", resp.status, text
                    )
                    raise ServiceTokenError(f"Keycloak returned {resp.status}: {text}")
                data = await resp.json()

        self._token = data["access_token"]
        self._expires_at = time.time() + int(data.get("expires_in", 60))
        logger.info(
            "Service token obtained (expires_in=%s)", data.get("expires_in")
        )
        return self._token
