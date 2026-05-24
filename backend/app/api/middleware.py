"""Global API middleware helpers: exception handling and rate limiting."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import HTTPException as FastAPIHTTPException
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import settings


logger = logging.getLogger(__name__)
limiter = Limiter(key_func=get_remote_address)


def _json_http_error(_: Request, exc: FastAPIHTTPException | StarletteHTTPException) -> JSONResponse:
    """Return API errors in a consistent JSON envelope."""
    return JSONResponse(status_code=exc.status_code, content={"error": str(exc.detail)})


def _json_unhandled_error(_: Request, exc: Exception) -> JSONResponse:
    """Return unhandled exceptions as JSON and log full traceback."""
    logger.exception("Unhandled application error", exc_info=exc)

    detail: str | None = None
    if settings.ENVIRONMENT.lower() != "production":
        detail = str(exc)

    content: dict[str, Any] = {"error": "Internal server error"}
    if detail:
        content["detail"] = detail

    return JSONResponse(status_code=500, content=content)


def _json_rate_limit_error(_: Request, exc: RateLimitExceeded) -> JSONResponse:
    """Return rate-limit responses in JSON with Retry-After header."""
    retry_after = str(getattr(exc, "retry_after", 60))
    return JSONResponse(
        status_code=429,
        content={"error": str(exc.detail)},
        headers={"Retry-After": retry_after},
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register global exception handlers for API responses."""
    app.add_exception_handler(FastAPIHTTPException, _json_http_error)
    app.add_exception_handler(StarletteHTTPException, _json_http_error)
    app.add_exception_handler(RateLimitExceeded, _json_rate_limit_error)
    app.add_exception_handler(Exception, _json_unhandled_error)
