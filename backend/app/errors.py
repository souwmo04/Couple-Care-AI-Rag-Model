"""Structured application errors.

Every error that reaches the client has the shape::

    {"error": {"code": "model_offline", "message": "...", "retryable": true}}

Messages are written for end users and never include stack traces, file paths, or the
user's own message text.
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class AppError(Exception):
    status_code = 500
    code = "internal_error"
    retryable = False

    def __init__(self, message: str, *, code: str | None = None, status_code: int | None = None,
                 retryable: bool | None = None) -> None:
        super().__init__(message)
        self.message = message
        if code is not None:
            self.code = code
        if status_code is not None:
            self.status_code = status_code
        if retryable is not None:
            self.retryable = retryable


class NotFoundError(AppError):
    status_code = 404
    code = "not_found"


class ConflictError(AppError):
    status_code = 409
    code = "conflict"


class BadRequestError(AppError):
    status_code = 400
    code = "bad_request"


class ModelOfflineError(AppError):
    status_code = 503
    code = "model_offline"
    retryable = True


class ModelTimeoutError(AppError):
    status_code = 504
    code = "model_timeout"
    retryable = True


class ModelResponseError(AppError):
    status_code = 502
    code = "model_error"
    retryable = True


class IndexUnavailableError(AppError):
    status_code = 503
    code = "index_unavailable"
    retryable = True


def error_body(code: str, message: str, retryable: bool = False, details: object | None = None) -> dict:
    body: dict = {"error": {"code": code, "message": message, "retryable": retryable}}
    if details is not None:
        body["error"]["details"] = details
    return body


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(error_body(exc.code, exc.message, exc.retryable), status_code=exc.status_code)

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        # Echo field locations and messages, never the submitted values (they may be private).
        details = [
            {"field": ".".join(str(p) for p in err.get("loc", ()) if p != "body"), "message": err.get("msg", "")}
            for err in exc.errors()
        ]
        return JSONResponse(
            error_body("validation_error", "Some of the submitted values are not valid.", details=details),
            status_code=422,
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = {404: "not_found", 405: "method_not_allowed", 413: "payload_too_large"}.get(exc.status_code, "http_error")
        return JSONResponse(error_body(code, str(exc.detail)), status_code=exc.status_code)

    @app.exception_handler(Exception)
    async def _unhandled(_: Request, exc: Exception) -> JSONResponse:  # pragma: no cover - defensive
        import logging

        logging.getLogger("couplecare").exception("unhandled_error", extra={"error_type": type(exc).__name__})
        return JSONResponse(error_body("internal_error", "Something went wrong on the local server."), status_code=500)
