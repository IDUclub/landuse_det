from contextlib import contextmanager
from contextvars import ContextVar, Token
from typing import Iterator

_current_bearer_token: ContextVar[str | None] = ContextVar(
    "current_bearer_token",
    default=None,
)

_service_scope: ContextVar[bool] = ContextVar("service_scope", default=False)


def extract_bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer":
        return None

    token = token.strip()
    return token or None


def get_current_bearer_token() -> str | None:
    return _current_bearer_token.get()


def set_current_bearer_token(token: str | None) -> Token[str | None]:
    return _current_bearer_token.set(token)


def reset_current_bearer_token(token: Token[str | None]) -> None:
    _current_bearer_token.reset(token)


def in_service_scope() -> bool:
    return _service_scope.get()


@contextmanager
def service_scope() -> Iterator[None]:
    """
    Background (Kafka) processing scope: requests to Urban API are made with the
    Keycloak service token and bypass the file cache, so indicators are always
    recalculated from fresh data.
    """
    bearer_marker = _current_bearer_token.set(None)
    scope_marker = _service_scope.set(True)
    try:
        yield
    finally:
        _service_scope.reset(scope_marker)
        _current_bearer_token.reset(bearer_marker)
