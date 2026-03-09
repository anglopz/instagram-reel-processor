from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.container import init_container
from src.domain.exceptions import DomainException
from src.presentation.api.v1.auth import router as auth_router
from src.presentation.api.v1.health import router as health_router
from src.presentation.api.v1.tasks import router as tasks_router
from src.presentation.middleware.error_handler import (
    domain_exception_handler,
    unhandled_exception_handler,
)


def create_app() -> FastAPI:
    app = FastAPI(
        title="Instagram Reel Processor",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Exception handlers
    app.add_exception_handler(DomainException, domain_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)

    # Routers
    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(tasks_router, prefix="/api/v1")
    app.include_router(health_router, prefix="/api/v1")

    # DI — wire ports to adapters for Celery workers
    @app.on_event("startup")
    async def startup() -> None:
        init_container()

    return app


app = create_app()
