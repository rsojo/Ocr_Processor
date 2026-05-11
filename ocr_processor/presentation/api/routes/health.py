import shutil

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from ocr_processor.config import settings

router = APIRouter()


def _tesseract_available() -> bool:
    return shutil.which(settings.tesseract_cmd) is not None


@router.get("/health", tags=["observability"])
async def health():
    """Liveness check — always returns 200 if the process is running."""
    return {"status": "healthy", "version": "1.0.0"}


@router.get("/ready", tags=["observability"])
async def ready():
    """Readiness check — verifies dependencies for the configured OCR engine."""
    engine = settings.ocr_engine.lower()
    tesseract_available = _tesseract_available()

    if engine == "tesseract" and not tesseract_available:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unavailable",
                "reason": f"tesseract not found at {settings.tesseract_cmd}",
            },
        )

    if engine == "pdf_inspector":
        try:
            import pdf_inspector  # noqa: F401
        except ImportError:
            return JSONResponse(
                status_code=503,
                content={
                    "status": "unavailable",
                    "reason": "pdf_inspector is not installed",
                },
            )
        if not tesseract_available:
            return JSONResponse(
                status_code=503,
                content={
                    "status": "unavailable",
                    "reason": (
                        "tesseract not found at "
                        f"{settings.tesseract_cmd} for scanned PDFs/images fallback"
                    ),
                },
            )

    if engine == "paddleocr":
        return JSONResponse(
            status_code=503,
            content={
                "status": "unavailable",
                "reason": "paddleocr engine is not implemented",
            },
        )

    if engine not in {"pdf_inspector", "tesseract", "paddleocr"}:
        return JSONResponse(
            status_code=503,
            content={"status": "unavailable", "reason": f"unknown OCR engine '{engine}'"},
        )

    return {"status": "ready", "engine": engine}
