from __future__ import annotations

import logging
import time
import uuid
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request
from starlette.responses import Response

from cyreneAI.server.logging_config import bind_log_context

logger = logging.getLogger("cyreneAI.server.requests")

DEFAULT_REQUEST_ID_HEADER = "X-Request-ID"


def install_request_logging_middleware(
    app: FastAPI,
    *,
    enabled: bool = True,
    request_id_header: str = DEFAULT_REQUEST_ID_HEADER,
) -> None:
    """
    Attach request id propagation and request completion logging.
    """
    if not enabled:
        return

    header_name = request_id_header.strip() or DEFAULT_REQUEST_ID_HEADER

    @app.middleware("http")
    async def request_logging_middleware(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request_id = _request_id(request, header_name=header_name)
        started = time.perf_counter()
        with bind_log_context(
            request_id=request_id,
            http_method=request.method,
            http_path=request.url.path,
            client_ip=_client_ip(request),
        ):
            try:
                response = await call_next(request)
            except Exception:
                logger.exception(
                    "HTTP request failed",
                    extra={
                        "duration_ms": _duration_ms(started),
                    },
                )
                raise
            response.headers[header_name] = request_id
            logger.info(
                "HTTP request completed",
                extra={
                    "status_code": response.status_code,
                    "duration_ms": _duration_ms(started),
                },
            )
            return response


def _request_id(request: Request, *, header_name: str) -> str:
    value = request.headers.get(header_name)
    if value is not None:
        request_id = value.strip()
        if request_id:
            return request_id
    return uuid.uuid4().hex


def _client_ip(request: Request) -> str | None:
    if request.client is None:
        return None
    return request.client.host


def _duration_ms(started: float) -> int:
    return int((time.perf_counter() - started) * 1000)


__all__ = [
    "DEFAULT_REQUEST_ID_HEADER",
    "install_request_logging_middleware",
]
