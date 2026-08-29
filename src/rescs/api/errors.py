"""Consistent API error responses."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from rescs.errors import RESCSError


def _loc_to_string(loc: list) -> str:
    return ".".join(str(part) for part in loc)


def _validation_detail(exc: RequestValidationError) -> list[dict]:
    detail = []
    for error in exc.errors():
        detail.append(
            {
                "loc": _loc_to_string(error.get("loc", [])),
                "message": error.get("msg"),
                "type": error.get("type"),
            }
        )
    return detail


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(RESCSError)
    async def _rescs_error_handler(_request: Request, exc: RESCSError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.to_dict()},
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_error_handler(
        _request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "request validation failed",
                    "details": {"errors": _validation_detail(exc)},
                }
            },
        )