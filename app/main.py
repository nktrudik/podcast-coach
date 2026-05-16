from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.core.errors import AppError
from app.core.logger import get_logger, setup_logging
from app.db.migrations import init_db

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Подготавливает ресурсы приложения при старте и завершении."""
    logger.info("Запуск приложения")
    init_db()
    yield
    logger.info("Остановка приложения")


async def _handle_app_error(request: Request, exc: AppError) -> JSONResponse:
    """Формирует ответ для контролируемых ошибок приложения."""
    logger.warning(
        "Обработана ошибка приложения: path=%s module=%s code=%s details=%s",
        request.url.path,
        exc.module,
        exc.error_code,
        exc.details,
    )
    return JSONResponse(status_code=exc.status_code, content=exc.to_response())


async def _handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Формирует единый ответ при ошибке валидации входных данных."""
    logger.warning("Ошибка валидации запроса: path=%s", request.url.path)
    return JSONResponse(
        status_code=422,
        content={
            "detail": "Ошибка валидации данных запроса",
            "error_code": "request_validation_error",
            "module": "api",
            "details": {"errors": exc.errors()},
        },
    )


async def _handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    """Возвращает безопасный ответ для необработанных исключений."""
    logger.exception("Необработанная ошибка в пути %s: %s", request.url.path, exc)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Внутренняя ошибка сервера",
            "error_code": "internal_server_error",
            "module": "core",
        },
    )


def create_app() -> FastAPI:
    """Создает и настраивает экземпляр FastAPI приложения."""
    setup_logging()

    application = FastAPI(
        title="English Interview Coach API",
        description="API for technical video ingestion and IT English interview practice.",
        lifespan=lifespan,
    )

    application.add_exception_handler(AppError, _handle_app_error)
    application.add_exception_handler(RequestValidationError, _handle_validation_error)
    application.add_exception_handler(Exception, _handle_unexpected_error)

    application.include_router(api_router)
    return application


app = create_app()
