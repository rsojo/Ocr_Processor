from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ocr_processor.config import settings
from ocr_processor.infrastructure.logging_config import configure_logging
from ocr_processor.presentation.api.middleware import (
    RequestIDMiddleware,
    add_exception_handlers,
)
from ocr_processor.presentation.api.routes import health, ocr_upload, ocr_url


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging(settings.log_level)
    Path(settings.temp_dir).mkdir(parents=True, exist_ok=True)
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="OCR Processor API",
        description=(
            "Extract text from images and PDFs using OCR. "
            "Supports file upload and remote URL processing."
        ),
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # Middleware
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Exception handlers
    add_exception_handlers(app)

    # Routes
    prefix = "/api/v1"
    app.include_router(health.router, prefix=prefix)
    app.include_router(ocr_upload.router, prefix=prefix)
    app.include_router(ocr_url.router, prefix=prefix)

    return app


app = create_app()
