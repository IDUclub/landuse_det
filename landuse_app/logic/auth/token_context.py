"""Per-request bearer-token storage.

The frontend sends ``Authorization: Bearer <jwt>`` on every scenario request.
Rather than thread the token through every service method signature (the call
chain is controller -> renovation_potential -> preprocessing -> urban_api_access
-> RequestHandler), we stash it in a ``ContextVar`` that the ``verify_token``
dependency sets per request and ``RequestHandler`` reads when building headers.

Each HTTP request runs in its own asyncio Task with a copied context, so the
value never leaks across requests. Tasks spawned within a request (e.g.
``asyncio.gather``) inherit the value automatically.
"""
from __future__ import annotations

from contextvars import ContextVar, Token

_current_token: ContextVar[str | None] = ContextVar("current_bearer_token", default=None)


def set_current_token(token: str | None) -> Token:
    """Store the bearer token for the current request context."""
    return _current_token.set(token)


def get_current_token() -> str | None:
    """Return the bearer token for the current request, or ``None`` (e.g. Kafka path)."""
    return _current_token.get()


def reset_current_token(token: Token) -> None:
    """Restore the previous context value (used by dependency teardown)."""
    _current_token.reset(token)
