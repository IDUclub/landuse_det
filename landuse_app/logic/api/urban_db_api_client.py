import asyncio
import logging

import aiohttp
from fastapi import HTTPException

from landuse_app.logic.auth.service_token import ServiceTokenProvider
from landuse_app.logic.auth.token_context import get_current_token

logger = logging.getLogger(__name__)

# network errors worth retrying (upstream reset the connection / timed out)
_RETRYABLE_ERRORS = (
    aiohttp.ServerDisconnectedError,
    aiohttp.ClientConnectorError,
    aiohttp.ClientOSError,
    aiohttp.ClientPayloadError,
    asyncio.TimeoutError,
)


class RequestHandler:
    """Async HTTP client for urban_api.

    The bearer token is resolved per call:
      1. the frontend token stored in the request context (HTTP path), or
      2. a Keycloak service-account token (Kafka / background path).

    Requests use an explicit timeout and retry transient network failures
    (e.g. ``Connection reset by peer``) before surfacing a 502.
    """

    def __init__(
        self,
        api_base: str,
        service_token_provider: ServiceTokenProvider,
        cache_service=None,
        *,
        timeout_seconds: int = 120,
        retries: int = 3,
    ):
        self.url = api_base
        self.service_token = service_token_provider
        self.cache = cache_service
        self.timeout = aiohttp.ClientTimeout(total=timeout_seconds)
        self.retries = retries

    async def _resolve_token(self) -> str | None:
        """Frontend token (request context) or a Keycloak service token."""
        token = get_current_token()
        if token:
            return token
        # no request-scoped token -> background/Kafka path, use service account
        return await self.service_token.get_token()

    async def _prepare_headers(self) -> dict:
        headers: dict[str, str] = {}
        token = await self._resolve_token()
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    async def get(
        self, path: str, params: dict = None, ignore_404: bool = False
    ) -> dict | None:
        headers = await self._prepare_headers()
        key = path.strip("/").replace("/", "_")
        if self.cache:
            recent = self.cache.get_recent_cache_file(key, params or {})
            if recent and self.cache.is_cache_valid(recent):
                logger.info("Using cache for %s", path)
                return self.cache.load_cache(recent)

        url = f"{self.url}{path}"
        last_exc: Exception | None = None
        for attempt in range(self.retries):
            try:
                async with aiohttp.ClientSession(timeout=self.timeout) as sess:
                    async with sess.get(
                        url, params=params, headers=headers
                    ) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            if self.cache:
                                self.cache.save_with_cleanup(data, key, params or {})
                            return data
                        if ignore_404 and resp.status == 404:
                            return None
                        text = await resp.text()
                        logger.error("GET %s failed: %s", path, text)
                        raise HTTPException(
                            resp.status, f"Urban API GET error: {text}"
                        )
            except _RETRYABLE_ERRORS as exc:
                last_exc = exc
                logger.warning(
                    "GET %s network error (attempt %s/%s): %s",
                    path,
                    attempt + 1,
                    self.retries,
                    exc,
                )
                await asyncio.sleep(1)

        logger.error("GET %s failed after %s attempts: %s", path, self.retries, last_exc)
        raise HTTPException(
            502, f"Urban API unavailable: {last_exc}"
        )

    async def put(
        self,
        path: str,
        data: dict | None = None,
        *,
        extra_headers: dict[str, str] | None = None,
        override_token: str | None = None,
    ) -> dict:
        """
        Async PUT-request.
        - extra_headers – any additional headers
        - override_token – use this token instead of the resolved one
        """
        headers = dict(extra_headers) if extra_headers else {}

        token = override_token or await self._resolve_token()
        if token:
            headers["Authorization"] = f"Bearer {token}"

        url = f"{self.url}{path}"
        last_exc: Exception | None = None
        for attempt in range(self.retries):
            try:
                async with aiohttp.ClientSession(timeout=self.timeout) as sess:
                    async with sess.put(url, json=data, headers=headers) as resp:
                        if resp.status in (200, 201):
                            return await resp.json()
                        text = await resp.text()
                        logger.error("PUT %s failed: %s", path, text)
                        raise HTTPException(
                            resp.status, f"Urban API PUT error: {text}"
                        )
            except _RETRYABLE_ERRORS as exc:
                last_exc = exc
                logger.warning(
                    "PUT %s network error (attempt %s/%s): %s",
                    path,
                    attempt + 1,
                    self.retries,
                    exc,
                )
                await asyncio.sleep(1)

        logger.error("PUT %s failed after %s attempts: %s", path, self.retries, last_exc)
        raise HTTPException(502, f"Urban API unavailable: {last_exc}")
