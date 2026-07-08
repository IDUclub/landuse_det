from contextvars import ContextVar, Token

_current_bearer_token: ContextVar[str | None] = ContextVar(
    "current_bearer_token",
    default=None,
)


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
