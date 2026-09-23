import logging

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import get_settings
from app.schemas.errors import ErrorBody, ErrorResponse

logger = logging.getLogger(__name__)


def _error(status_code: int, code: str, message: str, details: object | None = None) -> JSONResponse:
    payload = ErrorResponse(error=ErrorBody(code=code, message=message, details=details))
    return JSONResponse(status_code=status_code, content=jsonable_encoder(payload.model_dump()))



def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
        return _error(
            status_code=exc.status_code,
            code="http_error",
            message=str(exc.detail),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        _request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return _error(
            status_code=422,
            code="validation_error",
            message="Request validation failed",
            details=exc.errors(),
        )

    @app.exception_handler(SQLAlchemyError)
    async def sqlalchemy_exception_handler(_request: Request, exc: SQLAlchemyError) -> JSONResponse:
        logger.exception("Database error: %s", exc)
        details = str(exc) if get_settings().debug else None
        return _error(
            status_code=500,
            code="database_error",
            message="A database error occurred",
            details=details,
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error: %s", exc)
        details = str(exc) if get_settings().debug else None
        return _error(
            status_code=500,
            code="internal_error",
            message="An unexpected error occurred",
            details=details,
        )
