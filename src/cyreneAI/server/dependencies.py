from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from cyreneAI.application.runtime import CyreneAIRuntime
from cyreneAI.core.errors.base import StateError
from cyreneAI.server.auth import verify_admin_credentials, verify_admin_session
from cyreneAI.server.config import ServerSettings
from cyreneAI.server.errors import raise_http_error

_admin_basic = HTTPBasic(auto_error=False)


def get_runtime(request: Request) -> CyreneAIRuntime:
    runtime = request.app.state.runtime
    if runtime is None:
        raise_http_error(StateError("Runtime is not ready"))
    return runtime


def get_server_settings(request: Request) -> ServerSettings:
    return request.app.state.server_settings


def require_admin(
    request: Request,
    credentials: Annotated[HTTPBasicCredentials | None, Depends(_admin_basic)],
    settings: ServerSettings = Depends(get_server_settings),
) -> None:
    if verify_admin_session(request, settings):
        return
    verify_admin_credentials(credentials, settings)
