"""Duck Chat — unified error handling.

All API errors follow the format:
  {"error": {"code": "ERROR_CODE", "message": "Human-readable description"}}
"""

import logging
from fastapi import Request
from fastapi.responses import JSONResponse

logger = logging.getLogger("myapi.errors")


class AppError(Exception):
    """Base application error with structured payload."""

    def __init__(self, code: str, message: str, status_code: int = 400, detail: str | None = None):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.detail = detail
        super().__init__(message)

    def to_dict(self) -> dict:
        d = {"code": self.code, "message": self.message}
        if self.detail:
            d["detail"] = self.detail
        return {"error": d}

    @classmethod
    def not_found(cls, msg: str = "Resource not found", detail: str | None = None) -> "AppError":
        return cls("NOT_FOUND", msg, 404, detail)

    @classmethod
    def bad_request(cls, msg: str = "Bad request", detail: str | None = None) -> "AppError":
        return cls("BAD_REQUEST", msg, 400, detail)

    @classmethod
    def unauthorized(cls, msg: str = "Unauthorized", detail: str | None = None) -> "AppError":
        return cls("UNAUTHORIZED", msg, 401, detail)

    @classmethod
    def forbidden(cls, msg: str = "Forbidden", detail: str | None = None) -> "AppError":
        return cls("FORBIDDEN", msg, 403, detail)

    @classmethod
    def rate_limited(cls, msg: str = "Rate limited", detail: str | None = None) -> "AppError":
        return cls("RATE_LIMITED", msg, 429, detail)

    @classmethod
    def service_unavailable(cls, msg: str = "Service unavailable", detail: str | None = None) -> "AppError":
        return cls("SERVICE_UNAVAILABLE", msg, 503, detail)

    @classmethod
    def internal(cls, msg: str = "Internal error", detail: str | None = None) -> "AppError":
        return cls("INTERNAL_ERROR", msg, 500, detail)


def error_response(code: str, message: str, status_code: int = 400, detail: str | None = None) -> JSONResponse:
    """Build a structured JSON error response."""
    d: dict = {"error": {"code": code, "message": message}}
    if detail:
        d["error"]["detail"] = detail
    return JSONResponse(d, status_code=status_code)


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    """FastAPI exception handler for AppError."""
    return JSONResponse(exc.to_dict(), status_code=exc.status_code)


async def generic_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all for unhandled exceptions."""
    logger.exception("Unhandled exception: %s", exc)
    return JSONResponse(
        {"error": {"code": "INTERNAL_ERROR", "message": "Internal server error"}},
        status_code=500,
    )
