import logging
import uuid

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from ocr_processor.domain.exceptions import (
    DownloadError,
    FileTooLargeError,
    InvalidFileTypeError,
    OCRProcessingError,
    UnsafeURLError,
)

logger = logging.getLogger(__name__)

REQUEST_ID_HEADER = "X-Request-ID"


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Injects a unique request-id into every request/response."""

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get(REQUEST_ID_HEADER, str(uuid.uuid4()))
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers[REQUEST_ID_HEADER] = request_id
        return response


def add_exception_handlers(app) -> None:
    """Register domain exception → HTTP response mappings."""

    @app.exception_handler(InvalidFileTypeError)
    async def handle_invalid_file_type(request: Request, exc: InvalidFileTypeError):
        return JSONResponse(
            status_code=422,
            content={"detail": str(exc), "type": "invalid_file_type"},
        )

    @app.exception_handler(FileTooLargeError)
    async def handle_file_too_large(request: Request, exc: FileTooLargeError):
        return JSONResponse(
            status_code=413,
            content={"detail": str(exc), "type": "file_too_large"},
        )

    @app.exception_handler(UnsafeURLError)
    async def handle_unsafe_url(request: Request, exc: UnsafeURLError):
        return JSONResponse(
            status_code=400,
            content={"detail": str(exc), "type": "unsafe_url"},
        )

    @app.exception_handler(DownloadError)
    async def handle_download_error(request: Request, exc: DownloadError):
        return JSONResponse(
            status_code=502,
            content={"detail": str(exc), "type": "download_error"},
        )

    @app.exception_handler(OCRProcessingError)
    async def handle_ocr_error(request: Request, exc: OCRProcessingError):
        return JSONResponse(
            status_code=500,
            content={"detail": str(exc), "type": "ocr_processing_error"},
        )
