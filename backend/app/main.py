from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.exception_handlers import register_exception_handlers
from app.api.routes.conversations import router as conversations_router
from app.api.routes.health import router as health_router
from app.config import get_settings
from app.db.session import init_db


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    init_db()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        lifespan=lifespan,
    )

    # Configure CORS for local development (e.g. Vite on 5173, React on 3000)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(application)

    # Register API routers with versioned and unversioned /api prefixes
    application.include_router(health_router, prefix="/api/v1")
    application.include_router(health_router, prefix="/api")
    application.include_router(conversations_router, prefix="/api/v1")
    application.include_router(conversations_router, prefix="/api")

    return application



app = create_app()
