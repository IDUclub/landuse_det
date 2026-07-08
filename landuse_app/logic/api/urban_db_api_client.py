import logging

import aiohttp
from fastapi import HTTPException
from idu_service_auth import KeycloakTokenClient, KeycloakTokenConfig
from iduconfig import Config

from landuse_app.auth_context import get_current_bearer_token

logger = logging.getLogger(__name__)


class AuthService:
    """Service-to-service authentication against Keycloak.

    Uses the OAuth2 *client credentials* grant (service token) via
    :class:`idu_service_auth.KeycloakTokenClient`. The client is created once and
    kept for the whole application lifecycle; it caches the token and refreshes it
    transparently before expiry.
    """

    def __init__(self, iduconfig: Config):
        self.iduconfig = iduconfig
        auth_server_url = iduconfig.get("KEYCLOAK_URL")
        realm = iduconfig.get("KEYCLOAK_REALM")
        client_id = iduconfig.get("KEYCLOAK_CLIENT_ID")
        client_secret = iduconfig.get("KEYCLOAK_CLIENT_SECRET")

        missing = [
            name
            for name, value in (
                ("KEYCLOAK_URL", auth_server_url),
                ("KEYCLOAK_REALM", realm),
                ("KEYCLOAK_CLIENT_ID", client_id),
                ("KEYCLOAK_CLIENT_SECRET", client_secret),
            )
            if not value
        ]
        if missing:
            raise HTTPException(
                500,
                f"Missing Keycloak service credentials in config: {', '.join(missing)}",
            )

        self._client = KeycloakTokenClient(
            KeycloakTokenConfig(
                auth_server_url=auth_server_url,
                realm=realm,
                client_id=client_id,
                client_secret=client_secret,
            )
        )

    async def get_token(self) -> str:
        """Return a valid service access token, refreshing it if needed."""
        return await self._client.get_access_token()

    async def aclose(self) -> None:
        """Release the underlying HTTP session. Call on application shutdown."""
        await self._client.aclose()


class RequestHandler:
    def __init__(self, api_base: str, auth_service: AuthService, cache_service=None):
        self.url = api_base
        self.auth = auth_service
        self.cache = cache_service

    async def _prepare_headers(
        self,
        *,
        extra_headers: dict[str, str] | None = None,
        use_token: bool = True,
        override_token: str | None = None,
    ) -> dict:
        headers = dict(extra_headers) if extra_headers else {}
        if not use_token:
            return headers

        token = override_token or get_current_bearer_token()
        if token is None:
            token = await self.auth.get_token()

        headers["Authorization"] = f"Bearer {token}"
        return headers

    async def get(
        self, path: str, params: dict = None, ignore_404: bool = False
    ) -> dict | None:
        request_bearer_token = get_current_bearer_token()
        headers = await self._prepare_headers()
        cache = self.cache if request_bearer_token is None else None
        key = path.strip("/").replace("/", "_")
        if cache:
            recent = cache.get_recent_cache_file(key, params or {})
            if recent and cache.is_cache_valid(recent):
                logger.info("Using cache for %s", path)
                return cache.load_cache(recent)

        url = f"{self.url}{path}"
        async with aiohttp.ClientSession() as sess:
            async with sess.get(url, params=params, headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if cache:
                        cache.save_with_cleanup(data, key, params or {})
                    return data
                if ignore_404 and resp.status == 404:
                    return None
                text = await resp.text()
                logger.error("GET %s failed: %s", path, text)
                raise HTTPException(resp.status, f"Urban API GET error: {text}")

    async def put(
        self,
        path: str,
        data: dict | None = None,
        *,
        extra_headers: dict[str, str] | None = None,
        use_token: bool = True,
        override_token: str | None = None,
    ) -> dict:
        """
        Async PUT-request.
        - extra_headers – any additional headers
        - use_token, override_token – default logic from AuthService
        """
        headers = await self._prepare_headers(
            extra_headers=extra_headers,
            use_token=use_token,
            override_token=override_token,
        )

        url = f"{self.url}{path}"
        async with aiohttp.ClientSession() as sess:
            async with sess.put(url, json=data, headers=headers) as resp:
                if resp.status in (200, 201):
                    return await resp.json()
                text = await resp.text()
                logger.error("PUT %s failed: %s", path, text)
                raise HTTPException(resp.status, f"Urban API PUT error: {text}")
