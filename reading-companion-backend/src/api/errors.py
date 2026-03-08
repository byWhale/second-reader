"""Centralized API error handling."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from src.api.schemas import ErrorResponse


class ApiError(Exception):
    """Structured API error mapped into the stable error envelope."""

    def __init__(
        self,
        *,
        status: int,
        code: str,
        message: str,
        retryable: bool = False,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.retryable = retryable
        self.details = details

    def to_response(self) -> ErrorResponse:
        """Convert the exception into the public error schema."""
        return ErrorResponse(
            error_id=uuid.uuid4().hex[:12],
            code=self.code,
            message=self.message,
            status=self.status,
            retryable=self.retryable,
            details=self.details,
        )


def error_response(
    *,
    status: int,
    code: str,
    message: str,
    retryable: bool = False,
    details: dict[str, Any] | None = None,
) -> JSONResponse:
    """Build a JSON error response matching the public schema."""
    payload = ErrorResponse(
        error_id=uuid.uuid4().hex[:12],
        code=code,
        message=message,
        status=status,
        retryable=retryable,
        details=details,
    )
    return JSONResponse(status_code=status, content=payload.model_dump())


def install_error_handlers(app: FastAPI) -> None:
    """Register global handlers that normalize all REST errors."""

    @app.exception_handler(ApiError)
    async def _handle_api_error(_request: Request, exc: ApiError) -> JSONResponse:
        payload = exc.to_response()
        return JSONResponse(status_code=payload.status, content=payload.model_dump())

    @app.exception_handler(RequestValidationError)
    async def _handle_validation_error(_request: Request, exc: RequestValidationError) -> JSONResponse:
        return error_response(
            status=422,
            code="VALIDATION_ERROR",
            message="Request validation failed.",
            retryable=False,
            details={"errors": exc.errors()},
        )

    @app.exception_handler(FileNotFoundError)
    async def _handle_file_not_found(_request: Request, exc: FileNotFoundError) -> JSONResponse:
        return error_response(
            status=404,
            code="INTERNAL_ERROR",
            message=str(exc) or "Requested file was not found.",
            retryable=False,
            details=None,
        )

    @app.exception_handler(Exception)
    async def _handle_unexpected_error(_request: Request, exc: Exception) -> JSONResponse:
        return error_response(
            status=500,
            code="INTERNAL_ERROR",
            message=str(exc) or "Unexpected server error.",
            retryable=False,
            details=None,
        )
