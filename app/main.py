from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.core.config import settings
from app.core.errors import AppError
from app.core.logger import get_logger, setup_logging
from app.db.migrations import init_db

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Prepare application resources during startup and shutdown."""
    logger.info("Application startup")
    init_db()
    yield
    logger.info("Application shutdown")


async def _handle_app_error(request: Request, exc: Exception) -> JSONResponse:
    """Build a response for controlled application errors."""
    if not isinstance(exc, AppError):
        return await _handle_unexpected_error(request, exc)

    logger.warning(
        "Application error handled: path=%s module=%s code=%s details=%s",
        request.url.path,
        exc.module,
        exc.error_code,
        exc.details,
    )
    return JSONResponse(status_code=exc.status_code, content=exc.to_response())


async def _handle_validation_error(request: Request, exc: Exception) -> JSONResponse:
    """Build a consistent response for request validation errors."""
    if not isinstance(exc, RequestValidationError):
        return await _handle_unexpected_error(request, exc)

    logger.warning("Request validation failed: path=%s", request.url.path)
    return JSONResponse(
        status_code=422,
        content={
            "detail": "Request validation failed",
            "error_code": "request_validation_error",
            "module": "api",
            "details": {"errors": jsonable_encoder(exc.errors())},
        },
    )


async def _handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    """Return a safe response for unexpected exceptions."""
    logger.exception("Unhandled error on path %s: %s", request.url.path, exc)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "error_code": "internal_server_error",
            "module": "core",
        },
    )


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    setup_logging()

    application = FastAPI(
        title="English Interview Coach API",
        description=(
            "API for technical video ingestion and IT English interview practice."
        ),
        lifespan=lifespan,
    )

    application.add_exception_handler(AppError, _handle_app_error)
    application.add_exception_handler(RequestValidationError, _handle_validation_error)
    application.add_exception_handler(Exception, _handle_unexpected_error)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    application.include_router(api_router, prefix="/api/v1")
    application.include_router(api_router)
    return application


app = create_app()
