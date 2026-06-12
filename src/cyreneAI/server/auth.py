from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import time

from fastapi import Request, Response
from fastapi.security import HTTPBasicCredentials

from cyreneAI.core.errors.base import AuthorizationError, ConfigurationError
from cyreneAI.server.config import ServerSettings
from cyreneAI.server.errors import raise_http_error

_BASIC_AUTH_HEADERS = {"WWW-Authenticate": "Basic"}


def verify_admin_password(
    *,
    username: str,
    password: str,
    settings: ServerSettings,
) -> None:
    if not settings.auth_enabled:
        return
    if not settings.admin_username or not settings.admin_password:
        raise_http_error(ConfigurationError("Admin auth is not configured"))

    username_matches = secrets.compare_digest(username, settings.admin_username)
    password_matches = secrets.compare_digest(password, settings.admin_password)
    if not username_matches or not password_matches:
        raise_http_error(
            AuthorizationError("Invalid admin credentials"),
            headers=_BASIC_AUTH_HEADERS,
        )


def verify_admin_credentials(
    credentials: HTTPBasicCredentials | None,
    settings: ServerSettings,
) -> None:
    if not settings.auth_enabled:
        return
    if credentials is None:
        raise_http_error(
            AuthorizationError("Admin credentials are required"),
            headers=_BASIC_AUTH_HEADERS,
        )
    verify_admin_password(
        username=credentials.username,
        password=credentials.password,
        settings=settings,
    )


def verify_admin_session(request: Request, settings: ServerSettings) -> bool:
    if not settings.auth_enabled:
        return True

    token = request.cookies.get(settings.session_cookie_name)
    if not token:
        return False
    payload = _decode_session_token(token, settings)
    if payload is None:
        return False
    username, expires_at = payload
    if expires_at < int(time.time()):
        return False
    if not settings.admin_username:
        return False
    return secrets.compare_digest(username, settings.admin_username)


def set_admin_session_cookie(response: Response, settings: ServerSettings) -> None:
    if not settings.auth_enabled:
        return
    if not settings.admin_username:
        raise_http_error(ConfigurationError("Admin auth is not configured"))
    expires_at = int(time.time()) + settings.session_ttl_seconds
    token = _encode_session_token(settings.admin_username, expires_at, settings)
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        max_age=settings.session_ttl_seconds,
        httponly=True,
        samesite="lax",
    )


def clear_admin_session_cookie(response: Response, settings: ServerSettings) -> None:
    response.delete_cookie(settings.session_cookie_name)


def _encode_session_token(
    username: str,
    expires_at: int,
    settings: ServerSettings,
) -> str:
    payload = f"{username}:{expires_at}"
    signature = _session_signature(payload, settings)
    raw = f"{payload}:{signature}".encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii")


def _decode_session_token(
    token: str,
    settings: ServerSettings,
) -> tuple[str, int] | None:
    try:
        raw = base64.urlsafe_b64decode(token.encode("ascii")).decode("utf-8")
        username, expires_at_text, signature = raw.rsplit(":", maxsplit=2)
        expires_at = int(expires_at_text)
    except (ValueError, UnicodeDecodeError):
        return None

    payload = f"{username}:{expires_at}"
    expected_signature = _session_signature(payload, settings)
    if not secrets.compare_digest(signature, expected_signature):
        return None
    return username, expires_at


def _session_signature(payload: str, settings: ServerSettings) -> str:
    secret = (
        settings.session_secret
        or settings.admin_password
        or "cyrene-admin-session-development-secret"
    )
    return hmac.new(
        secret.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
