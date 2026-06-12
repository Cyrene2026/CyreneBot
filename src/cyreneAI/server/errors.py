from __future__ import annotations

from typing import Mapping, NoReturn

from fastapi import HTTPException, status

from cyreneAI.core.errors.base import (
    AuthorizationError,
    ConfigurationError,
    ConflictError,
    CyreneAIError,
    DependencyError,
    NotFoundError,
    RateLimitError,
    RequestError,
    RequestTimeoutError,
    ResponseError,
    StateError,
    UnavailableError,
    UnsupportedError,
    ValidationError,
)
from cyreneAI.core.errors.plugin import PluginError
from cyreneAI.core.errors.provider import ProviderError


def http_status_for_error(exc: CyreneAIError) -> int:
    if isinstance(exc, NotFoundError):
        return status.HTTP_404_NOT_FOUND
    if isinstance(exc, ConflictError):
        return status.HTTP_409_CONFLICT
    if isinstance(exc, RateLimitError):
        return status.HTTP_429_TOO_MANY_REQUESTS
    if isinstance(exc, RequestTimeoutError):
        return status.HTTP_504_GATEWAY_TIMEOUT
    if isinstance(exc, AuthorizationError):
        return status.HTTP_401_UNAUTHORIZED
    if isinstance(exc, StateError) and _looks_not_configured(exc):
        return status.HTTP_503_SERVICE_UNAVAILABLE
    if isinstance(exc, StateError):
        return status.HTTP_409_CONFLICT
    if isinstance(exc, ValidationError | UnsupportedError):
        return 422
    if isinstance(exc, RequestError):
        return status.HTTP_400_BAD_REQUEST
    if isinstance(exc, ResponseError):
        return status.HTTP_502_BAD_GATEWAY
    if isinstance(exc, DependencyError | UnavailableError):
        return status.HTTP_503_SERVICE_UNAVAILABLE
    if isinstance(exc, ProviderError | PluginError):
        return 422
    if isinstance(exc, ConfigurationError):
        return status.HTTP_503_SERVICE_UNAVAILABLE
    return status.HTTP_400_BAD_REQUEST


def raise_http_error(
    exc: CyreneAIError,
    *,
    status_code: int | None = None,
    headers: Mapping[str, str] | None = None,
) -> NoReturn:
    raise HTTPException(
        status_code=status_code or http_status_for_error(exc),
        detail=str(exc),
        headers=dict(headers) if headers is not None else None,
    ) from exc


def _looks_not_configured(exc: CyreneAIError) -> bool:
    return "not configured" in str(exc).casefold()


__all__ = ["http_status_for_error", "raise_http_error"]
