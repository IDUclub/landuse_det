"""Bearer-token extraction + verification dependency for the API layer.

The frontend sends ``Authorization: Bearer <jwt>``. This dependency extracts
the token, optionally verifies it against the Keycloak realm JWKS (when
``AUTH_VERIFY`` is true), stashes it in the request-scoped context var so the
downstream urban_api calls forward it, and returns it to the endpoint.
"""
from __future__ import annotations

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .exceptions import AuthError
from .token_context import set_current_token

http_bearer = HTTPBearer(auto_error=True)


def _get_token_from_header(credentials: HTTPAuthorizationCredentials) -> str:
    if not credentials:
        raise HTTPException(status_code=401, detail="Authorization header missing")
    token = credentials.credentials
    if not token:
        raise HTTPException(
            status_code=400,
            detail="Token is missing in the authorization header",
        )
    return token


async def verify_token(
    credentials: HTTPAuthorizationCredentials = Depends(http_bearer),
) -> str:
    """Extract the Bearer token, verify it when enabled, and store it for forwarding.

    When ``AUTH_VERIFY`` is false the token is accepted as-is (urban_api
    validates it downstream). When true, the signature + claims are checked
    against the realm JWKS; a rejected token yields 401 so the caller can
    refresh it.
    """
    # imported lazily to avoid an import cycle with dependencies.py
    from landuse_app.dependencies import auth_client

    token = _get_token_from_header(credentials)
    if auth_client.config.verify:
        try:
            await auth_client.get_user_from_token(token)
        except AuthError as exc:
            raise HTTPException(status_code=401, detail=exc.detail) from exc

    set_current_token(token)
    return token
