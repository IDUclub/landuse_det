"""FastAPI authentication client is defined here."""

import json
from base64 import b64decode
from datetime import datetime

import httpx
from cachetools import TTLCache
from fastapi import Request

from landuse_api.dto import UserDTO


class AuthenticationClient:

    def __init__(self, cache_size: int, cache_ttl: int, validate_token: int, auth_url: str):
        self._validate_token = validate_token
        self._auth_url = auth_url
        self._cache = TTLCache(maxsize=cache_size, ttl=cache_ttl)

    @staticmethod
    def decode_token(token: str) -> dict:
        """Decode the JWT token without verification to extract payload."""
        try:
            return json.loads(b64decode(token.split(".")[1]))
        except Exception as exc:
            raise JWTDecodeError(token) from exc

    @staticmethod
    def is_token_expired(payload: dict) -> bool:
        """Check if the JWT token is expired."""
        if "exp" in payload:
            expiration = datetime.utcfromtimestamp(payload["exp"])
            return expiration < datetime.utcnow()
        return False

    def update(
        self,
        cache_size: int | None = None,
        cache_ttl: int | None = None,
        validate_token: int | None = None,
        auth_url: str | None = None,
    ) -> None:
        self._validate_token = validate_token or self._validate_token
        self._auth_url = auth_url or self._auth_url
        self._cache = (
            TTLCache(maxsize=cache_size, ttl=cache_ttl)
            if cache_size is not None and cache_ttl is not None
            else self._cache
        )

    async def validate_token_online(self, token: str) -> None:
        """Validate token by calling an external service if needed."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(self._auth_url, headers={"Authorization": f"Bearer {token}"})
            if response.status_code != 200:
                raise InvalidTokenSignature(token)
        except Exception as exc:
            raise AuthServiceUnavailable() from exc

    async def get_user_from_token(self, token: str) -> UserDTO:
        """Main method that processes the token and returns UserDTO."""

        cached_user = self._cache.get(token)
        if cached_user:
            return cached_user

        payload = self.decode_token(token)

        # Optionally validate the token online
        if self._validate_token:
            if self.is_token_expired(payload):
                raise ExpiredToken(token)
            await self.validate_token_online(token)

        user_dto = UserDTO(id=payload.get("sub"), is_active=payload.get("active"))

        self._cache[token] = user_dto

        return user_dto


def get_user(request: Request):
    return request.state.user if hasattr(request.state, "user") else None
