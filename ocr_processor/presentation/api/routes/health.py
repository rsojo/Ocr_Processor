import shutil

from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()


@router.get("/health", tags=["observability"])
async def health():
    """Liveness check — always returns 200 if the process is running."""
    return {"status": "healthy", "version": "1.0.0"}


@router.get("/ready", tags=["observability"])
async def ready():
    """Readiness check — verifies Tesseract is available."""
    tesseract_available = shutil.which("tesseract") is not None
    if not tesseract_available:
        return JSONResponse(
            status_code=503,
            content={"status": "unavailable", "reason": "tesseract not found in PATH"},
        )
    return {"status": "ready"}
